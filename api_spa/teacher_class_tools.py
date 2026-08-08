"""Teacher-scoped class tools, groups, standards, assistant, and Google Classroom APIs."""

from __future__ import annotations

from datetime import datetime

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import teacher_required
from extensions import db
from models import Assignment, Class, GroupAssignment
from teacher_routes.utils import is_authorized_for_class

from . import spa_api_blueprint


def _require_class(class_id: int) -> tuple[Class | None, tuple | None]:
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None, (jsonify({"error": "Class not found"}), 404)
    if not is_authorized_for_class(class_obj):
        return None, (jsonify({"error": "Forbidden"}), 403)
    return class_obj, None


@spa_api_blueprint.route("/teacher/attendance/take/<int:class_id>/csv-template")
@login_required
@teacher_required
def teacher_attendance_csv_template(class_id: int):
    from management_routes.attendance_csv_template import build_attendance_csv_template_response

    _, err = _require_class(class_id)
    if err:
        return err
    return build_attendance_csv_template_response(class_id)


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/tools/<tool>")
@login_required
@teacher_required
def teacher_class_tool(class_id: int, tool: str):
    from management_routes.class_tools_spa_helpers import CLASS_TOOL_SLUGS, query_class_tool

    _, err = _require_class(class_id)
    if err:
        return err
    if tool not in CLASS_TOOL_SLUGS and tool != "analytics":
        return jsonify({"success": False, "message": "Unknown tool."}), 404
    try:
        return jsonify(query_class_tool(class_id, tool))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/deadline-reminders/hub")
@login_required
@teacher_required
def teacher_deadline_reminders_hub(class_id: int):
    from management_routes.deadline_reminders_spa_helpers import query_deadline_reminders_hub

    _, err = _require_class(class_id)
    if err:
        return err
    return jsonify(query_deadline_reminders_hub(class_id))


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/tools/deadline-reminders")
@login_required
@teacher_required
def teacher_deadline_reminders_tool(class_id: int):
    from management_routes.class_tools_spa_helpers import query_class_tool

    _, err = _require_class(class_id)
    if err:
        return err
    return jsonify(query_class_tool(class_id, "deadline-reminders"))


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/deadline-reminders/form")
@login_required
@teacher_required
def teacher_deadline_form(class_id: int):
    from management_routes.deadline_reminders_spa_helpers import query_deadline_reminder_form

    _, err = _require_class(class_id)
    if err:
        return err
    return jsonify(query_deadline_reminder_form(class_id))


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/deadline-reminders/<int:reminder_id>/form")
@login_required
@teacher_required
def teacher_deadline_edit_form(class_id: int, reminder_id: int):
    from management_routes.deadline_reminders_spa_helpers import query_deadline_reminder_form

    _, err = _require_class(class_id)
    if err:
        return err
    return jsonify(query_deadline_reminder_form(class_id, reminder_id))


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/deadline-reminders", methods=["POST"])
@login_required
@teacher_required
def teacher_deadline_create(class_id: int):
    from management_routes.deadline_reminders_spa_helpers import create_deadline_reminder

    _, err = _require_class(class_id)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    result = create_deadline_reminder(class_id, body)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/deadline-reminders/<int:reminder_id>", methods=["PUT"])
