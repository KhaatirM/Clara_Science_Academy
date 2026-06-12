from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from models import TeacherStaff as TeacherStaffModel
    from models import User as UserModel


# --- Student lifecycle timers ---
ALUMNI_SUSPEND_AFTER_DAYS = 365  # 1 year in Alumni before Google deactivation
REMOVAL_SUSPEND_AFTER_DAYS = 183  # legacy alias; transferred departures suspend immediately

# Set True when /Students/High School is live; until then grades 9–12 use Alumni/Middle.
HIGH_SCHOOL_OU_ENABLED = False

STUDENT_OU_TRANSFERRED_REMOVED = "Transferred & Removed"
STUDENT_OU_ALUMNI = "Alumni"
ALUMNI_SUB_ELEMENTARY = "Elementary"
ALUMNI_SUB_MIDDLE = "Middle"
ALUMNI_SUB_HIGH = "High"

# Top grade of each division before promotion to the next (5→6, 8→9, 12→done).
_DIVISION_TOP_GRADE = {
    ALUMNI_SUB_ELEMENTARY: 5,
    ALUMNI_SUB_MIDDLE: 8,
    ALUMNI_SUB_HIGH: 12,
}


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
    if not out:
        return "/"
    # Legacy OU segment: keep singular ``Administrator`` (not ``Administrators``).
    if "/Staff/Administrators" in out:
        out = out.replace("/Staff/Administrators", "/Staff/Administrator")
    return out


def _parse_grade_level(grade_level) -> Optional[int]:
    from utils.student_login_policy import parse_grade_level_for_policy

    return parse_grade_level_for_policy(grade_level)


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
    3. Legacy: grad_year, then expected_grad_date
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


def break_window_for_date(
    as_of: date,
    *,
    prior_school_year_end: Optional[date] = None,
    next_school_year_start: Optional[date] = None,
) -> Tuple[Optional[date], Optional[date]]:
    """
    Return (prior_end, next_start) when ``as_of`` falls in the summer gap between two school years.
    Uses explicit dates when provided; otherwise queries SchoolYear rows; finally Jul–Aug fallback.
    """
    if prior_school_year_end and next_school_year_start:
        if prior_school_year_end < next_school_year_start and prior_school_year_end < as_of < next_school_year_start:
            return prior_school_year_end, next_school_year_start
        return None, None

    try:
        from models import SchoolYear

        years = SchoolYear.query.order_by(SchoolYear.start_date).all()
        for idx in range(len(years) - 1):
            y1, y2 = years[idx], years[idx + 1]
            if y1.end_date < as_of < y2.start_date:
                return y1.end_date, y2.start_date
    except Exception:
        pass

    if as_of.month in (7, 8):
        return date(as_of.year, 6, 30), date(as_of.year, 8, 31)
    return None, None


def _in_summer_break_window(
    as_of: date,
    *,
    prior_school_year_end: Optional[date] = None,
    next_school_year_start: Optional[date] = None,
) -> bool:
    prior_end, next_start = break_window_for_date(
        as_of,
        prior_school_year_end=prior_school_year_end,
        next_school_year_start=next_school_year_start,
    )
    return bool(prior_end and next_start)


def _class_suffix(effective: Optional[int]) -> str:
    return f"Class of {effective}" if effective else "Unknown Class Year"


def _alumni_path(alumni_sub: str, effective: Optional[int]) -> str:
    return _sanitize_ou_path(
        f"/Students/{STUDENT_OU_ALUMNI}/{alumni_sub}/{_class_suffix(effective)}"
    )


def _transferred_path(effective: Optional[int]) -> str:
    return _sanitize_ou_path(
        f"/Students/{STUDENT_OU_TRANSFERRED_REMOVED}/{_class_suffix(effective)}"
    )


def _alumni_sub_for_summer_departure(grade: int) -> Optional[str]:
    """
    Alumni tier when a student leaves during the summer gap after completing a division.

    - Finished 5th (grade 5) or promoted to 6th → Elementary alumni
    - Finished 8th (grade 8) or promoted to 9th–11th → Middle alumni
    - Finished 12th (grade 12) → High alumni
    """
    if grade == _DIVISION_TOP_GRADE[ALUMNI_SUB_ELEMENTARY] or grade == 6:
        return ALUMNI_SUB_ELEMENTARY
    if grade == _DIVISION_TOP_GRADE[ALUMNI_SUB_MIDDLE] or (9 <= grade <= 11):
        return ALUMNI_SUB_MIDDLE
    if grade >= _DIVISION_TOP_GRADE[ALUMNI_SUB_HIGH]:
        return ALUMNI_SUB_HIGH
    return None


