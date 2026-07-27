"""Student assignments list API for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import student_required
from student_routes.assignments_spa_helpers import build_student_assignments_payload

from . import spa_api_blueprint


@spa_api_blueprint.route("/student/assignments")
@login_required
@student_required
def student_assignments_list():
    payload, error = build_student_assignments_payload(
        class_id=request.args.get("class_id", type=int),
        status=request.args.get("status"),
        start_date=request.args.get("start_date"),
        end_date=request.args.get("end_date"),
    )
    if error or not payload:
        return jsonify({"error": error or "Could not load assignments"}), 500
    return jsonify(payload)
