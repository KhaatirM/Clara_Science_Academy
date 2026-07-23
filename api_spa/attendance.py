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


@spa_api_blueprint.route("/attendance/take/<int:class_id>")
@login_required
@permissions_required("attendance:manage")
def attendance_take_class(class_id: int):
    from management_routes.attendance_spa_helpers import query_take_class_attendance

    try:
        payload = query_take_class_attendance(class_id, request.args.get("date"))
        payload["urls"] = {
            **payload.get("urls", {}),
            "records": f"/app/management/attendance/records/{class_id}",
            "csv_upload": f"/api/spa/attendance/take/{class_id}/upload-csv",
            "csv_template": f"/api/spa/attendance/take/{class_id}/csv-template",
        }
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404


@spa_api_blueprint.route("/attendance/take/<int:class_id>", methods=["POST"])
@login_required
@permissions_required("attendance:manage")
def attendance_take_class_save(class_id: int):
    from management_routes.attendance_spa_helpers import save_take_class_attendance

    payload = request.get_json(silent=True) or {}
    date_str = (payload.get("date") or "").strip()
    entries = payload.get("entries") or []
    if not date_str:
        return jsonify({"success": False, "message": "Date is required."}), 400
    result = save_take_class_attendance(class_id, date_str, entries)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/attendance/records/<int:class_id>")
@login_required
@permissions_required("attendance:manage")
def attendance_class_records(class_id: int):
    from management_routes.attendance_spa_helpers import query_class_attendance_records

    return jsonify(
        query_class_attendance_records(
            class_id,
            start_date_str=request.args.get("start_date"),
            end_date_str=request.args.get("end_date"),
            student_id=request.args.get("student_id", type=int),
            status_filter=request.args.get("status"),
        )
    )


@spa_api_blueprint.route("/attendance/take/<int:class_id>/csv-template")
@login_required
@permissions_required("attendance:manage")
def attendance_take_csv_template(class_id: int):
    from management_routes.attendance_csv_template import build_attendance_csv_template_response

    return build_attendance_csv_template_response(class_id)


@spa_api_blueprint.route("/attendance/take/<int:class_id>/upload-csv", methods=["POST"])
@login_required
@permissions_required("attendance:manage")
def attendance_take_upload_csv(class_id: int):
    from flask_login import current_user
    from management_routes.attendance_spa_helpers import process_attendance_csv_upload

    file = request.files.get("attendance_file")
    teacher_id = getattr(current_user, "teacher_staff_id", None)
    result = process_attendance_csv_upload(class_id, file, teacher_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status

