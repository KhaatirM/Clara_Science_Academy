"""Bug reports API for the management React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import management_required
from management_routes.bug_reports_spa_helpers import query_bug_reports
from models import BugReport, db

from . import spa_api_blueprint


@spa_api_blueprint.route("/bug-reports")
@login_required
@management_required
def bug_reports_list():
    return jsonify(query_bug_reports(user=current_user))


@spa_api_blueprint.route("/bug-reports", methods=["POST"])
@login_required
@management_required
def bug_reports_submit():
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
        browser_info=request.headers.get("User-Agent", ""),
        ip_address=request.remote_addr,
        page_url=page_url or request.referrer,
    )
    db.session.add(report)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "Bug report submitted successfully. Thank you for helping us improve the system!",
            "report_id": report.id,
        }
    )


@spa_api_blueprint.route("/bug-reports/<int:report_id>/status", methods=["POST"])
@login_required
@management_required
def bug_reports_update_status(report_id: int):
    if current_user.role not in ("Tech", "IT Support"):
        return jsonify(
            {"success": False, "message": "Access denied. Only technical staff can update bug report status."}
        ), 403

    payload = request.get_json(silent=True) or {}
    new_status = (payload.get("status") or "").strip()
    if new_status not in ("open", "in_progress", "resolved", "closed"):
        return jsonify({"success": False, "message": "Invalid status."}), 400

    report = BugReport.query.get_or_404(report_id)
    report.status = new_status
    db.session.commit()
    return jsonify({"success": True, "message": "Status updated.", "status": new_status})
