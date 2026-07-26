"""Legacy GET redirects for migrated student SPA tabs."""

from __future__ import annotations

from utils.spa_management_urls import react_spa_enabled


def user_should_use_spa_student_shell() -> bool:
    if not react_spa_enabled():
        return False
    try:
        from flask_login import current_user
        from utils.user_roles import user_has_student_spa_entry

        return bool(
            current_user.is_authenticated and user_has_student_spa_entry(current_user)
        )
    except Exception:
        return False


def _spa_student_get_redirect(app_path: str):
    from flask import redirect, request

    if not user_should_use_spa_student_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect(app_path)


def spa_student_dashboard_redirect():
    return _spa_student_get_redirect("/app/student")


def spa_student_assignments_redirect():
    from flask import redirect, request

    if not user_should_use_spa_student_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    qs = request.query_string.decode("utf-8") if request.query_string else ""
    path = "/app/student/assignments"
    if qs:
        path = f"{path}?{qs}"
    return redirect(path)


def spa_student_classes_redirect():
    return _spa_student_get_redirect("/app/student/classes")


def spa_student_class_detail_redirect(class_id: int):
    return _spa_student_get_redirect(f"/app/student/classes/{class_id}")


def spa_student_grades_redirect():
    return _spa_student_get_redirect("/app/student/grades")


def spa_student_collaborate_redirect():
    return _spa_student_get_redirect("/app/student/collaborate")


def spa_student_schedule_redirect():
    return _spa_student_get_redirect("/app/student/schedule")


def spa_student_calendar_redirect():
    from flask import redirect, request

    if not user_should_use_spa_student_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    qs = request.query_string.decode("utf-8") if request.query_string else ""
    path = "/app/student/calendar"
    if qs:
        path = f"{path}?{qs}"
    return redirect(path)


def spa_student_jobs_redirect():
    return _spa_student_get_redirect("/app/student/jobs")


def spa_student_settings_redirect():
    return _spa_student_get_redirect("/app/student/settings")


def spa_student_bug_reports_redirect():
    return _spa_student_get_redirect("/app/student/settings/bug-reports")


def spa_student_take_quiz_redirect(assignment_id: int):
    from flask import redirect, request

    if not user_should_use_spa_student_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    qs = request.query_string.decode("utf-8") if request.query_string else ""
    path = f"/app/student/take-quiz/{int(assignment_id)}"
    if qs:
        path = f"{path}?{qs}"
    return redirect(path)


def spa_student_discussion_redirect(assignment_id: int):
    from flask import redirect, request

    if not user_should_use_spa_student_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    qs = request.query_string.decode("utf-8") if request.query_string else ""
    path = f"/app/student/discussion/{int(assignment_id)}"
    if qs:
        path = f"{path}?{qs}"
    return redirect(path)


def spa_student_discussion_thread_redirect(assignment_id: int, thread_id: int):
    from flask import redirect, request

    if not user_should_use_spa_student_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    qs = request.query_string.decode("utf-8") if request.query_string else ""
    path = f"/app/student/discussion/{int(assignment_id)}/thread/{int(thread_id)}"
    if qs:
        path = f"{path}?{qs}"
    return redirect(path)
