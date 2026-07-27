"""Grade 1 & 3 standards checklist API for the React management SPA."""

from __future__ import annotations

from flask import abort, jsonify, request
from flask_login import current_user, login_required

from decorators import permissions_required
from management_routes.grade_standards_spa_helpers import (
    apply_grade_standards_changes,
    query_grade_standards_editor,
    query_grade_standards_hub,
)

from . import spa_api_blueprint


def _grade_from_route(raw: str) -> str:
    text = (raw or "").strip().lower()
    if text not in ("grade1", "grade3", "1", "3"):
        abort(404)
    return text


@spa_api_blueprint.route("/grade-standards/<grade>/hub")
@login_required
@permissions_required("report_cards:view", "report_cards:generate")
def grade_standards_hub(grade: str):
    return jsonify(query_grade_standards_hub(_grade_from_route(grade)))


@spa_api_blueprint.route("/grade-standards/<grade>/classes/<int:class_id>", methods=["GET"])
@login_required
@permissions_required("report_cards:view", "report_cards:generate")
def grade_standards_editor_get(grade: str, class_id: int):
    quarter = request.args.get("quarter")
    view = request.args.get("view", "grid")
    student_id = request.args.get("student_id", type=int)
    return jsonify(
        query_grade_standards_editor(
            _grade_from_route(grade),
            class_id,
            quarter=quarter,
            view=view,
            student_id=student_id,
        )
    )


@spa_api_blueprint.route("/grade-standards/<grade>/classes/<int:class_id>", methods=["POST"])
@login_required
@permissions_required("report_cards:view", "report_cards:generate")
def grade_standards_editor_post(grade: str, class_id: int):
    payload = request.get_json(silent=True) or {}
    result = apply_grade_standards_changes(
        _grade_from_route(grade),
        class_id,
        payload,
        getattr(current_user, "id", None),
    )
    return jsonify(result)
