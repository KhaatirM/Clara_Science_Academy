"""JSON API for the React management SPA."""

from __future__ import annotations

from flask import Blueprint, jsonify, url_for
from flask_login import current_user
from flask_wtf.csrf import generate_csrf

from decorators import get_user_permissions
from utils.user_roles import (
    canonical_role_label,
    staff_must_choose_dashboard,
    user_can_use_management_spa_shell,
    user_has_management_entry_access,
    user_has_parent_spa_entry,
    user_has_student_spa_entry,
    user_has_teacher_spa_entry,
    user_has_tech_spa_entry,
)

spa_api_blueprint = Blueprint("spa_api", __name__, url_prefix="/api/spa")


def _sidebar_title(user) -> str:
    role = canonical_role_label(getattr(user, "role", None))
    if role in ("Director", "School Administrator"):
        return role
    if role == "Parent":
        return "Family Portal"
    if role == "Student":
        return "Student"
    if role in ("Tech", "IT Support"):
        return "Tech"
    if role == "Staff":
        return "Staff"
    if role:
        return role
    return user.username or "User"


@spa_api_blueprint.route("/me")
def spa_me():
    """Current session for the React app (cookie auth)."""
    if not current_user.is_authenticated:
        return jsonify(
            {
                "authenticated": False,
                "login_url": url_for("auth.login", _external=False),
            }
        ), 401

    perms = sorted(get_user_permissions(current_user))
    role_canonical = canonical_role_label(current_user.role)

    staff_dashboard_target = None
    try:
        from flask import session

        if staff_must_choose_dashboard(current_user):
            raw = session.get("staff_dashboard_target")
            if raw in ("tech", "management"):
                staff_dashboard_target = raw
    except Exception:
        staff_dashboard_target = None

    from utils.user_theme import get_effective_theme

    flashes = []
    try:
        from flask import get_flashed_messages

        for category, message in get_flashed_messages(with_categories=True):
            text = (message or "").strip()
            if not text:
                continue
            cat = (category or "info").strip().lower() or "info"
            if cat == "error":
                cat = "danger"
            flashes.append({"category": cat, "message": text})
    except Exception:
        flashes = []

    try:
        from utils.school_timezone import get_school_timezone_sidebar_payload

        tz_payload = get_school_timezone_sidebar_payload()
        school_timezone = {
            "iana": tz_payload.get("school_timezone_iana") or "",
            "clock": tz_payload.get("school_timezone_clock") or "",
            "zone": tz_payload.get("school_timezone_zone") or "",
        }
    except Exception:
        from utils.school_timezone import DEFAULT_SCHOOL_TIMEZONE

        school_timezone = {"iana": DEFAULT_SCHOOL_TIMEZONE, "clock": "", "zone": ""}

    from utils.app_version import app_version_context
    from utils.idle_session import idle_timeout_minutes

    ver = app_version_context()
    return jsonify(
        {
            "authenticated": True,
            "school_timezone": school_timezone,
            "flashes": flashes,
            "idle_timeout_minutes": idle_timeout_minutes(),
            "app_version": {
                "version": ver["app_version"],
                "display": ver["app_version_display"],
                "origin": ver["app_version_origin"],
                "updates_estimate": ver["app_version_updates_estimate"],
                "release_label": ver["app_version_release_label"],
                "product_name": ver["app_version_product_name"],
            },
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role,
                "role_canonical": role_canonical,
                "email": getattr(current_user, "email", None),
                "permissions": perms,
                "management_entry": user_has_management_entry_access(current_user),
                "management_shell": user_can_use_management_spa_shell(current_user),
                "teacher_entry": user_has_teacher_spa_entry(current_user),
                "student_entry": user_has_student_spa_entry(current_user),
                "parent_entry": user_has_parent_spa_entry(current_user),
                "tech_entry": user_has_tech_spa_entry(current_user),
                "staff_dashboard_target": staff_dashboard_target,
                "student_id": getattr(current_user, "student_id", None),
                "sidebar_title": _sidebar_title(current_user),
                "csrf_token": generate_csrf(),
                "theme": get_effective_theme(current_user),
            },
        }
    )


@spa_api_blueprint.route("/health")
def spa_health():
    return jsonify({"ok": True, "service": "spa-api"})


from api_spa import staff as _spa_staff  # noqa: F401, E402
from api_spa import dashboard as _spa_dashboard  # noqa: F401, E402
from api_spa import students as _spa_students  # noqa: F401, E402
from api_spa import parents as _spa_parents  # noqa: F401, E402
from api_spa import classes as _spa_classes  # noqa: F401, E402
from api_spa import assignments as _spa_assignments  # noqa: F401, E402
from api_spa import extensions as _spa_extensions  # noqa: F401, E402
from api_spa import redo as _spa_redo  # noqa: F401, E402
from api_spa import calendar as _spa_calendar  # noqa: F401, E402
from api_spa import school_year_closure as _spa_school_year_closure  # noqa: F401, E402
from api_spa import school_years as _spa_school_years  # noqa: F401, E402
from api_spa import attendance as _spa_attendance  # noqa: F401, E402
from api_spa import report_cards as _spa_report_cards  # noqa: F401, E402
from api_spa import grade_standards as _spa_grade_standards  # noqa: F401, E402
from api_spa import billing as _spa_billing  # noqa: F401, E402
from api_spa import student_jobs as _spa_student_jobs  # noqa: F401, E402
from api_spa import settings as _spa_settings  # noqa: F401, E402
from api_spa import bug_reports as _spa_bug_reports  # noqa: F401, E402
from api_spa import class_tools as _spa_class_tools  # noqa: F401, E402
from api_spa import class_groups as _spa_class_groups  # noqa: F401, E402
from api_spa import teacher_dashboard as _spa_teacher_dashboard  # noqa: F401, E402
from api_spa import teacher_classes as _spa_teacher_classes  # noqa: F401, E402
from api_spa import teacher_tabs as _spa_teacher_tabs  # noqa: F401, E402
from api_spa import teacher_assignments_create as _spa_teacher_assignments_create  # noqa: F401, E402
from api_spa import teacher_assignments_workspace as _spa_teacher_assignments_workspace  # noqa: F401, E402
from api_spa import teacher_extensions_redo as _spa_teacher_extensions_redo  # noqa: F401, E402
from api_spa import teacher_class_tools as _spa_teacher_class_tools  # noqa: F401, E402
from api_spa import student_dashboard as _spa_student_dashboard  # noqa: F401, E402
from api_spa import student_assignments as _spa_student_assignments  # noqa: F401, E402
from api_spa import student_classes as _spa_student_classes  # noqa: F401, E402
from api_spa import student_grades as _spa_student_grades  # noqa: F401, E402
from api_spa import student_collaborate as _spa_student_collaborate  # noqa: F401, E402
from api_spa import student_tabs as _spa_student_tabs  # noqa: F401, E402
from api_spa import student_activities as _spa_student_activities  # noqa: F401, E402
from api_spa import tech as _spa_tech  # noqa: F401, E402
from api_spa import academic_concerns as _spa_academic_concerns  # noqa: F401, E402
from api_spa import class_syllabus as _spa_class_syllabus  # noqa: F401, E402
from api_spa import class_notes as _spa_class_notes  # noqa: F401, E402
from api_spa import parent_dashboard as _spa_parent_dashboard  # noqa: F401, E402
