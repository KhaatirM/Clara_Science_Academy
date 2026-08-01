"""Effective maintenance mode helpers.

``MaintenanceMode.is_active`` is a sticky flag — it stays True until someone clicks
Stop. Callers that only check ``is_active`` keep treating the portal as under
maintenance after the scheduled end time (notably dual-dashboard School
management gating and the Tech System status panel).

This module resolves the *effective* window: active, not past ``end_time``, and
optionally auto-clears expired rows so the DB matches reality.
"""

from __future__ import annotations

from datetime import datetime, timezone

from models import MaintenanceMode, db


def ensure_aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_window_current(maintenance: MaintenanceMode, now: datetime | None = None) -> bool:
    if not maintenance or not maintenance.is_active:
        return False
    end = ensure_aware_utc(maintenance.end_time)
    if end is None:
        # No end time — treat sticky is_active as still on.
        return True
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return end > current


def expire_stale_maintenance_sessions() -> int:
    """Deactivate any is_active rows whose end_time has passed. Returns count cleared."""
    now = datetime.now(timezone.utc)
    rows = MaintenanceMode.query.filter_by(is_active=True).all()
    cleared = 0
    for row in rows:
        if not _is_window_current(row, now=now):
            row.is_active = False
            cleared += 1
    if cleared:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return 0
    return cleared


def get_active_maintenance(*, auto_expire: bool = True) -> MaintenanceMode | None:
    """
    Return the maintenance session that should currently block the public portal.

    When ``auto_expire`` is True, past-due ``is_active`` rows are turned off so
    Tech UI and dual-dashboard gating stop treating them as live.
    """
    try:
        if auto_expire:
            expire_stale_maintenance_sessions()
        row = MaintenanceMode.query.filter_by(is_active=True).first()
    except Exception:
        return None
    if row and _is_window_current(row):
        return row
    return None


def maintenance_is_active(*, auto_expire: bool = True) -> bool:
    return get_active_maintenance(auto_expire=auto_expire) is not None
