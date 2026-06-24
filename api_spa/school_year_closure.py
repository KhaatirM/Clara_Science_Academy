"""School-year closure API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import management_required
from extensions import db
from management_routes.school_year_closure_spa_helpers import (
    create_closure_from_body,
    grant_closure_extension,
    query_closure_dashboard,
    query_closure_schedule_form,
    revoke_closure_extension,
    run_closure_action,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/school-year/closure/schedule")
@login_required
@management_required
def closure_schedule_form():
    return jsonify(query_closure_schedule_form())


@spa_api_blueprint.route("/school-year/closure", methods=["POST"])
@login_required
@management_required
def closure_create():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(create_closure_from_body(body, current_user))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-year/closure/<int:closure_id>")
@login_required
@management_required
def closure_dashboard(closure_id: int):
    try:
        return jsonify(query_closure_dashboard(closure_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@spa_api_blueprint.route("/school-year/closure/<int:closure_id>/<action>", methods=["POST"])
@login_required
@management_required
def closure_action(closure_id: int, action: str):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(run_closure_action(closure_id, action, body, current_user))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route("/school-year/closure/<int:closure_id>/extensions", methods=["POST"])
@login_required
@management_required
def closure_grant_extension(closure_id: int):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(grant_closure_extension(closure_id, body, current_user))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500


@spa_api_blueprint.route(
    "/school-year/closure/<int:closure_id>/extensions/<int:extension_id>/revoke",
    methods=["POST"],
)
@login_required
@management_required
def closure_revoke_extension(closure_id: int, extension_id: int):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(revoke_closure_extension(closure_id, extension_id, body, current_user))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 500

