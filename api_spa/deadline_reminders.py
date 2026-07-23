"""Deadline reminder API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import permissions_required
from management_routes.deadline_reminders_spa_helpers import (
    create_deadline_reminder,
    delete_deadline_reminder,
    query_deadline_reminder_form,
    query_deadline_reminders_hub,
    query_students_needing_reminder,
    send_deadline_reminder_now,
    toggle_deadline_reminder,
    update_deadline_reminder,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/classes/<int:class_id>/deadline-reminders/hub")
@login_required
@permissions_required("classes:manage")
def deadline_reminders_hub(class_id: int):
    return jsonify(query_deadline_reminders_hub(class_id))


@spa_api_blueprint.route("/classes/<int:class_id>/deadline-reminders/form")
@login_required
@permissions_required("classes:manage")
def deadline_reminder_create_form(class_id: int):
    return jsonify(query_deadline_reminder_form(class_id))


@spa_api_blueprint.route("/classes/<int:class_id>/deadline-reminders/<int:reminder_id>/form")
@login_required
@permissions_required("classes:manage")
def deadline_reminder_edit_form(class_id: int, reminder_id: int):
    return jsonify(query_deadline_reminder_form(class_id, reminder_id))


@spa_api_blueprint.route("/classes/<int:class_id>/deadline-reminders", methods=["POST"])
@login_required
@permissions_required("classes:manage")
def deadline_reminder_create(class_id: int):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(create_deadline_reminder(class_id, body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@spa_api_blueprint.route("/classes/<int:class_id>/deadline-reminders/<int:reminder_id>", methods=["PUT"])
@login_required
@permissions_required("classes:manage")
def deadline_reminder_update(class_id: int, reminder_id: int):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(update_deadline_reminder(class_id, reminder_id, body))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@spa_api_blueprint.route(
    "/classes/<int:class_id>/deadline-reminders/<int:reminder_id>/toggle",
    methods=["POST"],
)
@login_required
@permissions_required("classes:manage")
def deadline_reminder_toggle(class_id: int, reminder_id: int):
    return jsonify(toggle_deadline_reminder(class_id, reminder_id))


@spa_api_blueprint.route(
    "/classes/<int:class_id>/deadline-reminders/<int:reminder_id>/send-now",
    methods=["POST"],
)
@login_required
@permissions_required("classes:manage")
def deadline_reminder_send_now(class_id: int, reminder_id: int):
    result = send_deadline_reminder_now(class_id, reminder_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route(
    "/classes/<int:class_id>/deadline-reminders/<int:reminder_id>",
    methods=["DELETE"],
)
@login_required
@permissions_required("classes:manage")
def deadline_reminder_delete(class_id: int, reminder_id: int):
    return jsonify(delete_deadline_reminder(class_id, reminder_id))


@spa_api_blueprint.route("/assignments/<int:assignment_id>/students-needing-reminder")
@login_required
@permissions_required("classes:manage")
def assignment_students_needing_reminder(assignment_id: int):
    return jsonify(query_students_needing_reminder(assignment_id))
