"""Effective UI theme for authenticated users (site override or preference)."""

from __future__ import annotations

THEME_ORDER = (
    "default",
    "light",
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
    "coral",
    "sapphire",
    "honey",
    "slate",
)

THEME_CHOICES = frozenset(THEME_ORDER)

# Retired themes fall back to Default so stored preferences cannot keep them on.
REMOVED_THEMES = frozenset({"dark"})


def normalize_theme_name(value) -> str | None:
    """Map a stored theme to a current choice. Retired themes become Default."""
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    if normalized in REMOVED_THEMES:
        return "default"
    if normalized in THEME_CHOICES:
        return normalized
    return None


def get_effective_theme(user) -> str:
    """Return the theme class suffix (e.g. ``ocean``) for the signed-in user."""
    try:
        from models import SystemConfig

        site_override = normalize_theme_name(SystemConfig.get_value("site_theme_override"))
        if site_override:
            return site_override
    except Exception:
        pass

    pref = getattr(user, "theme_preference", None) if user is not None else None
    return normalize_theme_name(pref) or "default"


def get_site_theme_override() -> str | None:
    try:
        from models import SystemConfig

        raw = SystemConfig.get_value("site_theme_override")
        if not raw:
            return None
        return normalize_theme_name(raw)
    except Exception:
        return None
