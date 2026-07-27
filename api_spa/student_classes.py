"""Student classes list + detail API for the React SPA."""

from __future__ import annotations

from flask import jsonify
from flask_login import login_required

from decorators import student_required
from student_routes.class_view_spa_helpers import build_student_class_detail_payload
from student_routes.classes_spa_helpers import build_student_classes_payload

from . import spa_api_blueprint


@spa_api_blueprint.route("/student/classes")
@login_required
@student_required
def student_classes_list():
    payload, error = build_student_classes_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load classes"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/student/classes/<int:class_id>")
@login_required
@student_required
def student_class_detail(class_id: int):
    payload, error, status = build_student_class_detail_payload(class_id)
    if error or not payload:
        return jsonify({"error": error or "Could not load class"}), status
    return jsonify(payload)