@login_required
@teacher_required
def teacher_deadline_update(class_id: int, reminder_id: int):
    from management_routes.deadline_reminders_spa_helpers import update_deadline_reminder

    _, err = _require_class(class_id)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    result = update_deadline_reminder(class_id, reminder_id, body)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route(
    "/teacher/classes/<int:class_id>/deadline-reminders/<int:reminder_id>/toggle",
    methods=["POST"],
)
@login_required
@teacher_required
def teacher_deadline_toggle(class_id: int, reminder_id: int):
    from management_routes.deadline_reminders_spa_helpers import toggle_deadline_reminder

    _, err = _require_class(class_id)
    if err:
        return err
    result = toggle_deadline_reminder(class_id, reminder_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route(
    "/teacher/classes/<int:class_id>/deadline-reminders/<int:reminder_id>/send-now",
    methods=["POST"],
)
@login_required
@teacher_required
def teacher_deadline_send(class_id: int, reminder_id: int):
    from management_routes.deadline_reminders_spa_helpers import send_deadline_reminder_now

    _, err = _require_class(class_id)
    if err:
        return err
    result = send_deadline_reminder_now(class_id, reminder_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route(
    "/teacher/classes/<int:class_id>/deadline-reminders/<int:reminder_id>",
    methods=["DELETE"],
)
@login_required
@teacher_required
def teacher_deadline_delete(class_id: int, reminder_id: int):
    from management_routes.deadline_reminders_spa_helpers import delete_deadline_reminder

    _, err = _require_class(class_id)
    if err:
        return err
    result = delete_deadline_reminder(class_id, reminder_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/google-classroom/options")
@login_required
@teacher_required
def teacher_google_options(class_id: int):
    from management_routes.class_spa_helpers import google_classroom_options

    _, err = _require_class(class_id)
    if err:
        return err
    return jsonify(google_classroom_options(class_id))


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/google-classroom", methods=["POST"])
@login_required
@teacher_required
def teacher_google_action(class_id: int):
    from management_routes.class_spa_helpers import google_classroom_action

    _, err = _require_class(class_id)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").strip()
    google_id = body.get("google_classroom_id")
    result = google_classroom_action(class_id, action, google_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/standards/<grade>")
@login_required
@teacher_required
def teacher_standards_get(class_id: int, grade: str):
    from management_routes.grade_standards_spa_helpers import query_grade_standards_editor

    _, err = _require_class(class_id)
    if err:
        return err
    if grade in ("gradek", "kindergarten", "k", "0"):
        grade_num = 0
    elif grade in ("grade1", "1"):
        grade_num = 1
    elif grade in ("grade2", "2"):
        grade_num = 2
    else:
        grade_num = 3
    student_raw = request.args.get("student_id")
    student_id = int(student_raw) if student_raw and str(student_raw).isdigit() else None
    return jsonify(
        query_grade_standards_editor(
            grade_num,
            class_id,
            quarter=request.args.get("quarter"),
            view=request.args.get("view") or "grid",
            student_id=student_id,
        )
    )


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/standards/<grade>", methods=["POST"])
@login_required
@teacher_required
def teacher_standards_post(class_id: int, grade: str):
    from management_routes.grade_standards_spa_helpers import apply_grade_standards_changes

    _, err = _require_class(class_id)
    if err:
        return err
    if grade in ("gradek", "kindergarten", "k", "0"):
        grade_num = 0
    elif grade in ("grade1", "1"):
        grade_num = 1
    elif grade in ("grade2", "2"):
        grade_num = 2
    else:
        grade_num = 3
    body = request.get_json(silent=True) or {}
    result = apply_grade_standards_changes(grade_num, class_id, body, current_user.id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/assistant-approvals")
@login_required
@teacher_required
def teacher_assistant_approvals_list(class_id: int):
    from management_routes.student_assistant_utils import ASSISTANT_APPROVAL_PENDING

    class_obj, err = _require_class(class_id)
    if err:
        return err

    pending_individual = (
        Assignment.query.filter(
            Assignment.class_id == class_id,
            Assignment.assistant_approval_status == ASSISTANT_APPROVAL_PENDING,
        )
        .order_by(Assignment.created_at.desc())
        .all()
    )
    pending_group = (
        GroupAssignment.query.filter(
            GroupAssignment.class_id == class_id,
            GroupAssignment.assistant_approval_status == ASSISTANT_APPROVAL_PENDING,
        )
        .order_by(GroupAssignment.created_at.desc())
        .all()
    )

    def _row(a, *, is_group: bool) -> dict:
        return {
            "id": a.id,
            "is_group": is_group,
            "title": a.title or "Untitled",
            "assignment_type": getattr(a, "assignment_type", None) or ("group" if is_group else "pdf"),
            "status": a.status or "",
            "created_at": a.created_at.isoformat() if getattr(a, "created_at", None) else None,
            "due_date": a.due_date.isoformat() if getattr(a, "due_date", None) else None,
        }

    return jsonify(
        {
            "class": {"id": class_obj.id, "name": class_obj.name},
            "pending_individual": [_row(a, is_group=False) for a in pending_individual],
            "pending_group": [_row(a, is_group=True) for a in pending_group],
        }
    )


@spa_api_blueprint.route(
    "/teacher/classes/<int:class_id>/assistant-approvals/<int:assignment_id>/approve",
    methods=["POST"],
)
@login_required
@teacher_required
def teacher_assistant_approve(class_id: int, assignment_id: int):
    from management_routes.student_assistant_utils import (
        ASSISTANT_APPROVAL_APPROVED,
        ASSISTANT_APPROVAL_PENDING,
    )

    _, err = _require_class(class_id)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    is_group = bool(body.get("is_group"))
    publish_status = body.get("publish_status") or "Active"
    if publish_status not in ("Active", "Inactive", "Upcoming"):
        publish_status = "Active"

    if is_group:
        a = GroupAssignment.query.filter_by(id=assignment_id, class_id=class_id).first_or_404()
    else:
        a = Assignment.query.filter_by(id=assignment_id, class_id=class_id).first_or_404()

    if a.assistant_approval_status != ASSISTANT_APPROVAL_PENDING:
        return jsonify({"success": False, "message": "This assignment is not pending approval."}), 400

    a.assistant_approval_status = ASSISTANT_APPROVAL_APPROVED
    a.assistant_approval_reviewed_by_user_id = current_user.id
    a.assistant_approval_reviewed_at = datetime.utcnow()
    a.assistant_approval_review_notes = None
    a.status = publish_status
    db.session.commit()
    return jsonify({"success": True, "message": "Assignment approved."})


@spa_api_blueprint.route(
    "/teacher/classes/<int:class_id>/assistant-approvals/<int:assignment_id>/reject",
    methods=["POST"],
)
@login_required
@teacher_required
def teacher_assistant_reject(class_id: int, assignment_id: int):
    from management_routes.student_assistant_utils import (
        ASSISTANT_APPROVAL_PENDING,
        ASSISTANT_APPROVAL_REJECTED,
    )

    _, err = _require_class(class_id)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    is_group = bool(body.get("is_group"))
    notes = (body.get("notes") or "").strip() or None

    if is_group:
        a = GroupAssignment.query.filter_by(id=assignment_id, class_id=class_id).first_or_404()
    else:
        a = Assignment.query.filter_by(id=assignment_id, class_id=class_id).first_or_404()

    if a.assistant_approval_status != ASSISTANT_APPROVAL_PENDING:
        return jsonify({"success": False, "message": "This assignment is not pending approval."}), 400

    a.assistant_approval_status = ASSISTANT_APPROVAL_REJECTED
    a.assistant_approval_reviewed_by_user_id = current_user.id
    a.assistant_approval_reviewed_at = datetime.utcnow()
    a.assistant_approval_review_notes = notes
    a.status = "Inactive"
    db.session.commit()
    return jsonify({"success": True, "message": "Assignment rejected."})
