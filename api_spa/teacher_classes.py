"""Teacher classes list API for the React SPA."""

from __future__ import annotations

from flask import jsonify
from flask_login import login_required

from decorators import teacher_required
from teacher_routes.classes_spa_helpers import build_teacher_classes_payload
from teacher_routes.teacher_class_view_spa_helpers import build_teacher_class_view_payload

from . import spa_api_blueprint


@spa_api_blueprint.route("/teacher/classes")
@login_required
@teacher_required
def teacher_classes_list():
    payload, error = build_teacher_classes_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load classes"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/teacher/classes/<int:class_id>")
@login_required
@teacher_required
def teacher_class_view(class_id: int):
    payload, error, status = build_teacher_class_view_payload(class_id)
    if error or not payload:
        return jsonify({"error": error or "Could not load class"}), status
    return jsonify(payload)
