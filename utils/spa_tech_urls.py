"""Legacy GET redirects for migrated tech SPA tabs."""

from __future__ import annotations

from utils.spa_management_urls import react_spa_enabled


def user_should_use_spa_tech_shell() -> bool:
    if not react_spa_enabled():
        return False
    try:
        from flask import session
        from flask_login import current_user
        from utils.user_roles import (
            staff_must_choose_dashboard,
            user_has_management_entry_access,
            user_has_tech_spa_entry,
        )

        if not current_user.is_authenticated or not user_has_tech_spa_entry(current_user):
            return False
        if staff_must_choose_dashboard(current_user):
            return session.get("staff_dashboard_target") == "tech"
        if user_has_management_entry_access(current_user):
            return False
        return True
    except Exception:
        return False


def _spa_tech_get_redirect(app_path: str):
    from flask import redirect, request

    if not user_should_use_spa_tech_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect(app_path)


def spa_tech_dashboard_redirect():
    return _spa_tech_get_redirect("/app/tech")


def spa_tech_devices_redirect():
    return _spa_tech_get_redirect("/app/tech/devices")


def spa_tech_device_new_redirect():
    return _spa_tech_get_redirect("/app/tech/devices/new")


def spa_tech_device_edit_redirect(device_id: int):
    return _spa_tech_get_redirect(f"/app/tech/devices/{device_id}/edit")


def spa_tech_activity_log_redirect():
    return _spa_tech_get_redirect("/app/tech/logs?tab=activity")


def spa_tech_audit_logs_redirect():
    return _spa_tech_get_redirect("/app/tech/logs?tab=audit")


def spa_tech_error_reports_redirect():
    return _spa_tech_get_redirect("/app/tech/bugs?tab=errors")


def spa_tech_system_redirect():
    return _spa_tech_get_redirect("/app/tech/system")


def spa_tech_bug_reports_redirect():
    return _spa_tech_get_redirect("/app/tech/bugs?tab=reports")


def spa_tech_user_management_redirect():
    return _spa_tech_get_redirect("/app/tech/users")


def spa_tech_user_detail_redirect(user_id: int):
    return _spa_tech_get_redirect(f"/app/tech/users/{user_id}")


def spa_tech_settings_redirect():
    return _spa_tech_get_redirect("/app/tech/settings")
