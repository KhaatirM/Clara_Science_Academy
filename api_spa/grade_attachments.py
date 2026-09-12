"""Download routes for grade feedback attachments."""

from __future__ import annotations

import os

from flask import abort, send_file
from flask_login import current_user, login_required

from decorators import student_required
from models import Assignment, Enrollment, Grade, GradeAttachment
from teacher_routes.utils import is_admin, is_authorized_for_class
from utils.grade_feedback_attachments import resolve_grade_attachment_abs_path
from utils.user_roles import user_has_management_entry_access

from . import spa_api_blueprint


def _send_attachment(att: GradeAttachment):
    path = resolve_grade_attachment_abs_path(att)
    if not path:
        abort(404)
    name = att.attachment_original_filename or att.attachment_filename or "feedback.bin"
    return send_file(
        path,
        as_attachment=True,
        download_name=name,
        mimetype=att.attachment_mime_type or "application/octet-stream",
        max_age=0,
    )


def _staff_can_view_grade(grade: Grade) -> bool:
    assignment = Assignment.query.get(grade.assignment_id)
    if not assignment:
        return False
    if user_has_management_entry_access(current_user) or is_admin():
        return True
    class_info = assignment.class_info
    return bool(class_info and is_authorized_for_class(class_info))


@spa_api_blueprint.route("/grade-attachments/<int:attachment_id>/download")
@login_required
def grade_attachment_download(attachment_id: int):
    att = GradeAttachment.query.get_or_404(attachment_id)
    grade = Grade.query.get(att.grade_id)
    if not grade or not _staff_can_view_grade(grade):
        abort(403)
    return _send_attachment(att)


@spa_api_blueprint.route("/student/grade-attachments/<int:attachment_id>/download")
@login_required
@student_required
def student_grade_attachment_download(attachment_id: int):
    att = GradeAttachment.query.get_or_404(attachment_id)
    grade = Grade.query.get(att.grade_id)
    if not grade:
        abort(404)
    student_id = getattr(current_user, "student_id", None)
    if not student_id or grade.student_id != student_id:
        abort(403)
    assignment = Assignment.query.get(grade.assignment_id)
    if not assignment:
        abort(404)
    enrolled = Enrollment.query.filter_by(
        student_id=student_id, class_id=assignment.class_id, is_active=True
    ).first()
    if not enrolled:
        abort(403)
    return _send_attachment(att)
