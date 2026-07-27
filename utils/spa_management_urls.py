"""React SPA URL helpers for migrated management tabs."""

from __future__ import annotations

from flask import current_app, url_for

# SPA subpath (under /app/management) -> legacy Flask endpoint name
MGMT_NAV_ROUTES: dict[str, tuple[str, str]] = {
    "home": ("", "management.management_dashboard"),
    "students": ("students", "management.students"),
    "parents": ("parents", "management.parents.parents_hub"),
    "teachers": ("teachers", "management.teachers"),
    "classes": ("classes", "management.classes"),
    "assignments": ("assignments", "management.assignments_and_grades"),
    "attendance": ("attendance", "management.unified_attendance"),
    "report-cards": ("report-cards", "management.report_cards"),
    "billing": ("billing", "management.billing"),
    "student-jobs": ("student-jobs", "management.student_jobs"),
    "settings": ("settings", "management.settings"),
}


def spa_build_available() -> bool:
    """True when Vite output exists (static/spa is gitignored and built on deploy)."""
    import os

    return os.path.isfile(os.path.join(current_app.root_path, "static", "spa", "index.html"))


def react_spa_enabled() -> bool:
    """SPA routing only when enabled in config AND the frontend was built."""
    if not current_app.config.get("REACT_SPA_ENABLED"):
        return False
    return spa_build_available()


def user_should_use_spa_management_shell() -> bool:
    """Directors/admins and permission-only Administration staff use the React shell."""
    if not react_spa_enabled():
        return False
    try:
        from flask_login import current_user
        from utils.user_roles import user_can_use_management_spa_shell

        return bool(
            current_user.is_authenticated and user_can_use_management_spa_shell(current_user)
        )
    except Exception:
        return False


def spa_management_url(key: str, **legacy_kwargs: object) -> str:
    """Return /app/management/... when SPA is enabled for this user, else legacy url_for."""
    subpath, legacy_endpoint = MGMT_NAV_ROUTES[key]
    if user_should_use_spa_management_shell():
        if subpath:
            return f"/app/management/{subpath}"
        return "/app/management"
    return url_for(legacy_endpoint, **legacy_kwargs)


def management_home_redirect_target() -> str:
    if user_should_use_spa_management_shell():
        return "/app/management"
    return url_for("management.management_dashboard")


def spa_assignment_type_selector_redirect():
    """Redirect legacy assignment type selector GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    path = "/app/management/assignments/create"
    class_id = request.args.get("class_id", "").strip()
    if class_id.isdigit():
        path = f"{path}?class_id={class_id}"
    return redirect(path)


def spa_add_assignment_redirect():
    """Redirect legacy PDF/Paper create GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    context = request.args.get("context", "homework")
    if context not in ("homework", "in-class"):
        context = "homework"
    path = f"/app/management/assignments/create/pdf?context={context}"
    class_id = request.args.get("class_id", "").strip()
    if class_id.isdigit():
        path = f"{path}&class_id={class_id}"
    return redirect(path)


def spa_create_discussion_redirect():
    """Redirect legacy discussion create/edit GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    path = "/app/management/assignments/create/discussion"
    params = []
    class_id = request.args.get("class_id", "").strip()
    edit_id = request.args.get("edit", "").strip()
    if class_id.isdigit():
        params.append(f"class_id={class_id}")
    if edit_id.isdigit():
        params.append(f"edit={edit_id}")
    if params:
        path = f"{path}?{'&'.join(params)}"
    return redirect(path)


def spa_create_quiz_redirect():
    """Redirect legacy quiz create/edit GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    path = "/app/management/assignments/create/quiz"
    params = []
    class_id = request.args.get("class_id", "").strip()
    edit_id = request.args.get("edit", "").strip()
    if class_id.isdigit():
        params.append(f"class_id={class_id}")
    if edit_id.isdigit():
        params.append(f"edit={edit_id}")
    if params:
        path = f"{path}?{'&'.join(params)}"
    return redirect(path)


def spa_group_class_picker_redirect():
    """Redirect legacy group class picker GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/assignments/create/group")


def spa_group_type_selector_redirect(class_id: int):
    """Redirect legacy group type selector GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect(f"/app/management/assignments/create/group/{class_id}")


