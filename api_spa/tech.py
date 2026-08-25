"""Tech portal JSON API for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import tech_required
from management_routes.bug_reports_spa_helpers import query_bug_reports
from models import BugReport, db
from tech_routes.device_repair_spa_helpers import (
    build_repair_tickets_list_payload,
    create_repair_ticket,
    update_repair_ticket_status,
)
from tech_routes.spa_helpers import (
    build_activity_log_payload,
    build_audit_logs_payload,
    build_device_form_payload,
    build_devices_list_payload,
    build_error_reports_payload,
    build_system_payload,
    build_tech_dashboard_payload,
    build_tech_settings_payload,
    build_user_detail_payload,
    build_user_management_payload,
    bulk_upload_devices_from_csv,
    clear_app_cache,
    delete_device,
    impersonate_user_spa,
    reset_user_password_spa,
    run_database_backup,
    run_database_integrity,
    save_device,
    set_school_timezone_spa,
    set_site_theme_spa,
    start_maintenance_mode,
    stop_maintenance_mode,
    update_system_config,
)
from flask_login import current_user

from . import spa_api_blueprint


@spa_api_blueprint.route("/tech/dashboard")
@login_required
@tech_required
def tech_spa_dashboard():
    return jsonify(build_tech_dashboard_payload())


@spa_api_blueprint.route("/tech/settings/hub")
@login_required
@tech_required
def tech_spa_settings_hub():
    return jsonify(build_tech_settings_payload())


@spa_api_blueprint.route("/tech/settings/theme", methods=["POST"])
@login_required
@tech_required
def tech_spa_settings_theme():
    from auth_routes import update_theme

    return update_theme()


@spa_api_blueprint.route("/tech/devices")
@login_required
@tech_required
def tech_spa_devices_list():
    return jsonify(
        build_devices_list_payload(
            device_type=request.args.get("type", ""),
            search=request.args.get("q", ""),
            assignment=request.args.get("assignment", ""),
        )
    )


@spa_api_blueprint.route("/tech/devices/repair-tickets")
@login_required
@tech_required
def tech_spa_repair_tickets_list():
    device_id_raw = (request.args.get("device_id") or "").strip()
    device_id = None
    if device_id_raw:
        try:
            device_id = int(device_id_raw)
        except ValueError:
            return jsonify({"error": "Invalid device_id."}), 400
    return jsonify(
        build_repair_tickets_list_payload(
            status=request.args.get("status", ""),
            category=request.args.get("category", ""),
            search=request.args.get("q", ""),
            device_id=device_id,
        )
    )


@spa_api_blueprint.route("/tech/devices/repair-tickets", methods=["POST"])
@login_required
@tech_required
def tech_spa_repair_tickets_create():
    payload, error, status = create_repair_ticket(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/devices/repair-tickets/<int:ticket_id>/status", methods=["POST"])
@login_required
@tech_required
def tech_spa_repair_ticket_status(ticket_id: int):
    payload, error, status = update_repair_ticket_status(
        ticket_id, request.get_json(silent=True) or {}
    )
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/devices/form")
@login_required
@tech_required
def tech_spa_device_form_new():
    payload, error, status = build_device_form_payload()
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/devices/<int:device_id>/form")
@login_required
@tech_required
def tech_spa_device_form_edit(device_id: int):
    payload, error, status = build_device_form_payload(device_id)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/devices", methods=["POST"])
@login_required
@tech_required
def tech_spa_device_create():
    payload, error, status = save_device(device_id=None, body=request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/devices/bulk-upload", methods=["POST"])
@login_required
@tech_required
def tech_spa_devices_bulk_upload():
    upload = request.files.get("csv_file")
    if not upload or not upload.filename:
        return jsonify({"error": "Choose a CSV file to upload."}), 400
    if not upload.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file."}), 400
    payload, error, status = bulk_upload_devices_from_csv(upload.read())
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload), status


@spa_api_blueprint.route("/tech/devices/<int:device_id>", methods=["PATCH"])
@login_required
@tech_required
def tech_spa_device_update(device_id: int):
    payload, error, status = save_device(device_id=device_id, body=request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/devices/<int:device_id>", methods=["DELETE"])
@login_required
@tech_required
def tech_spa_device_delete(device_id: int):
    payload, error, status = delete_device(device_id)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/activity-log")
@login_required
@tech_required
def tech_spa_activity_log():
    return jsonify(
        build_activity_log_payload(
            user_id=request.args.get("user_id", type=int),
            action=request.args.get("action", ""),
            start_date=request.args.get("start_date", ""),
            end_date=request.args.get("end_date", ""),
            limit=request.args.get("limit", 100, type=int),
        )
    )


@spa_api_blueprint.route("/tech/audit-logs")
@login_required
@tech_required
def tech_spa_audit_logs():
    return jsonify(
        build_audit_logs_payload(
            q=request.args.get("q", ""),
            method=request.args.get("method", ""),
            status=request.args.get("status", ""),
            user_id=request.args.get("user_id", type=int),
            start=request.args.get("start", ""),
            end=request.args.get("end", ""),
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 50, type=int),
        )
    )


@spa_api_blueprint.route("/tech/error-reports")
@login_required
@tech_required
def tech_spa_error_reports():
    return jsonify(
        build_error_reports_payload(
            type_filter=request.args.get("type_filter", "All"),
            status_filter=request.args.get("status_filter", "All"),
            date_filter=request.args.get("date_filter", "7d"),
        )
    )


@spa_api_blueprint.route("/tech/system")
@login_required
@tech_required
def tech_spa_system():
    return jsonify(build_system_payload())


@spa_api_blueprint.route("/tech/system/backup", methods=["POST"])
@login_required
@tech_required
def tech_spa_backup():
    payload, error, status = run_database_backup()
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/system/integrity", methods=["POST"])
@login_required
@tech_required
def tech_spa_integrity():
    payload, error, status = run_database_integrity()
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/system/clear-cache", methods=["POST"])
@login_required
@tech_required
def tech_spa_clear_cache():
    payload, error, status = clear_app_cache()
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/system/maintenance/start", methods=["POST"])
@login_required
@tech_required
def tech_spa_maintenance_start():
    payload, error, status = start_maintenance_mode(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/system/maintenance/stop", methods=["POST"])
@login_required
@tech_required
def tech_spa_maintenance_stop():
    payload, error, status = stop_maintenance_mode()
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/system/config", methods=["POST"])
@login_required
@tech_required
def tech_spa_system_config():
    payload, error, status = update_system_config(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/system/timezone", methods=["POST"])
@login_required
@tech_required
def tech_spa_timezone():
    payload, error, status = set_school_timezone_spa(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/system/site-theme", methods=["POST"])
@login_required
@tech_required
def tech_spa_site_theme():
    payload, error, status = set_site_theme_spa(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/bug-reports", methods=["POST"])
@login_required
@tech_required
def tech_spa_bug_reports_submit():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    contact_email = (payload.get("contact_email") or "").strip() or None
    severity = (payload.get("severity") or "medium").strip().lower()
    page_url = (payload.get("page_url") or "").strip()
    if not title:
        return jsonify({"error": "Please provide a title for the bug report."}), 400
    if not description:
        return jsonify({"error": "Please provide a description of the bug."}), 400
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
            "message": "Bug report submitted successfully.",
            "report_id": report.id,
        }
    )


@spa_api_blueprint.route("/tech/bug-reports")
@login_required
@tech_required
def tech_spa_bug_reports():
    return jsonify(query_bug_reports(user=current_user))


@spa_api_blueprint.route("/tech/bug-reports/<int:report_id>/status", methods=["POST"])
@login_required
@tech_required
def tech_spa_bug_status(report_id: int):
    payload = request.get_json(silent=True) or {}
    new_status = (payload.get("status") or "").strip()
    if new_status not in ("open", "in_progress", "resolved", "closed"):
        return jsonify({"error": "Invalid status."}), 400
    report = BugReport.query.get_or_404(report_id)
    report.status = new_status
    db.session.commit()
    return jsonify({"success": True, "message": "Status updated.", "status": new_status})


@spa_api_blueprint.route("/tech/users")
@login_required
@tech_required
def tech_spa_users():
    return jsonify(build_user_management_payload())


@spa_api_blueprint.route("/tech/users/<int:user_id>")
@login_required
@tech_required
def tech_spa_user_detail(user_id: int):
    payload, error, status = build_user_detail_payload(user_id)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@tech_required
def tech_spa_reset_password(user_id: int):
    payload, error, status = reset_user_password_spa(user_id)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/tech/users/<int:user_id>/impersonate", methods=["POST"])
@login_required
@tech_required
def tech_spa_impersonate(user_id: int):
    payload, error, status = impersonate_user_spa(user_id)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)
