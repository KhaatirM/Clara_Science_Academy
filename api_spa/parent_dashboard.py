"""Parent / Family Portal JSON API for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required
from werkzeug.exceptions import HTTPException

from decorators import parent_required
from models import ReportCard
from parent_routes.dashboard_spa_helpers import (
    build_parent_bootstrap_payload,
    build_parent_home_payload,
    build_parent_settings_payload,
    build_parent_tab_payload,
    select_active_child,
)
from utils.report_card_portal import parent_can_download_report_card

from . import spa_api_blueprint


@spa_api_blueprint.route("/parent/bootstrap")
@login_required
@parent_required
def spa_parent_bootstrap():
    return jsonify(build_parent_bootstrap_payload())


@spa_api_blueprint.route("/parent/select-child", methods=["POST"])
@login_required
@parent_required
def spa_parent_select_child():
    body = request.get_json(silent=True) or {}
    try:
        student_id = int(body.get("student_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Choose a child."}), 400
    payload, error, status = select_active_child(student_id)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/parent/home")
@login_required
@parent_required
def spa_parent_home():
    payload, error, status = build_parent_home_payload()
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/parent/grades")
@login_required
@parent_required
def spa_parent_grades():
    payload, error, status = build_parent_tab_payload("grades")
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/parent/attendance")
@login_required
@parent_required
def spa_parent_attendance():
    payload, error, status = build_parent_tab_payload("attendance")
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/parent/classes")
@login_required
@parent_required
def spa_parent_classes():
    payload, error, status = build_parent_tab_payload("classes")
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/parent/report-cards")
@login_required
@parent_required
def spa_parent_report_cards():
    payload, error, status = build_parent_tab_payload("report-cards")
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/parent/report-cards/<int:report_card_id>/pdf")
@login_required
@parent_required
def spa_parent_report_card_pdf(report_card_id: int):
    if not parent_can_download_report_card(current_user.id, report_card_id):
        return jsonify({"error": "Access denied"}), 403
    report_card = ReportCard.query.get_or_404(report_card_id)
    try:
        from management_routes.reports import build_report_card_pdf_response

        return build_report_card_pdf_response(report_card)
    except ImportError:
        return jsonify({"error": "PDF download is temporarily unavailable."}), 503
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        return jsonify({"error": "Could not generate the report card PDF."}), 500


@spa_api_blueprint.route("/parent/settings")
@login_required
@parent_required
def spa_parent_settings():
    return jsonify(build_parent_settings_payload())


@spa_api_blueprint.route("/parent/settings/theme", methods=["POST"])
@login_required
@parent_required
def spa_parent_settings_theme():
    from auth_routes import update_theme

    return update_theme()
