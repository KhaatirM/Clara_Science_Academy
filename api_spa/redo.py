"""Redo dashboard API for the React management SPA."""

from __future__ import annotations

from datetime import datetime

from flask import jsonify, request, url_for
from flask_login import current_user, login_required

from decorators import is_teacher_role, permissions_required, user_can_manage_assignments_and_grades
from extensions import db
from management_routes.extensions_redo_spa_helpers import query_redo_dashboard
from models import (
    Assignment,
    AssignmentRedo,
    RedoRequest,
    TeacherStaff,
    class_additional_teachers,
    class_substitute_teachers,
)

from . import spa_api_blueprint


def _redo_request_authorized(assignment: Assignment) -> tuple[bool, str | None]:
    is_teacher = is_teacher_role(current_user.role)
    is_admin = user_can_manage_assignments_and_grades(current_user)

    if is_teacher:
        if not current_user.teacher_staff_id:
            return False, "Teacher record not found."
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        class_obj = assignment.class_info
        if not teacher or not class_obj:
            return False, "Assignment class not found."
        is_authorized = (
            class_obj.teacher_id == teacher.id
            or db.session.query(class_additional_teachers)
            .filter(
                class_additional_teachers.c.class_id == class_obj.id,
                class_additional_teachers.c.teacher_id == teacher.id,
            )
            .count()
            > 0
            or db.session.query(class_substitute_teachers)
            .filter(
                class_substitute_teachers.c.class_id == class_obj.id,
                class_substitute_teachers.c.teacher_id == teacher.id,
            )
            .count()
            > 0
        )
        if not is_authorized:
            return False, "You can only manage redos for your own classes."
        return True, None
    if is_admin:
        return True, None
    return False, "You are not authorized."


@spa_api_blueprint.route("/redo-dashboard")
@login_required
@permissions_required("assignments_grades:manage")
def redo_dashboard_api():
    return jsonify(query_redo_dashboard())


@spa_api_blueprint.route("/redo-requests/<int:request_id>/grant", methods=["POST"])
@login_required
def redo_request_grant(request_id: int):
    req = RedoRequest.query.get_or_404(request_id)
    if req.status != "Pending":
        return jsonify({"success": False, "message": "This request has already been reviewed."})

    assignment = Assignment.query.get_or_404(req.assignment_id)
    ok, err = _redo_request_authorized(assignment)
    if not ok:
        return jsonify({"success": False, "message": err}), 403

    payload = request.get_json(silent=True) or {}
    redo_deadline_str = (payload.get("redo_deadline") or request.form.get("redo_deadline") or "").strip()
    if not redo_deadline_str:
        return jsonify({"success": False, "message": "Please provide a redo deadline."}), 400

    raw_attempts = payload.get("additional_attempts", request.form.get("additional_attempts"))
    try:
        additional_attempts = int(raw_attempts) if raw_attempts not in (None, "") else 1
    except (TypeError, ValueError):
        additional_attempts = 1
    additional_attempts = max(1, min(20, additional_attempts))

    raw_review = payload.get(
        "allow_review_previous_attempts",
        request.form.get("allow_review_previous_attempts"),
    )
    if isinstance(raw_review, bool):
        allow_review_previous_attempts = raw_review
    elif raw_review is None or raw_review == "":
        allow_review_previous_attempts = False
    else:
        allow_review_previous_attempts = str(raw_review).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    try:
        from utils.redo_grant import grant_redo_access_for_request, parse_redo_deadline_end_of_day

        redo_deadline = parse_redo_deadline_end_of_day(redo_deadline_str)
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id) if current_user.teacher_staff_id else None

        result = grant_redo_access_for_request(
            assignment=assignment,
            student_id=req.student_id,
            teacher=teacher,
            redo_deadline=redo_deadline,
            reason=req.reason or "Granted from redo request",
            additional_attempts=additional_attempts,
            allow_review_previous_attempts=allow_review_previous_attempts,
        )

        req.status = "Approved"
        req.reviewed_at = datetime.utcnow()
        req.reviewed_by = teacher.id if teacher else None
        db.session.commit()

        if req.student and req.student.user:
            from app import create_notification

            kind = result.get("kind")
            if kind == "quiz":
                n = int(result.get("attempts_granted") or additional_attempts or 1)
                access_note = (
                    f"You have {n} additional quiz attempt{'s' if n != 1 else ''}"
                )
            elif kind == "discussion":
                access_note = "Discussion posting is open again"
            else:
                access_note = "The assignment is open again"
            create_notification(
                user_id=req.student.user.id,
                notification_type="assignment",
                title=f"Redo Granted: {assignment.title}",
                message=(
                    f'Your teacher granted a redo for "{assignment.title}". '
                    f"{access_note} until {redo_deadline.strftime('%m/%d/%Y')}."
                ),
                link=url_for("student.student_assignments"),
            )

        already = bool(result.get("already"))
        message = (
            "Redo already on file; deadline and access were refreshed. The student has been notified."
            if already
            else "Redo granted successfully. The student has been notified."
        )
        return jsonify({"success": True, "message": message})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@spa_api_blueprint.route("/redo-requests/<int:request_id>/reject", methods=["POST"])
@login_required
def redo_request_reject(request_id: int):
    req = RedoRequest.query.get_or_404(request_id)
    if req.status != "Pending":
        return jsonify({"success": False, "message": "This request has already been reviewed."})

    assignment = Assignment.query.get_or_404(req.assignment_id)
    ok, err = _redo_request_authorized(assignment)
    if not ok:
        return jsonify({"success": False, "message": err}), 403

    teacher = TeacherStaff.query.get(current_user.teacher_staff_id) if current_user.teacher_staff_id else None
    req.status = "Rejected"
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = teacher.id if teacher else None
    try:
        db.session.commit()
        if req.student and req.student.user:
            from app import create_notification

            create_notification(
                user_id=req.student.user.id,
                notification_type="assignment",
                title=f"Redo Request Declined: {assignment.title}",
                message=f'Your redo request for "{assignment.title}" was not approved.',
                link=url_for("student.student_assignments"),
            )
        return jsonify({"success": True, "message": "Redo request rejected."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@spa_api_blueprint.route("/redos/<int:redo_id>/revoke", methods=["POST"])
@login_required
def redo_revoke(redo_id: int):
    redo = AssignmentRedo.query.get_or_404(redo_id)

    if user_can_manage_assignments_and_grades(current_user):
        pass
    elif is_teacher_role(current_user.role):
        from teacher_routes.utils import is_authorized_for_class

        if not redo.assignment or not redo.assignment.class_info:
            return jsonify({"success": False, "message": "Assignment class not found."}), 403
        if not is_authorized_for_class(redo.assignment.class_info):
            return jsonify({"success": False, "message": "You can only revoke redos for your own classes."}), 403
    else:
        return jsonify({"success": False, "message": "You are not authorized to revoke redos."}), 403

    if redo.is_used:
        return jsonify({"success": False, "message": "Cannot revoke a redo that has already been used."}), 400

    try:
        if redo.student and redo.student.user:
            from app import create_notification

            create_notification(
                user_id=redo.student.user.id,
                notification_type="assignment",
                title=f"Redo Revoked: {redo.assignment.title}",
                message=f'Your redo permission for "{redo.assignment.title}" has been revoked.',
                link=url_for("student.student_assignments"),
            )

        db.session.delete(redo)
        db.session.commit()
        return jsonify({"success": True, "message": "Redo permission revoked successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error revoking redo: {e}"}), 500
