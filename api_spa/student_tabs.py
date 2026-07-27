"""Student schedule, calendar, jobs, settings, and bug-report APIs."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import student_required
from models import BugReport, db
from student_routes.tabs_spa_helpers import (
    build_student_bug_reports_payload,
    build_student_calendar_payload,
    build_student_jobs_payload,
    build_student_schedule_payload,
    build_student_settings_payload,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/student/schedule")
@login_required
@student_required
def student_schedule():
    payload, error = build_student_schedule_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load schedule"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/student/calendar")
@login_required
@student_required
def student_calendar():
    payload, error = build_student_calendar_payload(
        month=request.args.get("month", type=int),
        year=request.args.get("year", type=int),
    )
    if error or not payload:
        return jsonify({"error": error or "Could not load calendar"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/student/jobs")
@login_required
@student_required
def student_portal_jobs_hub():
    payload, error = build_student_jobs_payload()
    if error or not payload:
        return jsonify({"error": error or "Could not load student jobs"}), 500
    return jsonify(payload)


@spa_api_blueprint.route("/student/settings/hub")
@login_required
@student_required
def student_settings_hub():
    return jsonify(build_student_settings_payload(user=current_user))


@spa_api_blueprint.route("/student/settings/theme", methods=["POST"])
@login_required
@student_required
def student_settings_update_theme():
    from auth_routes import update_theme

    return update_theme()


@spa_api_blueprint.route("/student/settings/low-grade-threshold", methods=["POST"])
@login_required
@student_required
def student_settings_update_threshold():
    from student_routes.routes import update_low_grade_threshold

    return update_low_grade_threshold()


@spa_api_blueprint.route("/student/bug-reports")
@login_required
@student_required
def student_bug_reports_list():
    return jsonify(build_student_bug_reports_payload(user=current_user))


@spa_api_blueprint.route("/student/bug-reports", methods=["POST"])
@login_required
@student_required
def student_bug_reports_submit():
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
