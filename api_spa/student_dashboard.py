"""Student home dashboard API for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import student_required
from student_dashboard_spa_helpers import (
    build_student_home_payload,
    delete_student_goal,
    set_student_goal,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/student/dashboard/home")
@login_required
@student_required
def student_dashboard_home():
    payload, error = build_student_home_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load dashboard"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/student/goals", methods=["POST"])
@login_required
@student_required
def student_goals_set():
    body = request.get_json(silent=True) or {}
    class_id = body.get("class_id")
    target_grade = body.get("target_grade")
    try:
        class_id = int(class_id)
        target_grade = float(target_grade)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Please provide both class and target grade."}), 400
    if not class_id or target_grade is None:
        return jsonify({"success": False, "message": "Please provide both class and target grade."}), 400
    result = set_student_goal(current_user.student_id, class_id, target_grade)
    return jsonify(result)


@spa_api_blueprint.route("/student/goals/<int:goal_id>", methods=["DELETE"])
@login_required
@student_required
def student_goals_delete(goal_id: int):
    result = delete_student_goal(current_user.student_id, goal_id)
    status = 200 if result.get("success") else 400
    if result.get("message") == "Forbidden":
        status = 403
    elif result.get("message") == "Goal not found":
        status = 404
    return jsonify(result), status
