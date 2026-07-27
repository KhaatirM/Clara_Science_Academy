"""Legacy GET redirects for migrated parent / Family Portal SPA tabs."""

from __future__ import annotations

from utils.spa_management_urls import react_spa_enabled


def user_should_use_spa_parent_shell() -> bool:
    if not react_spa_enabled():
        return False
    try:
        from flask_login import current_user
        from utils.user_roles import user_has_parent_spa_entry

        return bool(current_user.is_authenticated and user_has_parent_spa_entry(current_user))
    except Exception:
        return False


def _spa_parent_get_redirect(app_path: str):
    from flask import redirect, request

    if not user_should_use_spa_parent_shell():
        return None
    if request.method != "GET":
        return None
    return redirect(app_path)


def spa_parent_dashboard_redirect():
    return _spa_parent_get_redirect("/app/parent")


def spa_parent_settings_redirect():
    return _spa_parent_get_redirect("/app/parent/settings")


def spa_parent_grades_redirect(student_id: int):
    return _spa_parent_get_redirect("/app/parent/grades")


def spa_parent_attendance_redirect(student_id: int):
    return _spa_parent_get_redirect("/app/parent/attendance")


def spa_parent_classes_redirect(student_id: int):
    return _spa_parent_get_redirect("/app/parent/classes")


def spa_parent_report_cards_redirect(student_id: int):
    return _spa_parent_get_redirect("/app/parent/report-cards")
