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


def _sanitize_ou_path(path: str) -> str:
    """Strip trailing slashes so Google Admin SDK paths are consistent."""
    if not path:
        return "/"
    out = path.rstrip("/")
    return out if out else "/"


def _legacy_stored_grad_year(
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
) -> Optional[int]:
    """Older DB fields only (not expected_graduation_year). Used after formula inference."""
    if grad_year is not None:
        try:
            return int(grad_year)
        except Exception:
            pass
    if expected_grad_date and "/" in str(expected_grad_date):
        try:
            return int(str(expected_grad_date).split("/", 1)[1])
        except Exception:
            return None
    return None


def _infer_grad_year_from_grade(grade_level: Optional[int], reference_year: int) -> Optional[int]:
    """
    Graduation calendar year when only grade is reliable:
    Graduation Year = reference_year + (12 - grade). K=0 … 12th=12.
    Example: reference_year 2026, grade 5 -> 2026 + (12 - 5) = 2033; grade 4 -> 2034.
    """
    if grade_level is None:
        return None
    try:
        g = int(grade_level)
    except (TypeError, ValueError):
        return None
    if g < 0 or g > 12:
        return None
    try:
        ry = int(reference_year)
    except (TypeError, ValueError):
        ry = date.today().year
    return ry + (12 - g)


def _effective_grad_year(
    grade_level: Optional[int],
    expected_graduation_year: Optional[int],
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
    reference_year: int,
) -> Optional[int]:
    """
    Resolution order (OU + groups):
    1. expected_graduation_year (authoritative when set)
    2. Calculated: reference_year + (12 - grade) when grade is known
    3. Legacy: grad_year, then expected_grad_date (e.g. missing grade on old records)
    """
    if expected_graduation_year is not None:
        try:
            return int(expected_graduation_year)
        except Exception:
            pass
    inferred = _infer_grad_year_from_grade(grade_level, reference_year)
    if inferred is not None:
        return int(inferred)
    legacy = _legacy_stored_grad_year(grad_year, expected_grad_date)
    if legacy is not None:
        return int(legacy)
    return None


def effective_graduation_year(
    *,
    grade_level: Optional[int],
    expected_graduation_year: Optional[int],
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
    reference_year: Optional[int] = None,
) -> Optional[int]:
    """Public helper for sync scripts (groups, reporting): same calendar year source as OU policy."""
    ref = reference_year if reference_year is not None else date.today().year
    return _effective_grad_year(grade_level, expected_graduation_year, grad_year, expected_grad_date, ref)


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


def _compute_ou_path_and_reason(
    *,
    grade_level: Optional[int],
    expected_graduation_year: Optional[int],
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
    is_active: bool,
    marked_for_removal: bool,
    today: date,
) -> Tuple[str, str]:
    reference_year = today.year
    effective = _effective_grad_year(
        grade_level, expected_graduation_year, grad_year, expected_grad_date, reference_year
    )

    grade_display = grade_level if grade_level is not None else "unknown"

    # Removal / inactive overrides
    if marked_for_removal or (is_active is False):
        class_suffix = f"Class of {effective}" if effective else "Unknown Class Year"
        path = _sanitize_ou_path(f"/Students/Marked for Removal/{class_suffix}")
        print(f"[DEBUG] Calculated OU for {grade_display} grade student: {path}")
        return path, "marked_for_removal_or_inactive"

    # Alumni (still "active" in workflow sense — uses graduation year from DB or inference)
    if effective is not None and _after_alumni_cutoff(today, int(effective)):
        path = _sanitize_ou_path(f"/Students/Alumni/Class of {int(effective)}")
        print(f"[DEBUG] Calculated OU for {grade_display} grade student: {path}")
        return path, "after_grad_year_cutoff"

    # Active students: /Students/[SchoolLevel]/Class of [Year] when we have a year (DB or inferred)
    school_level = _school_level_from_grade(grade_level) or "Students"
    if effective is not None:
        path = _sanitize_ou_path(f"/Students/{school_level}/Class of {int(effective)}")
        print(f"[DEBUG] Calculated OU for {grade_display} grade student: {path}")
        return path, "active_by_grade_and_grad_year"

    # No grade and no grad data: cannot infer — last resort without class folder
    path = _sanitize_ou_path(f"/Students/{school_level}")
    print(f"[DEBUG] Calculated OU for {grade_display} grade student: {path}")
    return path, "active_missing_grad_year"


def get_student_ou_path(
    *,
    grade_level: Optional[int],
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
    is_active: bool,
    marked_for_removal: bool,
    expected_graduation_year: Optional[int] = None,
    today: Optional[date] = None,
) -> str:
    """
    Compute the Google Workspace orgUnitPath for a student.

    - ``expected_graduation_year`` (when set) is the primary graduation year for ``/Class of [Year]``.
    - Then ``grad_year``, then ``expected_grad_date``; otherwise the year may be inferred from grade.
    - School level: K–5 Elementary, 6–8 Middle School, 9–12 High School.
    - Paths are normalized (no trailing slash).
    """
    path, _ = _compute_ou_path_and_reason(
        grade_level=grade_level,
        expected_graduation_year=expected_graduation_year,
        grad_year=grad_year,
        expected_grad_date=expected_grad_date,
        is_active=is_active,
        marked_for_removal=marked_for_removal,
        today=today or date.today(),
    )
    return path


def resolve_student_ou(
    *,
    grade_level: Optional[int],
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
    is_active: bool,
    marked_for_removal: bool,
    status_updated_at: Optional[datetime],
    expected_graduation_year: Optional[int] = None,
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
    target_ou_path, reason = _compute_ou_path_and_reason(
        grade_level=grade_level,
        expected_graduation_year=expected_graduation_year,
        grad_year=grad_year,
        expected_grad_date=expected_grad_date,
        is_active=is_active,
        marked_for_removal=marked_for_removal,
        today=today,
    )

    should_suspend = False
    if reason == "marked_for_removal_or_inactive":
        if status_updated_at:
            should_suspend = (datetime.utcnow() - status_updated_at) >= timedelta(days=REMOVAL_SUSPEND_AFTER_DAYS)
        else:
            should_suspend = False

    return StudentOuDecision(
        target_ou_path=target_ou_path,
        should_suspend_now=should_suspend,
        reason=reason,
    )
