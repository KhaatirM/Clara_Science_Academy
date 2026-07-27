"""Student collaborate hub API for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import student_required
from student_collaborate_spa_helpers import (
    build_student_collaborate_payload,
    submit_student_conflict,
    submit_student_feedback360,
    submit_student_journal,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/student/collaborate")
@login_required
@student_required
def student_collaborate():
    payload, error = build_student_collaborate_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load collaborate hub"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/student/collaborate/feedback", methods=["POST"])
@login_required
@student_required
def student_collaborate_feedback():
    payload, error, status = submit_student_feedback360(request.get_json(silent=True) or {})
    if error or not payload:
        return jsonify({"error": error or "Could not submit feedback"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/collaborate/journal", methods=["POST"])
@login_required
@student_required
def student_collaborate_journal():
    payload, error, status = submit_student_journal(request.get_json(silent=True) or {})
    if error or not payload:
        return jsonify({"error": error or "Could not submit journal"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/student/collaborate/conflict", methods=["POST"])
@login_required
@student_required
def student_collaborate_conflict():
    payload, error, status = submit_student_conflict(request.get_json(silent=True) or {})
    if error or not payload:
        return jsonify({"error": error or "Could not submit conflict report"}), status
    return jsonify(payload)
