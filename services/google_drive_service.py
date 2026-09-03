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


DRIVE_API_NOT_ENABLED = (
    'Google Drive API is not enabled for this app. Reconnecting your account will not fix it. '
    'A tech admin must enable "Google Drive API" in Google Cloud Console '
    '(APIs & Services → Library), wait a minute, then try linking the folder again.'
)


def _http_error_blob(exc: Exception) -> str:
    parts = [str(exc)]
    content = getattr(exc, 'content', None)
    if content:
        if isinstance(content, bytes):
            parts.append(content.decode('utf-8', errors='replace'))
        else:
            parts.append(str(content))
    return ' '.join(parts)


def _drive_access_message(exc: Exception, fallback: str) -> str:
    blob = _http_error_blob(exc)
    blob_lower = blob.lower()
    if 'accessnotconfigured' in blob_lower or 'drive api has not been used' in blob_lower:
        match = re.search(
            r'https://console\.(?:developers|cloud)\.google\.com/[^\s"\'<>]+',
            blob,
        )
        if match:
            return f'{DRIVE_API_NOT_ENABLED} Enable here: {match.group(0)}'
        return DRIVE_API_NOT_ENABLED
    if 'invalid_grant' in blob_lower:
        return (
            'Google access has expired or was revoked. '
            'Click Reconnect Google account, approve Drive access, then try again.'
        )
    return fallback


def _raise_drive_access(exc: Exception, fallback: str) -> None:
    current_app.logger.warning('Drive API call failed: %s', exc)
    raise DriveAccessError(_drive_access_message(exc, fallback)) from exc


def _clear_revoked_google_token(user) -> None:
    """Drop a refresh token Google has rejected so Settings shows Connect, not Connected."""
    try:
        from extensions import db

        user.google_refresh_token = None
        db.session.commit()
        current_app.logger.info('Cleared revoked Google refresh token for user %s', getattr(user, 'id', None))
    except Exception:
        current_app.logger.exception(
            'Could not clear revoked Google token for user %s', getattr(user, 'id', None)
        )


def safe_google_oauth_next(raw: str | None) -> str | None:
    """Allow only same-site relative return paths after Google OAuth."""
    value = (raw or '').strip()
    if not value.startswith('/') or value.startswith('//'):
        return None
    if '\\' in value or value.startswith('/\\'):
        return None
    return value[:500]


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
            _clear_revoked_google_token(db_user)
            raise DriveAuthError(
                'Google access has expired or was revoked. '
                'Click Reconnect Google account, approve Drive access, then link the folder again.'
            )
        raise DriveAuthError(
            'Google would not refresh Drive access. '
            'Click Reconnect Google account and approve Drive when asked.'
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
        _raise_drive_access(
            exc,
            'Could not open that Drive item. Make sure it is shared with your school account.',
        )


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
            _raise_drive_access(exc, 'Could not list that Drive folder.')

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


WORKSPACE_DOMAIN = 'clarascienceacademy.org'

# Office / text files that students cannot open locally — convert to Google Docs/Slides/Sheets.
OFFICE_TO_GOOGLE_MIME: dict[str, str] = {
    'application/msword': 'application/vnd.google-apps.document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': (
        'application/vnd.google-apps.document'
    ),
    'application/rtf': 'application/vnd.google-apps.document',
    'text/plain': 'application/vnd.google-apps.document',
    'application/vnd.ms-powerpoint': 'application/vnd.google-apps.presentation',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': (
        'application/vnd.google-apps.presentation'
    ),
    'application/vnd.ms-excel': 'application/vnd.google-apps.spreadsheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': (
        'application/vnd.google-apps.spreadsheet'
    ),
}

GOOGLE_APP_OPEN_LABELS: dict[str, str] = {
    'application/vnd.google-apps.document': 'Open in Google Docs',
    'application/vnd.google-apps.presentation': 'Open in Google Slides',
    'application/vnd.google-apps.spreadsheet': 'Open in Google Sheets',
    'application/vnd.google-apps.drawing': 'Open in Google Drawings',
}


def is_google_native(mime_type: str | None) -> bool:
    mime = (mime_type or '').lower()
    return mime.startswith('application/vnd.google-apps.') and mime != FOLDER_MIME_TYPE


def google_convert_mime_for(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    return OFFICE_TO_GOOGLE_MIME.get(mime_type.lower())


def open_label_for_mime(mime_type: str | None) -> str:
    mime = (mime_type or '').lower()
    if mime in GOOGLE_APP_OPEN_LABELS:
        return GOOGLE_APP_OPEN_LABELS[mime]
    converted = google_convert_mime_for(mime)
    if converted:
        return GOOGLE_APP_OPEN_LABELS.get(converted, 'Open')
    if mime == 'application/pdf' or mime.startswith('image/') or mime.startswith('video/'):
        return 'Open'
    return 'Open'


def share_file_with_school_domain(service, file_id: str) -> None:
    """Let anyone on the school Workspace domain view the file (no email blast)."""
    try:
        service.permissions().create(
            fileId=file_id,
            body={
                'type': 'domain',
                'domain': WORKSPACE_DOMAIN,
                'role': 'reader',
                'allowFileDiscovery': False,
            },
            fields='id',
            sendNotificationEmail=False,
            supportsAllDrives=True,
        ).execute()
    except Exception:
        # Already shared, or the owner restricted sharing — Open can still work for staff.
        current_app.logger.info('Could not domain-share Drive file %s', file_id)


def convert_office_file_to_google(
    service,
    file_id: str,
    *,
    name: str,
    mime_type: str | None,
) -> dict[str, Any]:
    """Copy an Office file into Google Docs/Slides/Sheets in the teacher's Drive."""
    target_mime = google_convert_mime_for(mime_type)
    if not target_mime:
        raise DriveAccessError('That file type cannot be opened as a Google Doc or Slide.')
    stem = (name or 'Untitled').rsplit('.', 1)[0][:200] or 'Untitled'
    try:
        copied = (
            service.files()
            .copy(
                fileId=file_id,
                body={'name': stem, 'mimeType': target_mime},
                fields='id,name,mimeType,webViewLink',
                supportsAllDrives=True,
            )
            .execute()
        )
    except Exception as exc:
        _raise_drive_access(
            exc,
            'Could not convert that file to Google Docs/Slides. '
            'Make sure it is shared with your school account.',
        )
    copied_id = copied.get('id')
    if copied_id:
        share_file_with_school_domain(service, copied_id)
    return copied


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
        _raise_drive_access(exc, 'Could not download that file from Drive.')


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
