"""Helpers for Tech IT dashboard user management lists."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from models import User as UserModel

# Primary roles that may use the portal without a TeacherStaff directory row.
_PORTAL_OK_WITHOUT_TEACHER_STAFF = frozenset(
    {
        "Director",
        "School Administrator",
        "Tech",
        "IT Support",
    }
)


def user_is_student_bucket(user: "UserModel") -> bool:
    """True when primary role is Student (student lists vs staff lists)."""
    from utils.user_roles import canonical_role_label

    return canonical_role_label(getattr(user, "role", None)) == "Student"


def user_portal_status_label(user: "UserModel") -> str:
    """
    Display status for Tech User Management: Active, Disabled, or No account.

    - **Student**: needs linked student row; inactive/deleted/marked_for_removal → Disabled.
    - **Teacher**: needs linked TeacherStaff; same flags → Disabled.
    - **Other roles** (Director, admin, Tech, etc.): Active if no staff row or staff row is
      active; Disabled when a linked staff row exists but is inactive/removed.
    """
    from utils.user_roles import canonical_role_label

    r = canonical_role_label(getattr(user, "role", None))
    sp = getattr(user, "student_profile", None)
    tsp = getattr(user, "teacher_staff_profile", None)
    sid = getattr(user, "student_id", None)
    tid = getattr(user, "teacher_staff_id", None)

    if r == "Student":
        if not sid or not sp:
            return "No account"
        if (
            getattr(sp, "is_deleted", False)
            or not getattr(sp, "is_active", True)
            or getattr(sp, "marked_for_removal", False)
        ):
            return "Disabled"
        return "Active"

    if r not in _PORTAL_OK_WITHOUT_TEACHER_STAFF:
        if not tid or not tsp:
            return "No account"
        if (
            getattr(tsp, "is_deleted", False)
            or not getattr(tsp, "is_active", True)
            or getattr(tsp, "marked_for_removal", False)
        ):
            return "Disabled"
        return "Active"

    if tsp:
        if (
            getattr(tsp, "is_deleted", False)
            or not getattr(tsp, "is_active", True)
            or getattr(tsp, "marked_for_removal", False)
        ):
            return "Disabled"
    return "Active"


def user_lifecycle_bucket(user: "UserModel") -> str:
    """'current' or 'former' based on linked Student or TeacherStaff row."""
    from utils.user_roles import canonical_role_label

    if canonical_role_label(getattr(user, "role", None)) == "Student":
        sp = getattr(user, "student_profile", None)
        if not sp:
            return "current"
        if (
            getattr(sp, "is_deleted", False)
            or not getattr(sp, "is_active", True)
            or getattr(sp, "marked_for_removal", False)
        ):
            return "former"
        return "current"

    tsp = getattr(user, "teacher_staff_profile", None)
    if not tsp:
        return "current"
    if (
        getattr(tsp, "is_deleted", False)
        or not getattr(tsp, "is_active", True)
        or getattr(tsp, "marked_for_removal", False)
    ):
        return "former"
    return "current"


def partition_users_for_tech_management(users: List["UserModel"]) -> Dict[str, List["UserModel"]]:
    """Split into student/staff × current/former for separate tables."""
    out: Dict[str, List["UserModel"]] = {
        "students_current": [],
        "students_former": [],
        "staff_current": [],
        "staff_former": [],
    }
    for u in users:
        is_st = user_is_student_bucket(u)
        life = user_lifecycle_bucket(u)
        key = ("students" if is_st else "staff") + "_" + life
        out[key].append(u)
    for k in out:
        out[k].sort(key=lambda x: (x.username or "").lower())
    return out