def _active_student_ou_path(grade: Optional[int], effective: Optional[int]) -> Tuple[str, str]:
    """OU for enrolled, active students."""
    if grade is None:
        school_level = "Students"
        if effective is not None:
            return _sanitize_ou_path(f"/Students/{school_level}/{_class_suffix(effective)}"), "active_missing_grade"
        return _sanitize_ou_path(f"/Students/{school_level}"), "active_missing_grade"

    if grade <= 5:
        path = _sanitize_ou_path(f"/Students/Elementary/{_class_suffix(effective)}")
        return path, "active_elementary"

    if grade <= 8:
        path = _sanitize_ou_path(f"/Students/Middle School/{_class_suffix(effective)}")
        return path, "active_middle_school"

    # Grades 9–12: High School OU when launched; otherwise Middle alumni cohort (no HS yet).
    if HIGH_SCHOOL_OU_ENABLED:
        path = _sanitize_ou_path(f"/Students/High School/{_class_suffix(effective)}")
        return path, "active_high_school"

    return _alumni_path(ALUMNI_SUB_MIDDLE, effective), "active_promoted_middle_alumni"


def _departure_ou_path_and_reason(
    *,
    grade: Optional[int],
    effective: Optional[int],
    event_date: date,
    prior_school_year_end: Optional[date],
    next_school_year_start: Optional[date],
) -> Tuple[str, str]:
    """
    Classify a departing student:

    - **Summer gap** after completing a division (5th→6th, 8th→9th, 12th done) → Alumni/{tier}
    - **Mid-year** or left before that milestone → Transferred & Removed
    """
    if grade is None:
        return _transferred_path(effective), "transferred_removed"

    in_summer = _in_summer_break_window(
        event_date,
        prior_school_year_end=prior_school_year_end,
        next_school_year_start=next_school_year_start,
    )

    if in_summer:
        alumni_sub = _alumni_sub_for_summer_departure(grade)
        if alumni_sub:
            return _alumni_path(alumni_sub, effective), "alumni_completed_level"

    return _transferred_path(effective), "transferred_removed"


def _is_departing(*, is_active: bool, marked_for_removal: bool, is_deleted: bool) -> bool:
    return bool(is_deleted or marked_for_removal or not is_active)


def _compute_ou_path_and_reason(
    *,
    grade_level,
    expected_graduation_year: Optional[int],
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
    is_active: bool,
    marked_for_removal: bool,
    is_deleted: bool,
    status_updated_at: Optional[datetime],
    today: date,
    prior_school_year_end: Optional[date],
    next_school_year_start: Optional[date],
) -> Tuple[str, str]:
    reference_year = today.year
    grade = _parse_grade_level(grade_level)
    effective = _effective_grad_year(
        grade, expected_graduation_year, grad_year, expected_grad_date, reference_year
    )

    if _is_departing(is_active=is_active, marked_for_removal=marked_for_removal, is_deleted=is_deleted):
        event_date = status_updated_at.date() if status_updated_at else today
        return _departure_ou_path_and_reason(
            grade=grade,
            effective=effective,
            event_date=event_date,
            prior_school_year_end=prior_school_year_end,
            next_school_year_start=next_school_year_start,
        )

    return _active_student_ou_path(grade, effective)


