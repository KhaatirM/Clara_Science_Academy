"""Student grades API for the React SPA."""

from __future__ import annotations

from flask import jsonify
from flask_login import login_required

from decorators import student_required
from student_routes.grades_spa_helpers import build_student_grades_payload

from . import spa_api_blueprint


@spa_api_blueprint.route("/student/grades")
@login_required
@student_required
def student_grades_list():
    payload, error = build_student_grades_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load grades"}), 500
    return jsonify(payload)
