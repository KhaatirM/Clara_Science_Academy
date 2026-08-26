"""Class notes SPA helpers: nested folders/units and file uploads."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any

from flask import current_app, send_from_directory
from flask_login import current_user
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename

from extensions import db
from models import Class, ClassNotesFolder, ClassNotesItem, Enrollment
from utils.class_notes_media import (
    NOTES_ALLOWED_EXTENSIONS,
    NOTES_MAX_VIDEO_SECONDS,
    notes_media_kind,
    probe_video_duration_seconds,
    validate_notes_extension,
)
from utils.user_roles import user_has_management_entry_access

NOTES_MAX_FOLDER_DEPTH = 3


def ensure_class_notes_tables() -> None:
    try:
        ClassNotesFolder.__table__.create(db.engine, checkfirst=True)
        ClassNotesItem.__table__.create(db.engine, checkfirst=True)
        _ensure_parent_id_column()
    except Exception:
        current_app.logger.exception('Could not ensure class notes tables')


def _ensure_parent_id_column() -> None:
    try:
        insp = inspect(db.engine)
        cols = {c['name'] for c in insp.get_columns('class_notes_folder')}
        if 'parent_id' in cols:
            return
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    'ALTER TABLE class_notes_folder '
                    'ADD COLUMN parent_id INTEGER REFERENCES class_notes_folder(id)'
                )
            )
    except Exception:
        current_app.logger.exception('Could not add class_notes_folder.parent_id')


def _notes_upload_dir() -> str:
    root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(
        current_app.root_path, 'static', 'uploads'
    )
    path = os.path.join(root, 'class_notes')
    os.makedirs(path, exist_ok=True)
    return path


def _user_can_manage_class_notes(class_obj: Class) -> bool:
    if user_has_management_entry_access(current_user):
        return True
    try:
        from teacher_routes.utils import is_authorized_for_class

        return bool(is_authorized_for_class(class_obj))
    except Exception:
        return False


def _user_can_view_class_notes(class_obj: Class) -> bool:
    if _user_can_manage_class_notes(class_obj):
        return True
    student = getattr(current_user, 'student_profile', None)
    if not student:
        return False
    return (
        Enrollment.query.filter_by(
            class_id=class_obj.id, student_id=student.id, is_active=True
        ).first()
        is not None
    )


def _delete_item_file(item: ClassNotesItem) -> None:
    root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(
        current_app.root_path, 'static', 'uploads'
    )
    abs_path = os.path.join(root, item.relative_path.replace('/', os.sep))
    try:
        if os.path.isfile(abs_path):
            os.remove(abs_path)
    except OSError:
        pass


def _folder_depth(folder: ClassNotesFolder | None) -> int:
    depth = 0
    seen: set[int] = set()
    cur = folder
    while cur is not None:
        depth += 1
        if cur.id in seen:
            break
        seen.add(cur.id)
        cur = cur.parent
    return depth


def _would_cycle(folder: ClassNotesFolder, new_parent_id: int | None) -> bool:
    if new_parent_id is None:
        return False
    if new_parent_id == folder.id:
        return True
    cur = ClassNotesFolder.query.get(new_parent_id)
    seen = {folder.id}
    while cur is not None:
        if cur.id in seen:
            return True
        seen.add(cur.id)
        cur = cur.parent
    return False


def _serialize_item(item: ClassNotesItem) -> dict[str, Any]:
    return {
        'id': item.id,
        'class_id': item.class_id,
        'folder_id': item.folder_id,
        'title': item.title,
        'original_filename': item.original_filename,
        'content_type': item.content_type,
        'file_size': item.file_size,
        'media_kind': item.media_kind,
        'duration_seconds': item.duration_seconds,
        'download_url': f'/api/spa/classes/{item.class_id}/notes/items/{item.id}/download',
        'uploaded_at': item.uploaded_at.isoformat() if item.uploaded_at else None,
        'uploaded_by': item.uploaded_by.username if item.uploaded_by else None,
    }


def _serialize_folder_node(
    folder: ClassNotesFolder,
    children_by_parent: dict[int | None, list[ClassNotesFolder]],
) -> dict[str, Any]:
    folder_items = sorted(
        folder.items or [],
        key=lambda i: i.uploaded_at or datetime.min,
        reverse=True,
    )
    items = [_serialize_item(i) for i in folder_items]
    kids = children_by_parent.get(folder.id, [])
    return {
        'id': folder.id,
        'parent_id': folder.parent_id,
        'name': folder.name,
        'description': folder.description or '',
        'sort_order': folder.sort_order or 0,
        'depth': _folder_depth(folder),
        'item_count': len(items),
        'items': items,
        'children': [_serialize_folder_node(c, children_by_parent) for c in kids],
        'created_at': folder.created_at.isoformat() if folder.created_at else None,
    }


def _build_folder_tree(folders: list[ClassNotesFolder]) -> list[dict[str, Any]]:
    by_parent: dict[int | None, list[ClassNotesFolder]] = {}
    for f in folders:
        by_parent.setdefault(f.parent_id, []).append(f)
    for kids in by_parent.values():
        kids.sort(key=lambda x: (x.sort_order or 0, (x.name or '').lower()))
    roots = by_parent.get(None, [])
    return [_serialize_folder_node(f, by_parent) for f in roots]


def _flatten_folders(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in nodes:
        children = node.get('children') or []
        flat = {k: v for k, v in node.items() if k != 'children'}
        out.append(flat)
        out.extend(_flatten_folders(children))
    return out


def get_class_notes_payload(class_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_view_class_notes(class_obj):
        return None, 'Access denied', 403

    can_manage = _user_can_manage_class_notes(class_obj)
    folders = (
        ClassNotesFolder.query.filter_by(class_id=class_id)
        .order_by(ClassNotesFolder.sort_order.asc(), ClassNotesFolder.name.asc())
        .all()
    )
    tree = _build_folder_tree(folders)
    root_items = (
        ClassNotesItem.query.filter_by(class_id=class_id, folder_id=None)
        .order_by(ClassNotesItem.uploaded_at.desc())
        .all()
    )
    return {
        'class': {
            'id': class_obj.id,
            'name': class_obj.name,
            'subject': class_obj.subject,
        },
        'folders': tree,
        'folders_flat': _flatten_folders(tree),
        'root_items': [_serialize_item(i) for i in root_items],
        'can_manage': can_manage,
        'allowed_extensions': sorted(NOTES_ALLOWED_EXTENSIONS),
        'max_video_seconds': NOTES_MAX_VIDEO_SECONDS,
        'max_folder_depth': NOTES_MAX_FOLDER_DEPTH,
    }, None, 200


def create_class_notes_folder(
    class_id: int,
    *,
    name: str,
    description: str | None = None,
    parent_id: int | None = None,
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can create folders.', 403

    clean_name = (name or '').strip()
    if not clean_name:
        return None, 'Folder name is required.', 400
    if len(clean_name) > 200:
        return None, 'Folder name is too long.', 400

    parent = None
    if parent_id is not None:
        parent = ClassNotesFolder.query.filter_by(id=parent_id, class_id=class_id).first()
        if not parent:
            return None, 'Parent folder not found.', 404
        if _folder_depth(parent) >= NOTES_MAX_FOLDER_DEPTH:
            return (
                None,
                f'Folders can only nest {NOTES_MAX_FOLDER_DEPTH} levels deep '
                '(Unit → Lesson → materials).',
                400,
            )

    max_order = (
        db.session.query(db.func.max(ClassNotesFolder.sort_order))
        .filter_by(class_id=class_id, parent_id=parent_id)
        .scalar()
    )
    folder = ClassNotesFolder(
        class_id=class_id,
        parent_id=parent_id,
        name=clean_name,
        description=(description or '').strip() or None,
        sort_order=(max_order or 0) + 1,
        created_by_user_id=current_user.id,
    )
    db.session.add(folder)
    db.session.commit()
    payload, _, _ = get_class_notes_payload(class_id)
    return {
        'success': True,
        'message': 'Folder created.',
        'folder_id': folder.id,
        **(payload or {}),
    }, None, 201


def update_class_notes_folder(
    class_id: int,
    folder_id: int,
    *,
    name: str | None = None,
    description: str | None = None,
    parent_id: int | None | object = ...,
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can edit folders.', 403

    folder = ClassNotesFolder.query.filter_by(id=folder_id, class_id=class_id).first()
    if not folder:
        return None, 'Folder not found', 404

    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            return None, 'Folder name is required.', 400
        folder.name = clean_name
    if description is not None:
        folder.description = description.strip() or None

    if parent_id is not ...:
        new_parent_id = parent_id
        if new_parent_id is not None:
            new_parent = ClassNotesFolder.query.filter_by(
                id=int(new_parent_id), class_id=class_id
            ).first()
            if not new_parent:
                return None, 'Parent folder not found.', 404
            if _would_cycle(folder, int(new_parent_id)):
                return None, 'Cannot move a folder into itself or a descendant.', 400
            # Depth of moved folder subtree: current depth relative + new parent depth
            subtree_height = 1

            def _height(node: ClassNotesFolder) -> int:
                kids = ClassNotesFolder.query.filter_by(
                    class_id=class_id, parent_id=node.id
                ).all()
                if not kids:
                    return 1
                return 1 + max(_height(k) for k in kids)

            subtree_height = _height(folder)
            if _folder_depth(new_parent) + subtree_height > NOTES_MAX_FOLDER_DEPTH:
                return (
                    None,
                    f'Move would exceed the {NOTES_MAX_FOLDER_DEPTH}-level folder limit.',
                    400,
                )
            folder.parent_id = int(new_parent_id)
        else:
            folder.parent_id = None

    folder.updated_at = datetime.utcnow()
    db.session.commit()
    payload, _, _ = get_class_notes_payload(class_id)
    return {
        'success': True,
        'message': 'Folder updated.',
        **(payload or {}),
    }, None, 200


def _delete_folder_recursive(folder: ClassNotesFolder) -> None:
    children = ClassNotesFolder.query.filter_by(
        class_id=folder.class_id, parent_id=folder.id
    ).all()
    for child in children:
        _delete_folder_recursive(child)
    for item in list(folder.items or []):
        _delete_item_file(item)
    db.session.delete(folder)


def delete_class_notes_folder(
    class_id: int, folder_id: int
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can remove folders.', 403

    folder = ClassNotesFolder.query.filter_by(id=folder_id, class_id=class_id).first()
    if not folder:
        return None, 'Folder not found', 404

    _delete_folder_recursive(folder)
    db.session.commit()
    payload, _, _ = get_class_notes_payload(class_id)
    return {
        'success': True,
        'message': 'Folder removed.',
        **(payload or {}),
    }, None, 200


def upload_class_notes_item(
    class_id: int,
    file_storage,
    *,
    folder_id: int | None = None,
    title: str | None = None,
    duration_seconds: float | None = None,
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can upload class notes.', 403
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None, 'Choose a file to upload.', 400

    filename = secure_filename(file_storage.filename)
    ok, err, ext = validate_notes_extension(filename)
    if not ok:
        return None, err or 'Invalid file', 400

    if folder_id is not None:
        folder = ClassNotesFolder.query.filter_by(id=folder_id, class_id=class_id).first()
        if not folder:
            return None, 'Folder not found', 404

    upload_dir = _notes_upload_dir()
    stored = f"class_{class_id}_{uuid.uuid4().hex[:12]}.{ext}"
    abs_path = os.path.join(upload_dir, stored)
    file_storage.save(abs_path)

    kind = notes_media_kind(ext)
    duration: float | None = None
    if kind == 'video':
        probed = probe_video_duration_seconds(abs_path, ext)
        claimed = None
        if duration_seconds is not None:
            try:
                claimed = float(duration_seconds)
            except (TypeError, ValueError):
                claimed = None
        duration = probed if probed is not None else claimed
        if duration is None:
            try:
                os.remove(abs_path)
            except OSError:
                pass
            return (
                None,
                'Could not read video length. Use MP4 when possible, or a video under 10 minutes.',
                400,
            )
        if duration > NOTES_MAX_VIDEO_SECONDS + 1:
            try:
                os.remove(abs_path)
            except OSError:
                pass
            return None, 'Videos must be 10 minutes or shorter.', 400

    clean_title = (title or '').strip() or filename.rsplit('.', 1)[0]
    if len(clean_title) > 255:
        clean_title = clean_title[:255]

    try:
        size = os.path.getsize(abs_path)
    except OSError:
        size = None

    item = ClassNotesItem(
        class_id=class_id,
        folder_id=folder_id,
        title=clean_title,
        original_filename=filename,
        stored_filename=stored,
        relative_path=f'class_notes/{stored}',
        content_type=getattr(file_storage, 'mimetype', None),
        file_size=size,
        media_kind=kind,
        duration_seconds=duration,
        uploaded_by_user_id=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    payload, _, _ = get_class_notes_payload(class_id)
    return {
        'success': True,
        'message': 'File uploaded.',
        'item': _serialize_item(item),
        **(payload or {}),
    }, None, 201


def upload_class_notes_items_bulk(
    class_id: int,
    file_storages: list,
    *,
    folder_id: int | None = None,
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can upload class notes.', 403
    if folder_id is not None:
        folder = ClassNotesFolder.query.filter_by(id=folder_id, class_id=class_id).first()
        if not folder:
            return None, 'Folder not found', 404

    named = [f for f in file_storages if f and getattr(f, 'filename', None)]
    if not named:
        return None, 'Choose at least one file to upload.', 400

    results: list[dict[str, Any]] = []
    ok_count = 0
    for file_storage in named:
        item_payload, err, status = upload_class_notes_item(
            class_id,
            file_storage,
            folder_id=folder_id,
        )
        if err:
            results.append(
                {
                    'ok': False,
                    'filename': getattr(file_storage, 'filename', None),
                    'error': err,
                    'status': status,
                }
            )
        else:
            ok_count += 1
            results.append(
                {
                    'ok': True,
                    'filename': getattr(file_storage, 'filename', None),
                    'item': (item_payload or {}).get('item'),
                }
            )

    payload, _, _ = get_class_notes_payload(class_id)
    return {
        'success': ok_count > 0,
        'message': f'Uploaded {ok_count} of {len(named)} file(s).',
        'results': results,
        **(payload or {}),
    }, None, 200 if ok_count > 0 else 400


def delete_class_notes_item(
    class_id: int, item_id: int
) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_manage_class_notes(class_obj):
        return None, 'Only teachers and administrators can remove files.', 403

    item = ClassNotesItem.query.filter_by(id=item_id, class_id=class_id).first()
    if not item:
        return None, 'File not found', 404

    _delete_item_file(item)
    db.session.delete(item)
    db.session.commit()
    payload, _, _ = get_class_notes_payload(class_id)
    return {
        'success': True,
        'message': 'File removed.',
        **(payload or {}),
    }, None, 200


def download_class_notes_item(class_id: int, item_id: int):
    ensure_class_notes_tables()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not _user_can_view_class_notes(class_obj):
        return None, 'Access denied', 403

    item = ClassNotesItem.query.filter_by(id=item_id, class_id=class_id).first()
    if not item:
        return None, 'File not found', 404

    root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(
        current_app.root_path, 'static', 'uploads'
    )
    directory = os.path.join(root, 'class_notes')
    as_attachment = item.media_kind != 'video'
    try:
        return (
            send_from_directory(
                directory,
                item.stored_filename,
                as_attachment=as_attachment,
                download_name=item.original_filename,
            ),
            None,
            200,
        )
    except Exception:
        return None, 'File missing on disk', 404
