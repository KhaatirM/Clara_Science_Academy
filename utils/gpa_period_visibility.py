"""
Quarter / semester GPA visibility for student-facing (and shared) UI.

Official period GPA is hidden until one week after 4:00 PM America/New_York
on the period's end date, so staff can finalize grades.

Uses pytz for Eastern time so Windows deployments without tzdata still work.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

import pytz

if TYPE_CHECKING:
    from datetime import date

EST = pytz.timezone("America/New_York")
GPA_RELEASE_HOUR = 16  # 4 PM Eastern
CALCULATING_DAYS = 7


def period_gpa_visibility_state(period_end_date: date | None) -> str:
    """
    Return where we are relative to official GPA release for an academic period.

    - in_progress: before 4:00 PM Eastern on period_end_date
    - calculating: from that moment until 7 full days later (grades being finalized)
    - released: after the 7-day window (show quarter/semester GPA as usual)

    If period_end_date is None, treat as released (no gating).
    """
    if period_end_date is None:
        return "released"

    now_est = datetime.now(EST)
    release_at = EST.localize(datetime.combine(period_end_date, time(GPA_RELEASE_HOUR, 0, 0)))
    visible_at = release_at + timedelta(days=CALCULATING_DAYS)

    if now_est < release_at:
        return "in_progress"
    if now_est < visible_at:
        return "calculating"
    return "released"
