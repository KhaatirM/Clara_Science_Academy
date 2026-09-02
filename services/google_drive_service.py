"""
Google Drive Service Module

Reads shared Drive folders on behalf of a teacher using their stored OAuth
refresh token. Used by class notes to mirror a folder's contents without
copying file bytes into portal storage.
"""

from __future__ import annotations

import io
import re
from typing import Any, Iterable

import requests
from flask import current_app
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'
SHORTCUT_MIME_TYPE = 'application/vnd.google-apps.shortcut'

# Google-native docs have no byte stream; they must be exported to a real format.
GOOGLE_NATIVE_EXPORTS: dict[str, tuple[str, str]] = {
    'application/vnd.google-apps.document': ('application/pdf', 'pdf'),
    'application/vnd.google-apps.presentation': ('application/pdf', 'pdf'),
    'application/vnd.google-apps.drawing': ('application/pdf', 'pdf'),
    'application/vnd.google-apps.spreadsheet': (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xlsx',
    ),
}

_FILE_FIELDS = (
    'id, name, mimeType, size, modifiedTime, webViewLink, iconLink, trashed, '
    'shortcutDetails(targetId, targetMimeType)'
)
_LIST_FIELDS = f'nextPageToken, files({_FILE_FIELDS})'

# Drive folder links look like /drive/folders/<id>, /drive/u/0/folders/<id>,
# or carry the id in a ?id= query parameter.
_FOLDER_URL_PATTERNS = (
    re.compile(r'/folders/([a-zA-Z0-9_-]+)'),
    re.compile(r'[?&]id=([a-zA-Z0-9_-]+)'),
    re.compile(r'/d/([a-zA-Z0-9_-]+)'),
)


class DriveAuthError(Exception):
    """The user's Google credentials are missing, revoked, or undecryptable."""


class DriveAccessError(Exception):
    """The folder or file could not be read with these credentials."""


def extract_drive_folder_id(raw: str) -> str | None:
    """Accept a full Drive URL or a bare folder id."""
    value = (raw or '').strip()
    if not value:
        return None
    if '/' not in value and '?' not in value:
        return value if re.fullmatch(r'[a-zA-Z0-9_-]{10,}', value) else None
    for pattern in _FOLDER_URL_PATTERNS:
        match = pattern.search(value)
        if match:
            return match.group(1)
    return None


def get_drive_service(user):
    """Build a Drive v3 client authenticated as ``user``.

    Reloads the user from the database so Flask-Login session objects cannot
    hide a freshly saved refresh token. Raises DriveAuthError with a specific
    message when the account is not connected, the stored token cannot be
    decrypted, or Google rejects the refresh.
    """
    from models import User

    user_id = getattr(user, 'id', None)
    db_user = User.query.get(user_id) if user_id else None
    if db_user is None:
        raise DriveAuthError(
            'Could not load your account to use Google Drive. Sign out and back in, then try again.'
        )

    if not db_user.has_google_token_stored:
        raise DriveAuthError(
            'Your portal Google account is not connected in Settings. '
            'Signing in with Google is not enough — open Settings and click Connect Google account.'
        )

    refresh_token = db_user.google_refresh_token
    if not refresh_token:
        raise DriveAuthError(
            'Your saved Google connection could not be read. '
            'Open Settings, disconnect Google, then Connect again.'
        )

    token_uri = 'https://oauth2.googleapis.com/token'
    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise DriveAuthError('Google OAuth is not configured on this server.')

    try:
        response = requests.post(
            token_uri,
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            },
            timeout=20,
        )
        payload = response.json()
    except Exception as exc:
        raise DriveAuthError('Could not reach Google to refresh access.') from exc

    if 'access_token' not in payload:
        current_app.logger.error(
            'Drive token refresh failed for user %s: %s', getattr(db_user, 'id', '?'), payload
        )
        error_code = (payload or {}).get('error')
        if error_code in ('invalid_grant', 'invalid_client'):
            raise DriveAuthError(
                'Google access has expired or was revoked. '
                'Open Settings, disconnect Google, then Connect again (Drive access is included).'
            )
        raise DriveAuthError(
            'Google would not refresh Drive access. '
            'Open Settings and reconnect your Google account, approving Drive when asked.'
        )

    creds = Credentials(
        token=payload['access_token'],
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
    )
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def get_file_metadata(service, file_id: str) -> dict[str, Any]:
    try:
        return (
            service.files()
            .get(fileId=file_id, fields=_FILE_FIELDS, supportsAllDrives=True)
            .execute()
        )
    except Exception as exc:
        raise DriveAccessError(
            'Could not open that Drive item. Make sure it is shared with your school account.'
        ) from exc


def get_folder_metadata(service, folder_id: str) -> dict[str, Any]:
    meta = get_file_metadata(service, folder_id)
    if meta.get('mimeType') != FOLDER_MIME_TYPE:
        raise DriveAccessError('That link points to a file, not a folder.')
    if meta.get('trashed'):
        raise DriveAccessError('That folder is in the Drive trash.')
    return meta


def list_folder_children(service, folder_id: str, *, page_limit: int = 20) -> list[dict[str, Any]]:
    """Return non-trashed children of a folder, following pagination."""
    children: list[dict[str, Any]] = []
    page_token: str | None = None
    pages = 0
    while pages < page_limit:
        try:
            response = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    fields=_LIST_FIELDS,
                    pageSize=200,
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    orderBy='folder,name',
                )
                .execute()
            )
        except Exception as exc:
            raise DriveAccessError('Could not list that Drive folder.') from exc

        children.extend(response.get('files', []) or [])
        page_token = response.get('nextPageToken')
        pages += 1
        if not page_token:
            break
    return children


def resolve_shortcut(service, entry: dict[str, Any]) -> dict[str, Any]:
    """Follow a Drive shortcut to its target, returning the entry unchanged otherwise."""
    if entry.get('mimeType') != SHORTCUT_MIME_TYPE:
        return entry
    target_id = (entry.get('shortcutDetails') or {}).get('targetId')
    if not target_id:
        return entry
    try:
        target = get_file_metadata(service, target_id)
    except DriveAccessError:
        return entry
    # Keep the shortcut's display name, which is what the teacher sees in Drive.
    target['name'] = entry.get('name') or target.get('name')
    return target


def is_google_native(mime_type: str | None) -> bool:
    return bool(mime_type) and mime_type in GOOGLE_NATIVE_EXPORTS


def export_target_for(mime_type: str | None) -> tuple[str, str] | None:
    if not mime_type:
        return None
    return GOOGLE_NATIVE_EXPORTS.get(mime_type)


def download_file_bytes(service, file_id: str, *, mime_type: str | None = None) -> tuple[bytes, str]:
    """Fetch a Drive file's contents.

    Google-native docs are exported (PDF/XLSX); everything else downloads as-is.
    Returns (data, content_type).
    """
    export = export_target_for(mime_type)
    try:
        if export:
            export_mime, _ = export
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            content_type = export_mime
        else:
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            content_type = mime_type or 'application/octet-stream'

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request, chunksize=1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue(), content_type
    except Exception as exc:
        raise DriveAccessError('Could not download that file from Drive.') from exc


def partition_children(entries: Iterable[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    """Split Drive children into (folders, files)."""
    folders: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get('trashed'):
            continue
        if entry.get('mimeType') == FOLDER_MIME_TYPE:
            folders.append(entry)
        else:
            files.append(entry)
    return folders, files
