"""JSON API for the React management SPA."""

from __future__ import annotations

from flask import Blueprint, jsonify, url_for
from flask_login import current_user
from flask_wtf.csrf import generate_csrf

from decorators import get_user_permissions
from utils.user_roles import canonical_role_label, user_has_management_entry_access

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

    return jsonify(
        {
            "authenticated": True,
            "school_timezone": school_timezone,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role,
                "role_canonical": role_canonical,
                "email": getattr(current_user, "email", None),
                "permissions": perms,
                "management_entry": user_has_management_entry_access(current_user),
                "sidebar_title": _sidebar_title(current_user),
                "csrf_token": generate_csrf(),
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
