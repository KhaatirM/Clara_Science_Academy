"""Management settings data for the React SPA."""

from __future__ import annotations

from typing import Any

from models import User
from utils.user_roles import canonical_role_label

THEME_OPTIONS = [
    {"value": "default", "label": "Default", "group": "Standard"},
    {"value": "light", "label": "Light", "group": "Standard"},
    {"value": "dark", "label": "Dark", "group": "Standard"},
    {"value": "snowy", "label": "Snowy (Winter)", "group": "Seasonal"},
    {"value": "autumn", "label": "Autumn", "group": "Seasonal"},
    {"value": "spring", "label": "Spring", "group": "Seasonal"},
    {"value": "summer", "label": "Summer", "group": "Seasonal"},
    {"value": "holiday", "label": "Holiday", "group": "Seasonal"},
    {"value": "ocean", "label": "Ocean", "group": "Color"},
    {"value": "forest", "label": "Forest", "group": "Color"},
    {"value": "sunset", "label": "Sunset", "group": "Color"},
    {"value": "midnight", "label": "Midnight", "group": "Color"},
    {"value": "desert", "label": "Desert", "group": "Color"},
    {"value": "lavender", "label": "Lavender", "group": "Color"},
    {"value": "rose", "label": "Rose", "group": "Color"},
    {"value": "cherry", "label": "Cherry Blossom", "group": "Color"},
    {"value": "aurora", "label": "Aurora", "group": "Color"},
    {"value": "storm", "label": "Storm", "group": "Color"},
    {"value": "wine", "label": "Wine", "group": "Color"},
    {"value": "mint", "label": "Mint", "group": "Color"},
]


def query_settings_hub(*, user) -> dict[str, Any]:
    db_user = User.query.get(user.id) if getattr(user, "id", None) else None
    role = canonical_role_label(getattr(user, "role", None))
    google_connected = bool(db_user and db_user.google_refresh_token)

    return {
        "role_canonical": role,
        "is_director": role == "Director",
        "account": {
            "username": user.username,
            "email": getattr(user, "email", None),
            "role": getattr(user, "role", None),
        },
        "preferences": {
            "theme": (db_user.theme_preference if db_user else None) or "default",
            "theme_options": THEME_OPTIONS,
            "notifications_coming_soon": True,
            "timezone_coming_soon": True,
        },
        "google": {
            "connected": google_connected,
            "connect_url": "/management/google-account/connect",
            "disconnect_url": "/management/google-account/disconnect",
        },
        "urls": {
            "home": "/management",
            "change_password": "/change-password",
            "bug_reports_tab": "/management/settings/bug-reports",
        },
    }