def get_student_ou_path(
    *,
    grade_level: Optional[int],
    grad_year: Optional[int],
    expected_grad_date: Optional[str],
    is_active: bool,
    marked_for_removal: bool,
    is_deleted: bool = False,
    expected_graduation_year: Optional[int] = None,
    today: Optional[date] = None,
) -> str:
    """
    Compute the Google Workspace orgUnitPath for a student.

    Active paths:
    - /Students/Elementary/Class of YYYY (K–5)
    - /Students/Middle School/Class of YYYY (6–8)
    - /Students/High School/Class of YYYY (9–12 when HIGH_SCHOOL_OU_ENABLED)
    - /Students/Alumni/Middle/Class of YYYY (9–12 while high school OU is not live)

    Departure paths:
    - /Students/Alumni/{Elementary|Middle|High}/Class of YYYY — completed a division (summer leave)
    - /Students/Transferred & Removed/Class of YYYY — mid-year or left before division completion
    """
    path, _ = _compute_ou_path_and_reason(
        grade_level=grade_level,
        expected_graduation_year=expected_graduation_year,
        grad_year=grad_year,
        expected_grad_date=expected_grad_date,
        is_active=is_active,
        marked_for_removal=marked_for_removal,
        is_deleted=is_deleted,
        status_updated_at=None,
        today=today or date.today(),
        prior_school_year_end=None,
        next_school_year_start=None,
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
    is_deleted: bool = False,
    today: Optional[date] = None,
    prior_school_year_end: Optional[date] = None,
    next_school_year_start: Optional[date] = None,
) -> StudentOuDecision:
    """
    Single source of truth for student OU placement + suspension rule.

    Suspension:
    - **Transferred & Removed** — immediate Google suspension when departing
    - **Alumni** (completed division) — 1 year after ``status_updated_at``, then suspend
    - **Active** — never suspended via this policy
    """
    today = today or date.today()
    target_ou_path, reason = _compute_ou_path_and_reason(
        grade_level=grade_level,
        expected_graduation_year=expected_graduation_year,
        grad_year=grad_year,
        expected_grad_date=expected_grad_date,
        is_active=is_active,
        marked_for_removal=marked_for_removal,
        is_deleted=is_deleted,
        status_updated_at=status_updated_at,
        today=today,
        prior_school_year_end=prior_school_year_end,
        next_school_year_start=next_school_year_start,
    )

    should_suspend = False
    if reason == "alumni_completed_level":
        if status_updated_at:
            as_of = datetime.combine(today, datetime.min.time())
            if status_updated_at.tzinfo is not None and as_of.tzinfo is None:
                as_of = as_of.replace(tzinfo=status_updated_at.tzinfo)
            should_suspend = (as_of - status_updated_at) >= timedelta(days=ALUMNI_SUSPEND_AFTER_DAYS)
    elif reason == "transferred_removed":
        should_suspend = True

    return StudentOuDecision(
        target_ou_path=target_ou_path,
        should_suspend_now=should_suspend,
        reason=reason,
    )


def staff_should_suspend_immediately(staff: "TeacherStaffModel") -> bool:
    """Staff deactivation is immediate (OU + Google suspended), never hard-deleted by sync."""
    employment = (getattr(staff, "employment_status", None) or "").strip().lower()
    return (
        bool(getattr(staff, "is_deleted", False))
        or not bool(getattr(staff, "is_active", True))
        or bool(getattr(staff, "marked_for_removal", False))
        or employment == "inactive"
    )


def staff_google_account_eligible(staff: "TeacherStaffModel") -> bool:
    """Only active employed staff with portal login should receive new Workspace accounts."""
    if staff_should_suspend_immediately(staff):
        return False
    return bool(getattr(staff, "portal_login", True))


def sync_student_google_suspension(
    user_email: str,
    *,
    decision: StudentOuDecision,
    is_active: bool,
    marked_for_removal: bool,
    is_deleted: bool,
) -> Optional[bool]:
    """
    Align Google suspension with student lifecycle policy.

    Active students stay unsuspended. Alumni departures get a 1-year grace period.
    Transferred & Removed departures suspend immediately.
    """
    from services.google_directory_service import (
        set_user_suspended,
        suspend_user,
        sync_user_suspension_with_db_is_active,
    )

    if not _is_departing(is_active=is_active, marked_for_removal=marked_for_removal, is_deleted=is_deleted):
        return sync_user_suspension_with_db_is_active(user_email, True)

    if decision.should_suspend_now:
        return suspend_user(user_email)
    if decision.reason == "alumni_completed_level":
        return set_user_suspended(user_email, False)
    return suspend_user(user_email)


