"""Effective UI theme for authenticated users (site override or preference)."""

from __future__ import annotations

THEME_CHOICES = frozenset(
    {
        "default",
        "light",
        "dark",
        "snowy",
        "autumn",
        "spring",
        "summer",
        "holiday",
        "ocean",
        "forest",
        "sunset",
        "midnight",
        "desert",
        "lavender",
        "rose",
        "cherry",
        "aurora",
        "storm",
        "wine",
        "mint",
    }
)


def get_effective_theme(user) -> str:
    """Return the theme class suffix (e.g. ``ocean``) for the signed-in user."""
    try:
        from models import SystemConfig

        site_override = SystemConfig.get_value("site_theme_override")
        if site_override:
            normalized = str(site_override).strip().lower()
            if normalized in THEME_CHOICES:
                return normalized
    except Exception:
        pass

    pref = getattr(user, "theme_preference", None) if user is not None else None
    if pref:
        normalized = str(pref).strip().lower()
        if normalized in THEME_CHOICES:
            return normalized
    return "default"


def get_site_theme_override() -> str | None:
    try:
        from models import SystemConfig

        raw = SystemConfig.get_value("site_theme_override")
        if not raw:
            return None
        normalized = str(raw).strip().lower()
        return normalized if normalized in THEME_CHOICES else None
    except Exception:
        return None
