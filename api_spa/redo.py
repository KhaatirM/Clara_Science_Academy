"""Redo dashboard API for the React management SPA."""

from __future__ import annotations

import json
from datetime import datetime

from flask import current_app, jsonify, request, url_for
from flask_login import current_user, login_required

from decorators import is_teacher_role, permissions_required, user_can_manage_assignments_and_grades
from extensions import db
from management_routes.extensions_redo_spa_helpers import query_redo_dashboard
from models import (
    Assignment,
    AssignmentReopening,
    AssignmentRedo,
    Grade,
    RedoRequest,
    Submission,
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
@permissions_required("assignments_grades:manage")
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

    try:
        redo_deadline = datetime.strptime(redo_deadline_str, "%Y-%m-%d")
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id) if current_user.teacher_staff_id else None

        submission = Submission.query.filter_by(
            student_id=req.student_id,
            assignment_id=req.assignment_id,
        ).first()
        has_submitted = submission is not None and submission.submission_type != "not_submitted"

        if has_submitted:
            existing = AssignmentRedo.query.filter_by(
                assignment_id=req.assignment_id,
                student_id=req.student_id,
            ).first()
            if existing:
                req.status = "Approved"
                req.reviewed_at = datetime.utcnow()
                req.reviewed_by = teacher.id if teacher else None
                db.session.commit()
                return jsonify({"success": True, "message": "Redo already granted for this student."})

            grade = (
                Grade.query.filter_by(student_id=req.student_id, assignment_id=req.assignment_id)
                .order_by(Grade.graded_at.desc())
                .first()
            )
            orig_grade = None
            if grade and grade.grade_data:
                try:
                    gd = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                    orig_grade = gd.get("score") or gd.get("points_earned")
                except (TypeError, json.JSONDecodeError):
                    pass

            redo_rec = AssignmentRedo(
                assignment_id=req.assignment_id,
                student_id=req.student_id,
                granted_by=teacher.id if teacher else None,
                redo_deadline=redo_deadline,
                reason=req.reason or "Granted from redo request",
                original_grade=orig_grade,
            )
            db.session.add(redo_rec)
        else:
            existing = AssignmentReopening.query.filter_by(
                assignment_id=req.assignment_id,
                student_id=req.student_id,
                is_active=True,
            ).first()
            if existing:
                req.status = "Approved"
                req.reviewed_at = datetime.utcnow()
                req.reviewed_by = teacher.id if teacher else None
                db.session.commit()
                return jsonify({"success": True, "message": "Reopening already granted for this student."})

            reopening = AssignmentReopening(
                assignment_id=req.assignment_id,
                student_id=req.student_id,
                reopened_by=teacher.id if teacher else None,
                is_active=True,
                additional_attempts=0,
            )
            db.session.add(reopening)

        req.status = "Approved"
        req.reviewed_at = datetime.utcnow()
        req.reviewed_by = teacher.id if teacher else None
        db.session.commit()

        if req.student and req.student.user:
            from app import create_notification

            create_notification(
                user_id=req.student.user.id,
                notification_type="assignment",
                title=f"Redo Granted: {assignment.title}",
                message=(
                    f'Your teacher granted a redo for "{assignment.title}". '
                    f'New deadline: {redo_deadline.strftime("%m/%d/%Y")}.'
                ),
                link=url_for("student.student_assignments"),
            )

        return jsonify({"success": True, "message": "Redo granted successfully. The student has been notified."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@spa_api_blueprint.route("/redo-requests/<int:request_id>/reject", methods=["POST"])
@login_required
@permissions_required("assignments_grades:manage")
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
@permissions_required("assignments_grades:manage")
def redo_revoke(redo_id: int):
    redo = AssignmentRedo.query.get_or_404(redo_id)

    if current_user.role == "Teacher":
        if current_user.teacher_staff_id:
            teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
            if not redo.assignment or not redo.assignment.class_info or redo.assignment.class_info.teacher_id != teacher.id:
                return jsonify({"success": False, "message": "You can only revoke redos for your own classes."}), 403
        else:
            return jsonify({"success": False, "message": "Teacher record not found."}), 403
    elif not user_can_manage_assignments_and_grades(current_user):
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
