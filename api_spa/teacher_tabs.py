"""Teacher SPA tab APIs (students, assignments, attendance, schedule, calendar, settings)."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import teacher_required
from management_routes.bug_reports_spa_helpers import query_bug_reports
from models import BugReport, db
from teacher_routes.teacher_tabs_spa_helpers import (
    build_teacher_assignments_class_payload,
    build_teacher_assignments_hub_payload,
    build_teacher_attendance_payload,
    build_teacher_calendar_payload,
    build_teacher_schedule_payload,
    build_teacher_settings_payload,
    build_teacher_students_payload,
)

from . import spa_api_blueprint


def _teacher_json(payload_builder):
    payload, error = payload_builder()
    if error or payload is None:
        return jsonify({"error": error or "Could not load data"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/teacher/students")
@login_required
@teacher_required
def teacher_students_list():
    return _teacher_json(build_teacher_students_payload)


@spa_api_blueprint.route("/teacher/students/<int:student_id>/grades")
@login_required
@teacher_required
def teacher_student_grades_report(student_id: int):
    from teacher_routes.teacher_student_report_spa_helpers import build_teacher_student_grades_report

    payload, error = build_teacher_student_grades_report(student_id)
    if error or payload is None:
        status = 403 if error == "Forbidden" else 404 if error == "Student not found" else 400
        return jsonify({"error": error or "Could not load grades report"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/teacher/students/<int:student_id>/attendance")
@login_required
@teacher_required
def teacher_student_attendance_report(student_id: int):
    from teacher_routes.teacher_student_report_spa_helpers import build_teacher_student_attendance_report

    payload, error = build_teacher_student_attendance_report(student_id)
    if error or payload is None:
        status = 403 if error == "Forbidden" else 404 if error == "Student not found" else 400
        return jsonify({"error": error or "Could not load attendance report"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/teacher/assignments-grades")
@login_required
@teacher_required
def teacher_assignments_grades_hub():
    return _teacher_json(build_teacher_assignments_hub_payload)


@spa_api_blueprint.route("/teacher/assignments-grades/<int:class_id>")
@login_required
@teacher_required
def teacher_assignments_class(class_id: int):
    view_mode = (request.args.get("view") or "grades").strip()
    sort_by = (request.args.get("sort") or "due_date").strip()
    sort_order = (request.args.get("order") or "desc").strip()
    payload, error = build_teacher_assignments_class_payload(
        class_id,
        view_mode=view_mode,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    if error or payload is None:
        status = 403 if error == "Forbidden" else 404 if error == "Class not found" else 500
        return jsonify({"error": error or "Could not load class assignments"}), status
    return jsonify(payload)


@spa_api_blueprint.route("/teacher/attendance")
@login_required
@teacher_required
def teacher_attendance_hub():
    return _teacher_json(build_teacher_attendance_payload)


@spa_api_blueprint.route("/teacher/attendance/take/<int:class_id>")
@login_required
@teacher_required
def teacher_attendance_take_get(class_id: int):
    from management_routes.attendance_spa_helpers import query_take_class_attendance
    from models import Class
    from teacher_routes.utils import get_teacher_or_admin, is_authorized_for_class

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        return jsonify({"error": "Forbidden"}), 403
    try:
        payload = query_take_class_attendance(class_id, request.args.get("date"))
        payload["urls"] = {
            "attendance_hub": "/app/teacher/attendance",
            "class_view": f"/app/teacher/classes/{class_id}",
            "records": f"/app/teacher/attendance/records/{class_id}",
            "csv_template": f"/api/spa/teacher/attendance/take/{class_id}/csv-template",
            "csv_upload": f"/api/spa/teacher/attendance/take/{class_id}/upload-csv",
        }
        payload["meta"] = {"teacher_id": getattr(get_teacher_or_admin(), "id", None)}
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404


@spa_api_blueprint.route("/teacher/attendance/take/<int:class_id>", methods=["POST"])
@login_required
@teacher_required
def teacher_attendance_take_save(class_id: int):
    from management_routes.attendance_spa_helpers import save_take_class_attendance
    from models import Class
    from teacher_routes.utils import is_authorized_for_class

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        return jsonify({"error": "Forbidden"}), 403
    payload = request.get_json(silent=True) or {}
    date_str = (payload.get("date") or "").strip()
    entries = payload.get("entries") or []
    result = save_take_class_attendance(class_id, date_str, entries)
    if result.get("success"):
        result["redirect_url"] = f"/app/teacher/attendance/take/{class_id}?date={date_str}"
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/teacher/attendance/take/<int:class_id>/mark-all-present", methods=["POST"])
@login_required
@teacher_required
def teacher_attendance_mark_all_present(class_id: int):
    from management_routes.attendance_spa_helpers import mark_class_all_present
    from models import Class
    from teacher_routes.utils import is_authorized_for_class

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        return jsonify({"error": "Forbidden"}), 403
    payload = request.get_json(silent=True) or {}
    date_str = (payload.get("date") or "").strip()
    result = mark_class_all_present(class_id, date_str)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/teacher/attendance/records/<int:class_id>")
@login_required
@teacher_required
def teacher_attendance_records(class_id: int):
    from management_routes.attendance_spa_helpers import query_class_attendance_records
    from models import Class
    from teacher_routes.utils import is_authorized_for_class

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(
        query_class_attendance_records(
            class_id,
            start_date_str=request.args.get("start_date"),
            end_date_str=request.args.get("end_date"),
            student_id=request.args.get("student_id", type=int),
            status_filter=request.args.get("status"),
        )
    )


@spa_api_blueprint.route("/teacher/attendance/take/<int:class_id>/upload-csv", methods=["POST"])
@login_required
@teacher_required
def teacher_attendance_upload_csv(class_id: int):
    from management_routes.attendance_spa_helpers import process_attendance_csv_upload
    from models import Class
    from teacher_routes.utils import get_teacher_or_admin, is_authorized_for_class

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        return jsonify({"error": "Forbidden"}), 403
    teacher = get_teacher_or_admin()
    teacher_id = teacher.id if teacher else None
    file = request.files.get("attendance_file")
    result = process_attendance_csv_upload(class_id, file, teacher_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/teacher/schedule")
@login_required
@teacher_required
def teacher_schedule():
    return _teacher_json(build_teacher_schedule_payload)


@spa_api_blueprint.route("/teacher/calendar")
@login_required
@teacher_required
def teacher_calendar():
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    payload, error = build_teacher_calendar_payload(month=month, year=year)
    if error or payload is None:
        return jsonify({"error": error or "Could not load calendar"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/teacher/settings/hub")
@login_required
@teacher_required
def teacher_settings_hub():
    return jsonify(build_teacher_settings_payload(user=current_user))


@spa_api_blueprint.route("/teacher/settings/theme", methods=["POST"])
@login_required
@teacher_required
def teacher_settings_update_theme():
    from authroutes import update_theme

    return update_theme()


@spa_api_blueprint.route("/teacher/bug-reports")
@login_required
@teacher_required
def teacher_bug_reports_list():
    return jsonify(query_bug_reports(user=current_user))


@spa_api_blueprint.route("/teacher/bug-reports", methods=["POST"])
@login_required
@teacher_required
def teacher_bug_reports_submit():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    contact_email = (payload.get("contact_email") or "").strip() or None
    severity = (payload.get("severity") or "medium").strip().lower()
    page_url = (payload.get("page_url") or "").strip()

    if not title:
        return jsonify({"success": False, "message": "Please provide a title for the bug report."}), 400
    if not description:
        return jsonify({"success": False, "message": "Please provide a description of the bug."}), 400
    if severity not in ("low", "medium", "high", "critical"):
        severity = "medium"

    report = BugReport(
        user_id=current_user.id,
        title=title,
        description=description,
        contact_email=contact_email,
        severity=severity,
        page_url=page_url or None,
        status="open",
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({"success": True, "message": "Bug report submitted. Thank you!"})
