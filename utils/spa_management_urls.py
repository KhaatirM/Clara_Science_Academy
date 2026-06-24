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
}


def react_spa_enabled() -> bool:
    return bool(current_app.config.get("REACT_SPA_ENABLED"))


def user_should_use_spa_management_shell() -> bool:
    """Directors/admins use the React shell; permission-only staff stay on legacy pages."""
    if not react_spa_enabled():
        return False
    try:
        from flask_login import current_user
        from utils.user_roles import user_has_management_entry_access

        return bool(
            current_user.is_authenticated and user_has_management_entry_access(current_user)
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
    if request.method != "GET" or request.args.get("legacy") == "1":
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
    if request.method != "GET" or request.args.get("legacy") == "1":
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
    """Redirect legacy discussion create GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    if request.args.get("edit"):
        return None
    path = "/app/management/assignments/create/discussion"
    class_id = request.args.get("class_id", "").strip()
    if class_id.isdigit():
        path = f"{path}?class_id={class_id}"
    return redirect(path)


def spa_create_quiz_redirect():
    """Redirect legacy quiz create GET to the React SPA (new quizzes only)."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    if request.args.get("edit"):
        return None
    path = "/app/management/assignments/create/quiz"
    class_id = request.args.get("class_id", "").strip()
    if class_id.isdigit():
        path = f"{path}?class_id={class_id}"
    return redirect(path)


def spa_group_class_picker_redirect():
    """Redirect legacy group class picker GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect("/app/management/assignments/create/group")


def spa_group_type_selector_redirect(class_id: int):
    """Redirect legacy group type selector GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect(f"/app/management/assignments/create/group/{class_id}")


def spa_group_pdf_create_redirect(class_id: int):
    """Redirect legacy group PDF create GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect(f"/app/management/assignments/create/group/{class_id}/pdf")


def spa_group_quiz_create_redirect(class_id: int):
    """Redirect legacy group quiz create GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect(f"/app/management/assignments/create/group/{class_id}/quiz")


def spa_assignments_hub_redirect():
    """Redirect legacy assignments & grades hub GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
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
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect("/app/management/extensions")


def spa_redo_dashboard_redirect():
    """Redirect legacy redo dashboard GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect("/app/management/redo")


def spa_assignment_view_redirect(assignment_id: int, *, is_group: bool = False):
    from flask import redirect, request
    from models import Assignment, GroupAssignment

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    if is_group:
        ga = GroupAssignment.query.get(assignment_id)
        if not ga:
            return None
        return redirect(f"/app/management/assignments/{ga.class_id}/group/{ga.id}/view")
    assignment = Assignment.query.get(assignment_id)
    if not assignment or not assignment.class_id:
        return None
    if (assignment.assignment_type or "") == "discussion":
        return None
    return redirect(f"/app/management/assignments/{assignment.class_id}/individual/{assignment.id}/view")


def spa_assignment_grade_redirect(assignment_id: int, *, is_group: bool = False):
    from flask import redirect, request
    from models import Assignment, GroupAssignment, QuizQuestion

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    if is_group:
        ga = GroupAssignment.query.get(assignment_id)
        if not ga:
            return None
        return redirect(f"/app/management/assignments/{ga.class_id}/group/{ga.id}/grade")
    assignment = Assignment.query.get(assignment_id)
    if not assignment or not assignment.class_id:
        return None
    atype = assignment.assignment_type or ""
    if atype == "discussion":
        return None
    if atype == "quiz":
        questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).all()
        if not any(q.question_type in ("short_answer", "essay") for q in questions):
            return None
    return redirect(f"/app/management/assignments/{assignment.class_id}/individual/{assignment.id}/grade")


def spa_class_workflow_redirect(class_id: int, suffix: str = ""):
    """Redirect legacy class workflow GET requests to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    path = f"/app/management/classes/{class_id}"
    if suffix:
        path = f"{path}/{suffix}"
    query = request.query_string.decode("utf-8") if request.query_string else ""
    if query:
        path = f"{path}?{query}"
    return redirect(path)


def spa_calendar_redirect():
    """Redirect legacy school calendar GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    path = "/app/management/calendar"
    query = request.query_string.decode("utf-8") if request.query_string else ""
    if query:
        path = f"{path}?{query}"
    return redirect(path)


def spa_closure_schedule_redirect():
    """Redirect legacy closure schedule GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect("/app/management/school-year/closure/schedule")


def spa_school_years_redirect():
    """Redirect legacy school years GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect("/app/management/school-years")


def spa_closure_dashboard_redirect(closure_id: int):
    """Redirect legacy closure dashboard GET to the React SPA."""
    from flask import redirect, request

    if not user_should_use_spa_management_shell():
        return None
    if request.method != "GET" or request.args.get("legacy") == "1":
        return None
    return redirect(f"/app/management/school-year/closure/{closure_id}")
