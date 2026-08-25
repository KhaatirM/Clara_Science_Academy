"""Academic concerns (at-risk GPA) API for management + teacher SPAs."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import is_teacher_role
from utils.user_roles import all_role_strings, user_has_management_entry_access

from . import spa_api_blueprint


def _resolve_scope(requested: str | None) -> str | None:
    is_admin = user_has_management_entry_access(current_user)
    is_teacher = any(is_teacher_role(r) for r in all_role_strings(current_user))
    if requested in ("management", "teacher"):
        if requested == "management" and not is_admin:
            return None
        if requested == "teacher" and not (is_teacher or is_admin):
            return None
        return requested
    if is_admin:
        return "management"
    if is_teacher:
        return "teacher"
    return None


@spa_api_blueprint.route("/academic-concerns")
@login_required
def spa_academic_concerns():
    scope = _resolve_scope((request.args.get("scope") or "").strip() or None)
    if not scope:
        return jsonify({"error": "Unauthorized"}), 403

    from utils.school_year_filters import get_active_school_year
    from utils.at_risk_alerts import get_at_risk_alerts_for_user
    from utils.gpa_period_visibility import roster_gpa_unlocked

    active_year = get_active_school_year()
    if not active_year:
        return jsonify(
            {
                "scope": scope,
                "schoolwide": scope == "management",
                "has_active_school_year": False,
                "school_year": None,
                "roster_gpa_unlocked": False,
                "alerts": [],
                "failing_count": 0,
                "overdue_count": 0,
                "not_submitted_count": 0,
                "count": 0,
                "details_base": (
                    "/management/student"
                    if scope == "management"
                    else "/teacher/student"
                ),
            }
        )

    gpa_unlocked = roster_gpa_unlocked(active_year.id)
    alerts, failing, overdue, not_submitted = get_at_risk_alerts_for_user(force_scope=scope)
    return jsonify(
        {
            "scope": scope,
            "schoolwide": scope == "management",
            "has_active_school_year": True,
            "school_year": {
                "id": active_year.id,
                "name": active_year.name,
            },
            "roster_gpa_unlocked": gpa_unlocked,
            "alerts": alerts or [],
            "failing_count": failing or 0,
            "overdue_count": overdue or 0,
            "not_submitted_count": not_submitted or 0,
            "count": len(alerts or []),
            "details_base": (
                "/management/student"
                if scope == "management"
                else "/teacher/student"
            ),
        }
    )


@spa_api_blueprint.route("/academic-concerns/<int:student_id>")
@login_required
def spa_academic_concern_student(student_id: int):
    """Proxy to existing management/teacher student details/data handlers."""
    from utils.school_year_filters import get_active_school_year

    if not get_active_school_year():
        return jsonify(
            {
                "success": False,
                "error": "Academic concerns are only available during an active school year.",
            }
        ), 404

    scope = _resolve_scope((request.args.get("scope") or "").strip() or None)
    if not scope:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    if scope == "management":
        from management_routes.students import view_student_details_data

        return view_student_details_data(student_id)

    from teacher_routes.dashboard import view_student_details_data as teacher_details

    return teacher_details(student_id)
