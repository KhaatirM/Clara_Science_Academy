from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, Tuple


REMOVAL_SUSPEND_AFTER_DAYS = 183  # ~6 months


@dataclass(frozen=True)
class StudentOuDecision:
    target_ou_path: str
    should_suspend_now: bool
    reason: str


def _derive_grad_year(grad_year: Optional[int], expected_grad_date: Optional[str]) -> Optional[int]:
    """
    Prefer grad_year if present, otherwise derive from expected_grad_date like "06/2034".
    """
    if grad_year:
        try:
            return int(grad_year)
        except Exception:
            return None
    if expected_grad_date and "/" in str(expected_grad_date):
        try:
            return int(str(expected_grad_date).split("/", 1)[1])
        except Exception:
            return None
    return None


def _school_level_from_grade(grade_level: Optional[int]) -> Optional[str]:
    if grade_level is None:
        return None
    g = int(grade_level)
    if g <= 5:
        return "Elementary"
    if 6 <= g <= 8:
        return "Middle School"
    return "High School"


def school_level_group_for_grade(grade_level: Optional[int]) -> Optional[str]:
    """
    Return the school level group key for a student's grade.
    Values: 'elementary', 'middle_school', 'highschool'
    """
    level = _school_level_from_grade(grade_level)
    if level == "Elementary":
        return "elementary"
    if level == "Middle School":
        return "middle_school"
    if level == "High School":
        return "highschool"
    return None


def _after_alumni_cutoff(today: date, grad_year: int) -> bool:
    """
    Alumni rule: move after June 30 of grad_year.
    """
    cutoff = date(int(grad_year), 6, 30)
    return today > cutoff


def resolve_student_ou(
    *,
    grade_level: Optional[int],
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
    is_active: bool,
    marked_for_removal: bool,
    status_updated_at: Optional[datetime],
    today: Optional[date] = None,
) -> StudentOuDecision:
    """
    Single source of truth for student OU placement + suspension rule.

    OU structure assumed (matches your Admin Console):
    - /Students/Elementary/Class of YYYY
    - /Students/Middle School/Class of YYYY
    - /Students/High School/Class of YYYY
    - /Students/Alumni/Class of YYYY
    - /Students/Marked for Removal/Class of YYYY
    """
    today = today or date.today()
    derived_grad_year = _derive_grad_year(grad_year, expected_grad_date)

    # Removal overrides everything else
    if marked_for_removal or (is_active is False):
        class_suffix = f"Class of {derived_grad_year}" if derived_grad_year else "Unknown Class Year"
        ou = f"/Students/Marked for Removal/{class_suffix}"

        # Suspend after ~6 months in removal
        if status_updated_at:
            should_suspend = (datetime.utcnow() - status_updated_at) >= timedelta(days=REMOVAL_SUSPEND_AFTER_DAYS)
        else:
            should_suspend = False
        return StudentOuDecision(
            target_ou_path=ou,
            should_suspend_now=should_suspend,
            reason="marked_for_removal_or_inactive",
        )

    # Alumni rule based on grad year cutoff
    if derived_grad_year and _after_alumni_cutoff(today, int(derived_grad_year)):
        return StudentOuDecision(
            target_ou_path=f"/Students/Alumni/Class of {int(derived_grad_year)}",
            should_suspend_now=False,
            reason="after_grad_year_cutoff",
        )

    # Active students: by school level
    school_level = _school_level_from_grade(grade_level) or "Students"
    if derived_grad_year:
        return StudentOuDecision(
            target_ou_path=f"/Students/{school_level}/Class of {int(derived_grad_year)}",
            should_suspend_now=False,
            reason="active_by_grade_and_grad_year",
        )

    # Fallback when grad year is unknown
    return StudentOuDecision(
        target_ou_path=f"/Students/{school_level}",
        should_suspend_now=False,
        reason="active_missing_grad_year",
    )

