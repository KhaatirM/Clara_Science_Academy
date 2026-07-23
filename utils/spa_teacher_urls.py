"""Legacy GET redirects for migrated teacher SPA tabs."""

from __future__ import annotations

from utils.spa_management_urls import react_spa_enabled


def user_should_use_spa_teacher_shell() -> bool:
    if not react_spa_enabled():
        return False
    try:
        from flask_login import current_user
        from utils.user_roles import user_has_teacher_spa_entry

        return bool(
            current_user.is_authenticated and user_has_teacher_spa_entry(current_user)
        )
    except Exception:
        return False


def _spa_teacher_get_redirect(app_path: str):
    from flask import redirect, request

    if not user_should_use_spa_teacher_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect(app_path)


def spa_teacher_dashboard_redirect():
    return _spa_teacher_get_redirect("/app/teacher")


def spa_teacher_classes_redirect():
    return _spa_teacher_get_redirect("/app/teacher/classes")


def spa_teacher_students_redirect():
    return _spa_teacher_get_redirect("/app/teacher/students")


def spa_teacher_assignments_grades_redirect():
    from flask import request

    class_id = request.args.get("class_id", type=int)
    if class_id:
        return _spa_teacher_get_redirect(f"/app/teacher/assignments-and-grades/{class_id}")
    return _spa_teacher_get_redirect("/app/teacher/assignments-and-grades")


def spa_teacher_attendance_redirect():
    return _spa_teacher_get_redirect("/app/teacher/attendance")


def spa_teacher_schedule_redirect():
    return _spa_teacher_get_redirect("/app/teacher/schedule")


def spa_teacher_calendar_redirect():
    return _spa_teacher_get_redirect("/app/teacher/calendar")


def spa_teacher_settings_redirect():
    return _spa_teacher_get_redirect("/app/teacher/settings")


def spa_teacher_class_view_redirect(class_id: int):
    return _spa_teacher_get_redirect(f"/app/teacher/classes/{class_id}")


def spa_teacher_assignment_type_selector_redirect():
    from flask import request

    class_id = request.args.get("class_id", type=int)
    if class_id:
        return _spa_teacher_get_redirect(
            f"/app/teacher/assignments/create?class_id={class_id}"
        )
    return _spa_teacher_get_redirect("/app/teacher/assignments/create")


def spa_teacher_extension_requests_redirect():
    return _spa_teacher_get_redirect("/app/teacher/extensions")


def spa_teacher_redo_dashboard_redirect():
    return _spa_teacher_get_redirect("/app/teacher/redo")
