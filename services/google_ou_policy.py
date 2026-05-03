from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from models import TeacherStaff as TeacherStaffModel
    from models import User as UserModel


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


# --- Staff OU hierarchy under /Staff ---
STAFF_OU_BASE = "/Staff"
STAFF_OU_TERMINATED_REMOVED = "Terminated & Removed"
STAFF_OU_ADMINISTRATOR = "Administrator"
STAFF_OU_DIRECTOR_BOARD = "Director & Board"
STAFF_OU_FACULTY = "Faculty"
STAFF_OU_SUBSTITUTES = "Substitutes"
STAFF_OU_TEACHERS = "Teachers"

# Higher number wins when a person matches multiple tiers (primary + secondary_roles + assigned_role).
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
    Substitute-style titles are checked before generic *teacher* substring matches.
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
    Final 6-tier staff OU under ``/Staff``. When multiple roles apply (primary, ``secondary_roles``,
    and comma-separated ``assigned_role``), the tier with the **highest** precedence rank wins.

    Rank order (high → low): Director & Board > Administrator > Substitutes > Teachers > Faculty.

    1. **Terminated & Removed** — ``is_deleted``, ``not is_active``, or ``marked_for_removal`` (always wins).
    2. **Administrator** — canonical Tech / IT Support / School Administrator, or ``position`` contains
       ``administrator``.
    3. **Director & Board** — canonical Director, or ``position`` / ``department`` hints for director/board.
    4. **Substitutes** — canonical substitute titles, or ``position`` contains ``substitute``.
    5. **Teachers** — canonical teacher titles, or ``position`` contains ``teacher``.
    6. **Faculty** — default when no other tier matches.

    Pass the linked ``User`` when present; use ``None`` if there is no website login.
    """
    if (
        bool(getattr(staff, "is_deleted", False))
        or not bool(getattr(staff, "is_active", True))
        or bool(getattr(staff, "marked_for_removal", False))
    ):
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
