"""Helpers for Tech IT dashboard user management lists and permission checks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from models import User as UserModel


def user_may_hard_delete_site_accounts(actor: Any) -> bool:
    """Only Tech or IT Support may permanently delete non-student login rows."""
    from utils.user_roles import all_role_strings

    return bool(all_role_strings(actor) & {"Tech", "IT Support"})


def user_is_student_bucket(user: "UserModel") -> bool:
    """True when primary role is Student (student lists vs staff lists)."""
    from utils.user_roles import canonical_role_label

    return canonical_role_label(getattr(user, "role", None)) == "Student"


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
