"""Mirror a shared Google Drive folder into a class's notes.

Only metadata is stored; file bytes stay in Drive and are streamed on demand
through the permission-checked download route.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

from flask import current_app
from flask_login import current_user

from extensions import db
from models import (
    Class,
    ClassNotesDriveItem,
    ClassNotesDriveLink,
    ClassNotesFolder,
    User,
)
from services.google_drive_service import (
    DriveAccessError,
    DriveAuthError,
    convert_office_file_to_google,
    download_file_bytes,
    export_target_for,
    extract_drive_folder_id,
    get_drive_service,
    get_file_metadata,
    get_folder_metadata,
    google_convert_mime_for,
    is_google_native,
    list_folder_children,
    open_label_for_mime,
    partition_children,
    resolve_shortcut,
    share_file_with_school_domain,
)
from utils.class_notes_media import notes_media_kind_for_drive

from .class_notes_spa_helpers import (
    NOTES_MAX_FOLDER_DEPTH,
    _folder_depth,
    _user_can_manage_class_notes,
    _user_can_view_class_notes,
    ensure_class_notes_tables,
    get_class_notes_payload,
    serialize_drive_link,
)

# How stale a link may be before opening the notes page refreshes it.
DRIVE_SYNC_STALE_AFTER = timedelta(minutes=10)
# Keep in-request Drive walks under Render's ~30s worker timeout.
DRIVE_SYNC_TIME_BUDGET_SECONDS = 18
DRIVE_SYNC_MAX_FOLDERS = 40


def ensure_google_token_column_wide() -> None:
    """Widen user._google_refresh_token so Fernet blobs are not truncated."""
    from sqlalchemy import inspect as sa_inspect, text

    try:
        cols = {c['name']: c for c in sa_inspect(db.engine).get_columns('user')}
        col = cols.get('_google_refresh_token')
        if not col:
            return
        col_type = str(col.get('type') or '').upper()
        # Already TEXT / unbounded — nothing to do.
        if 'TEXT' in col_type or 'CLOB' in col_type or col_type in ('', 'NULL'):
            return
        if 'VARCHAR' in col_type or 'CHARACTER VARYING' in col_type:
            dialect = db.engine.dialect.name
            if dialect == 'postgresql':
                ddl = 'ALTER TABLE "user" ALTER COLUMN _google_refresh_token TYPE TEXT'
            elif dialect == 'sqlite':
                # SQLite ignores VARCHAR length; leave alone.
                return
            else:
                ddl = 'ALTER TABLE user MODIFY _google_refresh_token TEXT'
            with db.engine.begin() as conn:
                conn.execute(text(ddl))
    except Exception:
        current_app.logger.exception('Could not widen user._google_refresh_token')


def _users_for_class_drive(class_obj: Class) -> list[User]:
    """Users whose Google token may open this class's Drive folder.

    Prefer the person doing the action, then the primary teacher, then any
    additional teachers — so an admin linking notes still works when the class
    teacher has Google connected.
    """
    seen: set[int] = set()
    ordered: list[User] = []

    def add(user: User | None) -> None:
        if user is None or user.id in seen:
            return
        seen.add(user.id)
        ordered.append(user)

    add(User.query.get(getattr(current_user, 'id', None)))

    teacher_ids: list[int] = []
    if getattr(class_obj, 'teacher_id', None):
        teacher_ids.append(class_obj.teacher_id)
    try:
        for staff in class_obj.additional_teachers.all():
            if staff and staff.id:
                teacher_ids.append(staff.id)
    except Exception:
        pass

    if teacher_ids:
        for user in User.query.filter(User.teacher_staff_id.in_(teacher_ids)).all():
            add(user)

    return ordered


def _ensure_converted_file_column() -> None:
    """Add converted_drive_file_id if this database is older than the column."""
    try:
        from sqlalchemy import inspect as sa_inspect, text

        cols = {c['name'] for c in sa_inspect(db.engine).get_columns('class_notes_drive_item')}
        if 'converted_drive_file_id' in cols:
            return
        dialect = db.engine.dialect.name
        col = 'VARCHAR(120)' if dialect != 'postgresql' else 'VARCHAR(120)'
        with db.engine.begin() as conn:
            conn.execute(text(
                f'ALTER TABLE class_notes_drive_item ADD COLUMN converted_drive_file_id {col}'
            ))
    except Exception:
        current_app.logger.exception('Could not add converted_drive_file_id column')


def _drive_service_for_class(class_obj: Class):
    """Build a Drive client using the first usable OAuth token for this class."""
    errors: list[str] = []
    for user in _users_for_class_drive(class_obj):
        if not getattr(user, 'has_google_token_stored', False):
            continue
        try:
            return get_drive_service(user), user
        except DriveAuthError as exc:
            errors.append(str(exc))
    if errors:
        # Prefer the most actionable message from the signed-in user.
        raise DriveAuthError(errors[0])
    raise DriveAuthError(
        'Your portal Google account is not connected in Settings. '
        'Open Settings and click Connect Google account, then try again.'
    )


def _link_owner(link: ClassNotesDriveLink) -> User | None:
    if link.linked_by:
        return link.linked_by
    if link.linked_by_user_id:
        return User.query.get(link.linked_by_user_id)
    return None


def _mirrored_folder_key(link: ClassNotesDriveLink, drive_folder_id: str) -> dict[str, Any]:
    return {
        'class_id': link.class_id,
        'drive_link_id': link.id,
        'drive_folder_id': drive_folder_id,
    }


def _upsert_mirror_folder(
    link: ClassNotesDriveLink,
    *,
    drive_folder_id: str,
    name: str,
    parent_id: int | None,
) -> ClassNotesFolder:
    folder = ClassNotesFolder.query.filter_by(
        **_mirrored_folder_key(link, drive_folder_id)
    ).first()
    if folder:
        folder.name = (name or folder.name)[:200]
        folder.parent_id = parent_id
        folder.updated_at = datetime.utcnow()
        return folder

    folder = ClassNotesFolder(
        class_id=link.class_id,
        parent_id=parent_id,
        name=(name or 'Drive folder')[:200],
        sort_order=0,
        created_by_user_id=link.linked_by_user_id,
        drive_folder_id=drive_folder_id,
        drive_link_id=link.id,
    )
    db.session.add(folder)
    db.session.flush()
    return folder


def _upsert_drive_item(
    link: ClassNotesDriveLink,
    entry: dict[str, Any],
    *,
    folder_id: int | None,
) -> ClassNotesDriveItem:
    drive_file_id = entry.get('id')
    mime_type = entry.get('mimeType')
    name = (entry.get('name') or 'Untitled')[:255]

    size: int | None
    try:
        size = int(entry['size']) if entry.get('size') is not None else None
    except (TypeError, ValueError):
        size = None

    item = ClassNotesDriveItem.query.filter_by(
        link_id=link.id, drive_file_id=drive_file_id
    ).first()
    if not item:
        item = ClassNotesDriveItem(link_id=link.id, drive_file_id=drive_file_id)
        db.session.add(item)

    item.class_id = link.class_id
    item.folder_id = folder_id
    item.name = name
    item.mime_type = mime_type
    item.media_kind = notes_media_kind_for_drive(mime_type, name)
    item.file_size = size
    item.drive_modified_time = entry.get('modifiedTime')
    item.web_view_link = entry.get('webViewLink')
    item.is_google_native = is_google_native(mime_type)
    item.synced_at = datetime.utcnow()
    return item


def sync_drive_link(link: ClassNotesDriveLink) -> tuple[bool, str | None]:
    """Walk the linked Drive folder and refresh mirrored folders and files.

    Stops after a short time budget so a large curriculum folder cannot kill
    the Gunicorn worker. Incomplete imports stay in the database; click Sync
    again to continue. Stale files are only deleted after a full walk.
    """
    owner = _link_owner(link)
    if not owner:
        link.needs_reauth = True
        link.last_error = 'The account that linked this folder is no longer available.'
        db.session.commit()
        return False, link.last_error

    try:
        service = get_drive_service(owner)
    except DriveAuthError as exc:
        link.needs_reauth = True
        link.last_error = str(exc)
        db.session.commit()
        return False, link.last_error

    seen_file_ids: set[str] = set()
    seen_folder_ids: set[str] = set()
    deadline = time.monotonic() + DRIVE_SYNC_TIME_BUDGET_SECONDS
    folders_visited = 0
    incomplete = False

    # (drive folder id, notes folder id, depth of the notes folder)
    base_depth = _folder_depth(link.folder) if link.folder else 0
    queue: list[tuple[str, int | None, int]] = [
        (link.drive_folder_id, link.folder_id, base_depth)
    ]

    try:
        while queue:
            if time.monotonic() >= deadline or folders_visited >= DRIVE_SYNC_MAX_FOLDERS:
                incomplete = True
                break
            drive_folder_id, notes_folder_id, depth = queue.pop(0)
            folders_visited += 1
            children = list_folder_children(service, drive_folder_id, page_limit=2)
            resolved = [resolve_shortcut(service, entry) for entry in children]
            subfolders, files = partition_children(resolved)

            for entry in files:
                if not entry.get('id'):
                    continue
                _upsert_drive_item(link, entry, folder_id=notes_folder_id)
                seen_file_ids.add(entry['id'])

            if not link.include_subfolders:
                continue

            for sub in subfolders:
                sub_id = sub.get('id')
                if not sub_id or sub_id in seen_folder_ids:
                    continue
                if depth >= NOTES_MAX_FOLDER_DEPTH:
                    queue.append((sub_id, notes_folder_id, depth))
                    seen_folder_ids.add(sub_id)
                    continue
                mirror = _upsert_mirror_folder(
                    link,
                    drive_folder_id=sub_id,
                    name=sub.get('name') or 'Drive folder',
                    parent_id=notes_folder_id,
                )
                seen_folder_ids.add(sub_id)
                queue.append((sub_id, mirror.id, depth + 1))
            if queue and time.monotonic() >= deadline:
                incomplete = True
                break
    except DriveAccessError as exc:
        db.session.rollback()
        link.last_error = str(exc)
        db.session.commit()
        return False, link.last_error
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Drive sync failed for link %s', link.id)
        link.last_error = f'Sync failed: {exc}'
        db.session.commit()
        return False, link.last_error

    if incomplete:
        db.session.commit()
        link.last_error = (
            'Imported some files, but the Drive folder is large. Click Sync now to continue.'
        )
        link.needs_reauth = False
        db.session.commit()
        return True, link.last_error

    # Drop anything that disappeared from Drive since the last sync.
    for stale in ClassNotesDriveItem.query.filter_by(link_id=link.id).all():
        if stale.drive_file_id not in seen_file_ids:
            db.session.delete(stale)
    for stale_folder in ClassNotesFolder.query.filter_by(
        class_id=link.class_id, drive_link_id=link.id
    ).all():
        if stale_folder.drive_folder_id not in seen_folder_ids:
            db.session.delete(stale_folder)

    link.last_synced_at = datetime.utcnow()
    link.last_error = None
    link.needs_reauth = False
    db.session.commit()
    return True, None


def drive_link_is_stale(link: ClassNotesDriveLink) -> bool:
    """True when a linked Drive folder should be refreshed (never synced or older than cutoff)."""
    if link.needs_reauth:
        return False
    if not link.last_synced_at:
        return True
    cutoff = datetime.utcnow() - DRIVE_SYNC_STALE_AFTER
    return link.last_synced_at <= cutoff


def refresh_stale_drive_links(class_id: int) -> None:
    """Best-effort refresh when the notes page is opened."""
    try:
        links = ClassNotesDriveLink.query.filter_by(class_id=class_id, is_active=True).all()
    except Exception:
        return
    cutoff = datetime.utcnow() - DRIVE_SYNC_STALE_AFTER
    for link in links:
        if link.needs_reauth:
            continue
        if link.last_synced_at and link.last_synced_at > cutoff:
            continue
        try:
            sync_drive_link(link)
        except Exception:
            current_app.logger.exception('Background Drive refresh failed for link %s', link.id)


def link_drive_folder(
    class_id: int,
    *,
    folder_url: str,
    folder_id: int | None = None,
    include_subfolders: bool = True,
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can link a Drive folder.', 403

    drive_folder_id = extract_drive_folder_id(folder_url)
    if not drive_folder_id:
        return None, 'Paste a Google Drive folder link or its folder ID.', 400

    if folder_id is not None:
        target = ClassNotesFolder.query.filter_by(id=folder_id, class_id=class_id).first()
        if not target:
            return None, 'Folder not found', 404

    existing = ClassNotesDriveLink.query.filter_by(
        class_id=class_id, drive_folder_id=drive_folder_id
    ).first()
    if existing and existing.is_active:
        return None, 'That Drive folder is already linked to this class.', 400

    try:
        service, oauth_user = _drive_service_for_class(class_obj)
    except DriveAuthError as exc:
        return None, str(exc), 400

    try:
        meta = get_folder_metadata(service, drive_folder_id)
    except DriveAccessError as exc:
        return None, str(exc), 400

    link = existing or ClassNotesDriveLink(
        class_id=class_id,
        drive_folder_id=drive_folder_id,
    )
    link.folder_id = folder_id
    link.drive_folder_name = (meta.get('name') or 'Drive folder')[:255]
    link.drive_web_view_link = meta.get('webViewLink')
    link.linked_by_user_id = oauth_user.id
    link.include_subfolders = bool(include_subfolders)
    link.is_active = True
    link.needs_reauth = False
    link.last_error = None
    db.session.add(link)
    db.session.commit()

    payload, _, _ = get_class_notes_payload(class_id)
    return {
        'success': True,
        'message': (
            f'Linked "{link.drive_folder_name}". Importing files next — '
            'large folders may need a second Sync now.'
        ),
        'needs_sync': True,
        'drive_link': serialize_drive_link(link),
        **(payload or {}),
    }, None, 201


def sync_drive_link_by_id(
    class_id: int, link_id: int
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can sync a Drive folder.', 403

    link = ClassNotesDriveLink.query.filter_by(id=link_id, class_id=class_id).first()
    if not link:
        return None, 'Drive link not found', 404

    ok, error = sync_drive_link(link)
    payload, _, _ = get_class_notes_payload(class_id)
    if ok and error:
        message = error
    elif ok:
        message = 'Drive folder synced.'
    else:
        message = error or 'Sync failed.'
    return {
        'success': ok,
        'message': message,
        'drive_link': serialize_drive_link(link),
        **(payload or {}),
    }, None, 200 if ok else 400


def unlink_drive_folder(
    class_id: int, link_id: int
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can unlink a Drive folder.', 403

    link = ClassNotesDriveLink.query.filter_by(id=link_id, class_id=class_id).first()
    if not link:
        return None, 'Drive link not found', 404

    name = link.drive_folder_name
    for item in ClassNotesDriveItem.query.filter_by(link_id=link.id).all():
        db.session.delete(item)
    for folder in ClassNotesFolder.query.filter_by(
        class_id=class_id, drive_link_id=link.id
    ).all():
        db.session.delete(folder)
    db.session.delete(link)
    db.session.commit()

    payload, _, _ = get_class_notes_payload(class_id)
    return {
        'success': True,
        'message': f'Unlinked "{name}". Files remain in Google Drive.',
        **(payload or {}),
    }, None, 200


def _google_open_url_for_item(service, item: ClassNotesDriveItem) -> str:
    """Convert Office files to Docs/Slides/Sheets and return a view URL."""
    _ensure_converted_file_column()
    converted_id = getattr(item, 'converted_drive_file_id', None)

    if converted_id:
        try:
            meta = get_file_metadata(service, converted_id)
            url = meta.get('webViewLink')
            if url:
                share_file_with_school_domain(service, converted_id)
                return url
        except DriveAccessError:
            item.converted_drive_file_id = None

    if is_google_native(item.mime_type):
        share_file_with_school_domain(service, item.drive_file_id)
        if item.web_view_link:
            return item.web_view_link
        meta = get_file_metadata(service, item.drive_file_id)
        url = meta.get('webViewLink')
        if url:
            item.web_view_link = url
            db.session.commit()
            return url

    if google_convert_mime_for(item.mime_type):
        copied = convert_office_file_to_google(
            service,
            item.drive_file_id,
            name=item.name,
            mime_type=item.mime_type,
        )
        item.converted_drive_file_id = copied.get('id')
        url = copied.get('webViewLink')
        if url:
            item.web_view_link = url
        db.session.commit()
        if url:
            return url

    share_file_with_school_domain(service, item.drive_file_id)
    if item.web_view_link:
        return item.web_view_link
    meta = get_file_metadata(service, item.drive_file_id)
    url = meta.get('webViewLink')
    if url:
        item.web_view_link = url
        db.session.commit()
        return url
    raise DriveAccessError('Could not open that file in Google Drive.')


def open_drive_item(class_id: int, item_id: int) -> tuple[str | None, str | None, int]:
    """Return a Google Docs/Slides/Sheets (or Drive preview) URL for one file."""
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_view_class_notes(class_obj):
        return None, 'Access denied', 403

    item = ClassNotesDriveItem.query.filter_by(id=item_id, class_id=class_id).first()
    if not item:
        return None, 'File not found', 404
    link = item.link
    if not link:
        return None, 'Drive link not found', 404
    owner = _link_owner(link)
    if not owner:
        return None, 'The Google account for this folder is no longer connected.', 400

    try:
        service = get_drive_service(owner)
        url = _google_open_url_for_item(service, item)
    except DriveAuthError as exc:
        link.needs_reauth = True
        db.session.commit()
        return None, str(exc), 400
    except DriveAccessError as exc:
        return None, str(exc), 400
    return url, None, 200


def download_drive_item(class_id: int, item_id: int):
    """Stream a mirrored Drive file to a viewer who has class access."""
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_view_class_notes(class_obj):
        return None, 'Access denied', 403

    # Only mirrored files are servable, so wider Drive access cannot be abused here.
    item = ClassNotesDriveItem.query.filter_by(id=item_id, class_id=class_id).first()
    if not item:
        return None, 'File not found', 404

    link = item.link
    if not link:
        return None, 'Drive link not found', 404

    owner = _link_owner(link)
    if not owner:
        return None, 'The Google account for this folder is no longer connected.', 400

    try:
        service = get_drive_service(owner)
        data, content_type = download_file_bytes(
            service, item.drive_file_id, mime_type=item.mime_type
        )
    except DriveAuthError as exc:
        link.needs_reauth = True
        db.session.commit()
        return None, str(exc), 400
    except DriveAccessError as exc:
        return None, str(exc), 400

    download_name = item.name
    export = export_target_for(item.mime_type)
    if export:
        _, extension = export
        if not download_name.lower().endswith(f'.{extension}'):
            download_name = f'{download_name}.{extension}'

    inline = item.media_kind in ('image', 'video') or content_type == 'application/pdf'
    return (
        {
            'data': data,
            'content_type': content_type,
            'download_name': download_name,
            'inline': inline,
        },
        None,
        200,
    )
