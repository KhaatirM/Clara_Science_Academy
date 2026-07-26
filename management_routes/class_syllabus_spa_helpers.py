"""Class syllabus SPA helpers: load, upload, outline, download."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any

from flask import current_app, send_from_directory
from flask_login import current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Class, ClassSyllabus, Enrollment
from utils.syllabus_outline import (
    SYLLABUS_ALLOWED_EXTENSIONS,
    build_outline_from_text,
    extract_text_from_file,
    outline_from_json,
    outline_to_json,
)
from utils.upload_validation import validate_upload_file
from utils.user_roles import user_has_management_entry_access

# Middle school starts at grade 6; elementary is K–5 (0–5).
SYLLABUS_MIN_GRADE = 6


def class_supports_syllabus(class_obj: Class | None) -> bool:
    """Syllabus is for middle school and high school classes only (grade 6+)."""
    if not class_obj:
        return False
    levels = class_obj.get_grade_levels() if hasattr(class_obj, 'get_grade_levels') else []
    return any(int(g) >= SYLLABUS_MIN_GRADE for g in (levels or []))


def ensure_class_syllabus_table() -> None:
    try:
        ClassSyllabus.__table__.create(db.engine, checkfirst=True)
    except Exception:
        current_app.logger.exception('Could not ensure class_syllabus table')


def _syllabus_upload_dir() -> str:
    root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(
        current_app.root_path, 'static', 'uploads'
    )
    path = os.path.join(root, 'syllabi')
    os.makedirs(path, exist_ok=True)
    return path


def _user_can_manage_class_syllabus(class_obj: Class) -> bool:
    if user_has_management_entry_access(current_user):
        return True
    try:
        from teacher_routes.utils import is_authorized_for_class

        return bool(is_authorized_for_class(class_obj))
    except Exception:
        return False


def _user_can_view_class_syllabus(class_obj: Class) -> bool:
    if not class_supports_syllabus(class_obj):
        return False
    if _user_can_manage_class_syllabus(class_obj):
        return True
    # Enrolled student
    student = getattr(current_user, 'student_profile', None)
    if not student:
        return False
    return (
        Enrollment.query.filter_by(
            class_id=class_obj.id, student_id=student.id, is_active=True
        ).first()
        is not None
    )


def _syllabus_not_available_error() -> tuple[None, str, int]:
    return None, 'Syllabus is only available for middle school and high school classes (grade 6 and up).', 404


def _serialize_syllabus(row: ClassSyllabus | None, *, can_manage: bool) -> dict[str, Any] | None:
    if not row:
        return None
    outline = outline_from_json(row.outline_json) or {
        'title': row.original_filename,
        'sections': [],
    }
    return {
        'id': row.id,
        'class_id': row.class_id,
        'original_filename': row.original_filename,
        'content_type': row.content_type,
        'file_size': row.file_size,
        'download_url': f'/api/spa/classes/{row.class_id}/syllabus/download',
        'uploaded_at': row.uploaded_at.isoformat() if row.uploaded_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        'uploaded_by': (
            row.uploaded_by.username if row.uploaded_by else None
        ),
        'outline': outline,
        'can_manage': can_manage,
        'has_file': bool(row.relative_path),
    }


def get_class_syllabus_payload(class_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_syllabus_table()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not class_supports_syllabus(class_obj):
        return _syllabus_not_available_error()
    if not _user_can_view_class_syllabus(class_obj):
        return None, 'Access denied', 403

    can_manage = _user_can_manage_class_syllabus(class_obj)
    row = ClassSyllabus.query.filter_by(class_id=class_id).first()
    return {
        'class': {
            'id': class_obj.id,
            'name': class_obj.name,
            'subject': class_obj.subject,
        },
        'syllabus': _serialize_syllabus(row, can_manage=can_manage),
        'can_manage': can_manage,
        'allowed_extensions': sorted(SYLLABUS_ALLOWED_EXTENSIONS),
    }, None, 200


def upload_class_syllabus(class_id: int, file_storage) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_syllabus_table()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not class_supports_syllabus(class_obj):
        return _syllabus_not_available_error()
    if not _user_can_manage_class_syllabus(class_obj):
        return None, 'Only teachers and administrators can upload a syllabus.', 403
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None, 'Choose a syllabus file to upload.', 400

    ok, err = validate_upload_file(file_storage)
    if not ok:
        return None, err or 'Invalid file', 400

    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in SYLLABUS_ALLOWED_EXTENSIONS:
        return None, 'Upload a PDF, DOCX, TXT, or Markdown syllabus.', 400

    upload_dir = _syllabus_upload_dir()
    stored = f"class_{class_id}_{uuid.uuid4().hex[:12]}.{ext}"
    abs_path = os.path.join(upload_dir, stored)
    file_storage.save(abs_path)

    try:
        text = extract_text_from_file(abs_path)
        outline = build_outline_from_text(text, source_name=filename.rsplit('.', 1)[0])
    except ValueError as exc:
        try:
            os.remove(abs_path)
        except OSError:
            pass
        return None, str(exc), 400
    except Exception as exc:
        current_app.logger.exception('Syllabus extraction failed')
        try:
            os.remove(abs_path)
        except OSError:
            pass
        return None, f'Could not parse syllabus: {exc}', 400

    if not (text or '').strip():
        try:
            os.remove(abs_path)
        except OSError:
            pass
        return None, 'No readable text found in that file. Try a text-based PDF or DOCX.', 400

    relative = f'syllabi/{stored}'
    row = ClassSyllabus.query.filter_by(class_id=class_id).first()
    old_rel = row.relative_path if row else None

    if not row:
        row = ClassSyllabus(class_id=class_id)
        db.session.add(row)

    row.original_filename = filename
    row.stored_filename = stored
    row.relative_path = relative
    row.content_type = getattr(file_storage, 'mimetype', None) or None
    try:
        row.file_size = os.path.getsize(abs_path)
    except OSError:
        row.file_size = None
    row.outline_json = outline_to_json(outline)
    row.plain_text = text
    row.uploaded_by_user_id = current_user.id
    row.uploaded_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.session.commit()

    if old_rel and old_rel != relative:
        try:
            root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(
                current_app.root_path, 'static', 'uploads'
            )
            candidate = os.path.join(root, old_rel.replace('/', os.sep))
            if os.path.isfile(candidate):
                os.remove(candidate)
        except OSError:
            pass

    payload, _, _ = get_class_syllabus_payload(class_id)
    return {
        'success': True,
        'message': 'Syllabus uploaded and outlined.',
        **(payload or {}),
    }, None, 200


def delete_class_syllabus(class_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    ensure_class_syllabus_table()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not class_supports_syllabus(class_obj):
        return _syllabus_not_available_error()
    if not _user_can_manage_class_syllabus(class_obj):
        return None, 'Only teachers and administrators can remove a syllabus.', 403

    row = ClassSyllabus.query.filter_by(class_id=class_id).first()
    if not row:
        return {'success': True, 'message': 'No syllabus to remove.'}, None, 200

    root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(
        current_app.root_path, 'static', 'uploads'
    )
    abs_path = os.path.join(root, row.relative_path.replace('/', os.sep))
    db.session.delete(row)
    db.session.commit()
    try:
        if os.path.isfile(abs_path):
            os.remove(abs_path)
    except OSError:
        pass
    return {'success': True, 'message': 'Syllabus removed.'}, None, 200


def download_class_syllabus(class_id: int):
    ensure_class_syllabus_table()
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, 'Class not found', 404
    if not class_supports_syllabus(class_obj):
        return _syllabus_not_available_error()
    if not _user_can_view_class_syllabus(class_obj):
        return None, 'Access denied', 403
    row = ClassSyllabus.query.filter_by(class_id=class_id).first()
    if not row:
        return None, 'No syllabus uploaded yet.', 404

    root = current_app.config.get('UPLOAD_FOLDER') or os.path.join(
        current_app.root_path, 'static', 'uploads'
    )
    directory = os.path.join(root, 'syllabi')
    if not os.path.isfile(os.path.join(directory, row.stored_filename)):
        return None, 'Syllabus file missing on server.', 404

    return (
        send_from_directory(
            directory,
            row.stored_filename,
            as_attachment=True,
            download_name=row.original_filename,
        ),
        None,
        200,
    )
