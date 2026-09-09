"""Pending grade alerts API for management + teacher SPAs."""

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


@spa_api_blueprint.route("/pending-grades")
@login_required
def spa_pending_grades():
    scope = _resolve_scope((request.args.get("scope") or "").strip() or None)
    if not scope:
        return jsonify({"error": "Unauthorized"}), 403

    from utils.pending_grade_alerts import get_pending_grade_alerts_for_user

    return jsonify(get_pending_grade_alerts_for_user(force_scope=scope))
