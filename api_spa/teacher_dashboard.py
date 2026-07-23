"""Teacher home dashboard API for the React SPA."""

from __future__ import annotations

from flask import jsonify
from flask_login import login_required

from decorators import teacher_required
from teacher_routes.dashboard_spa_helpers import build_teacher_home_payload

from . import spa_api_blueprint


@spa_api_blueprint.route("/teacher/dashboard/home")
@login_required
@teacher_required
def teacher_dashboard_home():
    payload, error = build_teacher_home_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load dashboard"}), 500
    return jsonify(payload)
