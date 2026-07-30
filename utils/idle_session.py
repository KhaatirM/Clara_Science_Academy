"""Idle session timeout: log users out after a period without requests."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)
from flask_login import current_user, logout_user


SESSION_LAST_ACTIVITY_KEY = "last_activity_at"
DEFAULT_IDLE_MINUTES = 30

_EXEMPT_PREFIXES = (
    "/static/",
    "/app/assets/",
    "/favicon",
    "/robots.txt",
    "/cron/",
)

_EXEMPT_ENDPOINTS = {
    "static",
    "auth.login",
    "auth.logout",
    "auth.google_login",
    "auth.google_callback",
    "spa_api.spa_health",
}


def idle_timeout_minutes() -> int:
    """Minutes of inactivity before forced logout (env / config, min 5)."""
    raw = current_app.config.get("IDLE_SESSION_TIMEOUT_MINUTES", DEFAULT_IDLE_MINUTES)
    try:
        minutes = int(raw)
    except (TypeError, ValueError):
        minutes = DEFAULT_IDLE_MINUTES
    return max(5, minutes)


def idle_timeout_seconds() -> int:
    return idle_timeout_minutes() * 60


def mark_session_activity() -> None:
    session[SESSION_LAST_ACTIVITY_KEY] = time.time()
    session.permanent = True
    session.modified = True


def _path_is_exempt() -> bool:
    path = request.path or ""
    if request.endpoint in _EXEMPT_ENDPOINTS:
        return True
    for prefix in _EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    if path in ("/login", "/logout", "/health", "/api/spa/health"):
        return True
    return False


def _wants_json() -> bool:
    if (request.path or "").startswith("/api/"):
        return True
    accept = (request.headers.get("Accept") or "").lower()
    if "application/json" in accept and "text/html" not in accept:
        return True
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def enforce_idle_session() -> Any:
    """
    before_request hook: expire authenticated sessions after idle timeout.
    Returns a response when logging the user out; otherwise None.
    """
    if _path_is_exempt():
        return None

    try:
        authenticated = bool(getattr(current_user, "is_authenticated", False))
    except Exception:
        authenticated = False

    if not authenticated:
        return None

    now = time.time()
    last = session.get(SESSION_LAST_ACTIVITY_KEY)
    limit = idle_timeout_seconds()

    if last is not None:
        try:
            idle_for = now - float(last)
        except (TypeError, ValueError):
            idle_for = 0
        if idle_for > limit:
            logout_user()
            session.clear()
            if _wants_json():
                return (
                    jsonify(
                        {
                            "authenticated": False,
                            "error": "idle_timeout",
                            "message": "Signed out due to inactivity. Please sign in again.",
                            "login_url": url_for("auth.login", idle=1, _external=False),
                        }
                    ),
                    401,
                )
            flash("You were signed out after a period of inactivity. Please sign in again.", "info")
            return redirect(url_for("auth.login", idle=1))

    mark_session_activity()
    return None


def register_idle_session_guard(app) -> None:
    """Attach idle timeout enforcement and align permanent cookie lifetime."""
    minutes = DEFAULT_IDLE_MINUTES
    try:
        minutes = max(5, int(app.config.get("IDLE_SESSION_TIMEOUT_MINUTES", DEFAULT_IDLE_MINUTES)))
    except (TypeError, ValueError):
        minutes = DEFAULT_IDLE_MINUTES
    app.config["IDLE_SESSION_TIMEOUT_MINUTES"] = minutes
    # Cookie max age should at least cover one idle window (+ small buffer).
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=minutes + 5)

    @app.before_request
    def _idle_session_guard():
        return enforce_idle_session()
