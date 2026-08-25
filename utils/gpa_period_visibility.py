"""
Quarter / semester GPA visibility for student-facing (and shared) UI.

Official period GPA is hidden until one week after 4:00 PM America/New_York
on the period's end date, so staff can finalize grades.

Uses pytz for Eastern time so Windows deployments without tzdata still work.

Roster / academic-concerns year GPA is gated the same way on active-year Q1:
unlocked only when Q1 visibility is ``released``.
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any

import pytz

if TYPE_CHECKING:
    from datetime import date

EST = pytz.timezone("America/New_York")
GPA_RELEASE_HOUR = 16  # 4 PM Eastern
CALCULATING_DAYS = 7

_log = logging.getLogger(__name__)
_missing_q1_warned_years: set[int] = set()


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


def active_year_q1_period(school_year_id: int | None = None) -> Any | None:
    """
    Return the Q1 AcademicPeriod for the given (or active) school year.

    Matches period_type ``quarter`` and name ``Q1`` (case-insensitive).
    """
    from models import AcademicPeriod, SchoolYear

    year_id = school_year_id
    if year_id is None:
        active = SchoolYear.query.filter_by(is_active=True).first()
        if not active:
            return None
        year_id = int(active.id)

    period = (
        AcademicPeriod.query.filter(
            AcademicPeriod.school_year_id == int(year_id),
            AcademicPeriod.period_type == "quarter",
            AcademicPeriod.name.ilike("Q1"),
        )
        .order_by(AcademicPeriod.id.asc())
        .first()
    )
    if period is None:
        # Some calendars store "1" / "Quarter 1"
        candidates = AcademicPeriod.query.filter(
            AcademicPeriod.school_year_id == int(year_id),
            AcademicPeriod.period_type == "quarter",
        ).all()
        for p in candidates:
            name = (p.name or "").strip().upper().replace(" ", "")
            if name in ("Q1", "1", "QUARTER1"):
                return p
    return period


def roster_gpa_unlocked(school_year_id: int | None = None) -> bool:
    """
    True when year roster GPA and academic-concern alerts may run.

    Unlocks only after official Q1 GPA release for the school year
    (``period_gpa_visibility_state(Q1.end_date) == "released"``).

    If Q1 is not configured, stay locked (no false early-year alerts) and log once.
    """
    from models import SchoolYear

    year_id = school_year_id
    if year_id is None:
        active = SchoolYear.query.filter_by(is_active=True).first()
        if not active:
            return False
        year_id = int(active.id)
    else:
        year_id = int(year_id)

    q1 = active_year_q1_period(year_id)
    if q1 is None:
        if year_id not in _missing_q1_warned_years:
            _missing_q1_warned_years.add(year_id)
            _log.warning(
                "No Q1 academic period for school_year_id=%s; "
                "roster GPA and academic concerns stay locked.",
                year_id,
            )
        return False

    return period_gpa_visibility_state(getattr(q1, "end_date", None)) == "released"
