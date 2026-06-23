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
