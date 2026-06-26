"""Unified attendance API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import permissions_required
from management_routes.attendance import (
    _attendance_analytics_context,
    _attendance_reports_context,
)
from management_routes.attendance_spa_helpers import (
    mark_class_all_present,
    query_unified_attendance_hub,
    save_school_day_attendance,
    serialize_attendance_analytics,
    serialize_attendance_reports,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/attendance/hub")
@login_required
@permissions_required("attendance:manage")
def attendance_hub():
    return jsonify(
        query_unified_attendance_hub(
            request.args.get("date"),
            request.args.get("class_date"),
        )
    )


@spa_api_blueprint.route("/attendance/school-day", methods=["POST"])
@login_required
@permissions_required("attendance:manage")
def attendance_school_day_save():
    payload = request.get_json(silent=True) or {}
    attendance_date = (payload.get("attendance_date") or "").strip()
    entries = payload.get("entries") or []
    if not isinstance(entries, list):
        return jsonify({"success": False, "message": "Invalid entries payload."}), 400

    result = save_school_day_attendance(attendance_date, entries)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/attendance/class/<int:class_id>/mark-all-present", methods=["POST"])
@login_required
@permissions_required("attendance:manage")
def attendance_mark_all_present(class_id: int):
    payload = request.get_json(silent=True) or {}
    date_str = (payload.get("date") or request.form.get("date") or "").strip()
    result = mark_class_all_present(class_id, date_str)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/attendance/reports")
@login_required
@permissions_required("attendance:manage")
def attendance_reports_api():
    ctx = _attendance_reports_context(request, embed_tab=False)
    return jsonify(serialize_attendance_reports(ctx))


@spa_api_blueprint.route("/attendance/analytics")
@login_required
@permissions_required("attendance:manage")
def attendance_analytics_api():
    ctx = _attendance_analytics_context(request)
    return jsonify(serialize_attendance_analytics(ctx))