def sync_staff_google_suspension(user_email: str, staff: "TeacherStaffModel") -> Optional[bool]:
    """Staff marked for removal / inactive / deleted → suspend immediately in Google."""
    from services.google_directory_service import suspend_user, sync_user_suspension_with_db_is_active

    if staff_should_suspend_immediately(staff):
        return suspend_user(user_email)
    return sync_user_suspension_with_db_is_active(user_email, True)


# --- Staff OU hierarchy under /Staff ---
STAFF_OU_BASE = "/Staff"
STAFF_OU_TERMINATED_REMOVED = "Terminated & Removed"
STAFF_OU_ADMINISTRATOR = "Administrator"
STAFF_OU_DIRECTOR_BOARD = "Director & Board"
STAFF_OU_FACULTY = "Faculty"
STAFF_OU_SUBSTITUTES = "Substitutes"
STAFF_OU_TEACHERS = "Teachers"

_STAFF_OU_RANK = {
    STAFF_OU_FACULTY: 10,
    STAFF_OU_TEACHERS: 40,
    STAFF_OU_SUBSTITUTES: 45,
    STAFF_OU_ADMINISTRATOR: 80,
    STAFF_OU_DIRECTOR_BOARD: 90,
}


def _staff_field_lower(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _staff_role_labels_for_ou(staff: "TeacherStaffModel", user: Optional["UserModel"]) -> set[str]:
    """Canonical labels from login (primary + secondary) plus comma-split ``assigned_role``."""
    from utils.user_roles import all_role_strings, canonical_role_label

    labels: set[str] = set()
    if user:
        labels.update(all_role_strings(user))
    ar = getattr(staff, "assigned_role", None) or ""
    for part in [p.strip() for p in str(ar).split(",") if p.strip()]:
        c = canonical_role_label(part)
        if c:
            labels.add(c)
    return labels


def _canonical_label_to_staff_ou_sub(label: str) -> Optional[str]:
    """
    Map one canonical role label to a ``/Staff/<Subfolder>`` name, or None if it does not imply a tier.
    """
    if not label or label == "Student":
        return None
    sl = label.strip().lower()
    if sl == "director":
        return STAFF_OU_DIRECTOR_BOARD
    if sl in ("school administrator", "tech", "it support"):
        return STAFF_OU_ADMINISTRATOR
    if "substitute" in sl:
        return STAFF_OU_SUBSTITUTES
    if "teacher" in sl or sl.endswith(" teacher"):
        return STAFF_OU_TEACHERS
    if sl in ("counselor", "school counselor", "other staff"):
        return STAFF_OU_FACULTY
    return None


def _position_department_staff_ou_subs(position: str, department: str) -> list[str]:
    """Legacy substring rules; each match adds a candidate tier."""
    subs: list[str] = []
    if "administrator" in position:
        subs.append(STAFF_OU_ADMINISTRATOR)
    if "director" in position or "director" in department or "board" in position or "board" in department:
        subs.append(STAFF_OU_DIRECTOR_BOARD)
    if "substitute" in position:
        subs.append(STAFF_OU_SUBSTITUTES)
    if "teacher" in position:
        subs.append(STAFF_OU_TEACHERS)
    return subs


def get_staff_ou_path(
    staff: "TeacherStaffModel",
    user: Optional["UserModel"] = None,
) -> str:
    """
    Final staff OU under ``/Staff``.

    1. **Terminated & Removed** — ``is_deleted``, ``not is_active``, or ``marked_for_removal`` (always wins).
    2. Role-based tiers: Director & Board > Administrator > Substitutes > Teachers > Faculty.
    """
    if staff_should_suspend_immediately(staff):
        return _sanitize_ou_path(f"{STAFF_OU_BASE}/{STAFF_OU_TERMINATED_REMOVED}")

    position = _staff_field_lower(getattr(staff, "position", None))
    department = _staff_field_lower(getattr(staff, "department", None))

    candidates: list[str] = []
    for label in _staff_role_labels_for_ou(staff, user):
        sub = _canonical_label_to_staff_ou_sub(label)
        if sub:
            candidates.append(sub)
    candidates.extend(_position_department_staff_ou_subs(position, department))

    if not candidates:
        sub = STAFF_OU_FACULTY
    else:
        sub = max(candidates, key=lambda s: _STAFF_OU_RANK.get(s, 0))

    return _sanitize_ou_path(f"{STAFF_OU_BASE}/{sub}")