def spa_group_pdf_create_redirect(class_id: int):
    """Redirect legacy group PDF create GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect(f"/app/management/assignments/create/group/{class_id}/pdf")


def spa_group_quiz_create_redirect(class_id: int):
    """Redirect legacy group quiz create GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect(f"/app/management/assignments/create/group/{class_id}/quiz")


def spa_group_discussion_create_redirect(class_id: int):
    """Redirect legacy group discussion create GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect(f"/app/management/assignments/create/group/{class_id}/discussion")


def spa_assignments_hub_redirect():
    """Redirect legacy assignments & grades hub GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    path = "/app/management/assignments"
    class_id = request.args.get("class_id", "").strip()
    if class_id.isdigit():
        path = f"{path}/{class_id}"
    query = request.query_string.decode("utf-8") if request.query_string else ""
    if query:
        sep = "&" if "?" in path else "?"
        # Drop class_id from query when already in path
        if class_id.isdigit():
            parts = [p for p in query.split("&") if p and not p.startswith("class_id=")]
            query = "&".join(parts)
        if query:
            path = f"{path}{sep}{query}"
    return redirect(path)


def spa_extension_requests_redirect():
    """Redirect legacy extension requests GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/extensions")


def spa_redo_dashboard_redirect():
    """Redirect legacy redo dashboard GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/redo")


def spa_assignment_view_redirect(assignment_id: int, *, is_group: bool = False):
    from flask import redirect, request
    from models import Assignment, GroupAssignment

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    if is_group:
        ga = GroupAssignment.query.get(assignment_id)
        if not ga:
            return None
        return redirect(f"/app/management/assignments/{ga.class_id}/group/{ga.id}/view")
    assignment = Assignment.query.get(assignment_id)
    if not assignment or not assignment.class_id:
        return None
    return redirect(f"/app/management/assignments/{assignment.class_id}/individual/{assignment.id}/view")


def spa_assignment_grade_redirect(assignment_id: int, *, is_group: bool = False):
    from flask import redirect, request
    from models import Assignment, GroupAssignment, QuizQuestion

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    if is_group:
        ga = GroupAssignment.query.get(assignment_id)
        if not ga:
            return None
        return redirect(f"/app/management/assignments/{ga.class_id}/group/{ga.id}/grade")
    assignment = Assignment.query.get(assignment_id)
    if not assignment or not assignment.class_id:
        return None
    return redirect(f"/app/management/assignments/{assignment.class_id}/individual/{assignment.id}/grade")


def spa_class_workflow_redirect(class_id: int, suffix: str = ""):
    """Redirect legacy class workflow GET requests to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    path = f"/app/management/classes/{class_id}"
    if suffix:
        path = f"{path}/{suffix}"
    query = request.query_string.decode("utf-8") if request.query_string else ""
    if query:
        path = f"{path}?{query}"
    return redirect(path)


def spa_billing_redirect():
    """Redirect legacy billing GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/billing")


def spa_student_jobs_redirect():
    """Redirect legacy student jobs GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/student-jobs")


def spa_settings_redirect():
    """Redirect legacy settings GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/settings")


def spa_calendar_redirect():
    """Redirect legacy school calendar GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    path = "/app/management/calendar"
    query = request.query_string.decode("utf-8") if request.query_string else ""
    if query:
        path = f"{path}?{query}"
    return redirect(path)


def spa_calendar_school_breaks_redirect():
    """Redirect legacy school-breaks page to the SPA calendar breaks modal."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/calendar?open=school-breaks")


def spa_closure_schedule_redirect():
    """Redirect legacy closure schedule GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/school-year/closure/schedule")


def spa_school_years_redirect():
    """Redirect legacy school years GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect("/app/management/school-years")


def spa_class_tool_redirect(class_id: int, tool: str):
    """Redirect legacy class admin tool GET requests to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect(f"/app/management/classes/{class_id}/tools/{tool}")


def spa_take_class_attendance_redirect(class_id: int):
    """Redirect legacy take-class-attendance GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    path = f"/app/management/attendance/take/{class_id}"
    date = request.args.get("date", "").strip()
    if date:
        path = f"{path}?date={date}"
    return redirect(path)


def spa_closure_dashboard_redirect(closure_id: int):
    """Redirect legacy closure dashboard GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET":
        return None
    return redirect(f"/app/management/school-year/closure/{closure_id}")

