"""
Effective school IANA timezone for the whole application.

Resolution order:
1. SystemConfig key ``school_timezone`` (set by Tech on System → Configuration) if non-empty and valid
2. Flask ``SCHOOL_TIMEZONE`` from environment / config.py
3. ``America/New_York``

Cached on ``flask.g`` for the duration of each HTTP request to limit DB reads.
"""

from __future__ import annotations

DEFAULT_SCHOOL_TIMEZONE = "America/New_York"
SYSTEM_CONFIG_KEY = "school_timezone"


def is_valid_iana_tz(name: str) -> bool:
    if not name or not str(name).strip():
        return False
    s = str(name).strip()
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(s)
        return True
    except Exception:
        try:
            import pytz

            pytz.timezone(s)
            return True
        except Exception:
            return False


def _env_school_timezone(app) -> str:
    v = (app.config.get("SCHOOL_TIMEZONE") or "").strip()
    return v or DEFAULT_SCHOOL_TIMEZONE


def _resolve_school_timezone_string(app) -> str:
    """Resolve effective zone (may query SystemConfig)."""
    from models import SystemConfig

    env_tz = _env_school_timezone(app)
    raw = (SystemConfig.get_value(SYSTEM_CONFIG_KEY, "") or "").strip()
    if not raw:
        return env_tz
    if is_valid_iana_tz(raw):
        return raw
    return env_tz


def get_school_timezone_name():
    """
    Effective IANA timezone name for assignment parsing, ``schooltime`` filter, reminders, etc.
    """
    from flask import current_app, g, has_request_context

    if has_request_context():
        if "_school_timezone_name" in g:
            return g._school_timezone_name
        resolved = _resolve_school_timezone_string(current_app)
        g._school_timezone_name = resolved
        return resolved
    return _resolve_school_timezone_string(current_app)
