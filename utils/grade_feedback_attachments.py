"""Grade feedback file attachments (PDF/paper teacher comments)."""

from __future__ import annotations

import os
import uuid
from typing import Any

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models import Grade, GradeAttachment, db


def feedback_attachments_payload(
    grade: Grade | None,
    *,
    download_url_for_id,
) -> list[dict[str, Any]]:
    if not grade or not getattr(grade, "id", None):
        return []
    rows = (
        GradeAttachment.query.filter_by(grade_id=grade.id)
        .order_by(GradeAttachment.sort_order, GradeAttachment.id)
        .all()
    )
    out: list[dict[str, Any]] = []
    for att in rows:
        out.append(
            {
                "id": att.id,
                "name": att.attachment_original_filename or att.attachment_filename,
                "size": att.attachment_file_size,
                "mime_type": att.attachment_mime_type,
                "url": download_url_for_id(att.id),
            }
        )
    return out


def _upload_root() -> str:
    root = current_app.config.get("UPLOAD_FOLDER") or os.path.join(
        current_app.root_path, "static", "uploads"
    )
    dest = os.path.join(root, "grade_feedback")
    os.makedirs(dest, exist_ok=True)
    return dest


def _delete_attachment_file(att: GradeAttachment) -> None:
    path = att.attachment_file_path
    if not path:
        return
    root = current_app.config.get("UPLOAD_FOLDER") or ""
    full = path if os.path.isabs(path) else os.path.join(root, path)
    try:
        if os.path.isfile(full):
            os.remove(full)
    except OSError:
        current_app.logger.warning("Could not delete grade feedback file %s", full)


def apply_grade_feedback_attachments(
    grade: Grade,
    *,
    files: list[FileStorage] | None = None,
    remove_ids: list[int] | None = None,
) -> None:
    """Remove selected attachments and/or append new uploaded feedback files."""
    if remove_ids:
        for att in GradeAttachment.query.filter(
            GradeAttachment.grade_id == grade.id,
            GradeAttachment.id.in_([int(x) for x in remove_ids if str(x).isdigit() or isinstance(x, int)]),
        ).all():
            _delete_attachment_file(att)
            db.session.delete(att)

    files = files or []
    if not files:
        return

    dest_dir = _upload_root()
    existing = GradeAttachment.query.filter_by(grade_id=grade.id).count()
    for index, storage in enumerate(files):
        if not storage or not getattr(storage, "filename", None):
            continue
        original = storage.filename or "feedback.bin"
        safe = secure_filename(original) or "feedback.bin"
        unique = f"{uuid.uuid4().hex}_{safe}"
        abs_path = os.path.join(dest_dir, unique)
        storage.save(abs_path)
        rel_path = os.path.join("grade_feedback", unique).replace("\\", "/")
        size = None
        try:
            size = os.path.getsize(abs_path)
        except OSError:
            size = None
        db.session.add(
            GradeAttachment(
                grade_id=grade.id,
                attachment_filename=unique,
                attachment_original_filename=original[:255],
                attachment_file_path=rel_path,
                attachment_file_size=size,
                attachment_mime_type=(getattr(storage, "mimetype", None) or "")[:100] or None,
                sort_order=existing + index,
            )
        )


def resolve_grade_attachment_abs_path(att: GradeAttachment) -> str | None:
    path = att.attachment_file_path
    if not path:
        return None
    if os.path.isabs(path) and os.path.isfile(path):
        return path
    root = current_app.config.get("UPLOAD_FOLDER") or ""
    full = os.path.join(root, path)
    return full if os.path.isfile(full) else None
