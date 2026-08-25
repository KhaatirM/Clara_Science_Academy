"""Helpers for Tech IT dashboard user management lists."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from models import Student as StudentModel
    from models import TeacherStaff as TeacherStaffModel
    from models import User as UserModel

# Primary roles that may use the portal without a TeacherStaff directory row.
_PORTAL_OK_WITHOUT_TEACHER_STAFF = frozenset(
    {
        "Director",
        "School Administrator",
        "Tech",
        "IT Support",
        "Parent",
    }
)


def user_is_student_bucket(user: "UserModel") -> bool:
    """True when primary role is Student (student lists vs staff lists)."""
    from utils.user_roles import canonical_role_label

    return canonical_role_label(getattr(user, "role", None)) == "Student"


def user_is_parent_bucket(user: "UserModel") -> bool:
    """True when primary role is Parent (separate from staff)."""
    from utils.user_roles import canonical_role_label

    return canonical_role_label(getattr(user, "role", None)) == "Parent"


def student_profile_is_former(student: Optional["StudentModel"]) -> bool:
    if student is None:
        return False
    from utils.student_roster import student_is_archived

    return student_is_archived(student)


def staff_profile_is_former(staff: Optional["TeacherStaffModel"]) -> bool:
    if staff is None:
        return False
    if getattr(staff, "is_deleted", False):
        return True
    if getattr(staff, "marked_for_removal", False):
        return True
    if getattr(staff, "is_active", True) is False:
        return True
    status = (getattr(staff, "employment_status", None) or "").strip().lower()
    if status in ("inactive", "terminated", "former", "removed"):
        return True
    return False


def user_portal_status_label(user: "UserModel") -> str:
    """
    Display status for Tech User Management: Active, Disabled, or No account.

    - **Student**: needs linked student row; inactive/deleted/marked_for_removal → Disabled.
    - **Parent**: portal login is enough (no TeacherStaff row).
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
        if student_profile_is_former(sp):
            return "Disabled"
        return "Active"

    if r == "Parent":
        return "Active"

    if r not in _PORTAL_OK_WITHOUT_TEACHER_STAFF:
        if not tid or not tsp:
            return "No account"
        if staff_profile_is_former(tsp):
            return "Disabled"
        return "Active"

    if tsp and staff_profile_is_former(tsp):
        return "Disabled"
    return "Active"


def user_lifecycle_bucket(user: "UserModel") -> str:
    """'current' or 'former' based on linked Student or TeacherStaff row."""
    from utils.user_roles import canonical_role_label

    role = canonical_role_label(getattr(user, "role", None))
    if role == "Parent":
        return "current"

    if role == "Student":
        sp = getattr(user, "student_profile", None)
        if not sp:
            return "current"
        return "former" if student_profile_is_former(sp) else "current"

    tsp = getattr(user, "teacher_staff_profile", None)
    if not tsp:
        return "current"
    return "former" if staff_profile_is_former(tsp) else "current"


def partition_users_for_tech_management(users: List["UserModel"]) -> Dict[str, List["UserModel"]]:
    """Split into student/staff/parent × current/former for separate tables."""
    out: Dict[str, List["UserModel"]] = {
        "students_current": [],
        "students_former": [],
        "parents": [],
        "staff_current": [],
        "staff_former": [],
    }
    for u in users:
        if user_is_parent_bucket(u):
            out["parents"].append(u)
            continue
        is_st = user_is_student_bucket(u)
        life = user_lifecycle_bucket(u)
        key = ("students" if is_st else "staff") + "_" + life
        out[key].append(u)
    for k in out:
        out[k].sort(key=lambda x: (x.username or "").lower())
    return out


def serialize_tech_mgmt_user_row(user: "UserModel") -> Dict[str, Any]:
    """Serialize a portal User for Tech User Management tables."""
    login_id = None
    if user.student_profile and user.student_profile.student_id:
        login_id = user.student_profile.student_id
    elif user.teacher_staff_profile and getattr(user.teacher_staff_profile, "staff_id", None):
        login_id = user.teacher_staff_profile.staff_id
    return {
        "id": user.id,
        "row_key": f"user-{user.id}",
        "username": user.username,
        "role": user.role,
        "login_id": login_id,
        "portal_status": user_portal_status_label(user),
        "email": getattr(user, "email", None),
        "can_view": True,
    }


def serialize_former_student_row(
    student: "StudentModel", user: Optional["UserModel"] = None
) -> Dict[str, Any]:
    if user is not None:
        return serialize_tech_mgmt_user_row(user)
    name = f"{student.first_name or ''} {student.last_name or ''}".strip()
    return {
        "id": None,
        "row_key": f"student-{student.id}",
        "username": name or f"Student #{student.id}",
        "role": "Student",
        "login_id": student.student_id,
        "portal_status": "No account",
        "email": getattr(student, "email", None),
        "can_view": False,
    }


def serialize_former_staff_row(
    staff: "TeacherStaffModel", user: Optional["UserModel"] = None
) -> Dict[str, Any]:
    if user is not None:
        return serialize_tech_mgmt_user_row(user)
    name = f"{staff.first_name or ''} {staff.last_name or ''}".strip()
    role = (
        getattr(staff, "assigned_role", None)
        or getattr(staff, "position", None)
        or "Staff"
    )
    return {
        "id": None,
        "row_key": f"staff-{staff.id}",
        "username": name or f"Staff #{staff.id}",
        "role": role,
        "login_id": getattr(staff, "staff_id", None),
        "portal_status": "No account",
        "email": getattr(staff, "email", None)
        or getattr(staff, "google_workspace_email", None),
        "can_view": False,
    }


def build_tech_user_management_lists() -> Dict[str, List[Dict[str, Any]]]:
    """
    Build Tech User Management buckets.

    Former student/staff lists include directory profiles even when the portal
    User was deleted on offboarding (so those sections are not empty).
    Parents are a separate category from staff.
    """
    from models import Student, TeacherStaff, User
    from sqlalchemy.orm import joinedload

    users = (
        User.query.options(
            joinedload(User.student_profile),
            joinedload(User.teacher_staff_profile),
        )
        .order_by(User.username.asc())
        .all()
    )
    parts = partition_users_for_tech_management(users)

    parents = [serialize_tech_mgmt_user_row(u) for u in parts["parents"]]

    students_current: List[Dict[str, Any]] = []
    for u in parts["students_current"]:
        if student_profile_is_former(getattr(u, "student_profile", None)):
            continue
        students_current.append(serialize_tech_mgmt_user_row(u))

    staff_current: List[Dict[str, Any]] = []
    for u in parts["staff_current"]:
        if staff_profile_is_former(getattr(u, "teacher_staff_profile", None)):
            continue
        staff_current.append(serialize_tech_mgmt_user_row(u))

    former_student_user_by_sid: Dict[int, Any] = {}
    for u in parts["students_former"] + parts["students_current"]:
        sid = getattr(u, "student_id", None)
        if sid and student_profile_is_former(getattr(u, "student_profile", None)):
            former_student_user_by_sid.setdefault(sid, u)

    students_former: List[Dict[str, Any]] = []
    seen_student_ids: set[int] = set()
    for s in Student.query.order_by(Student.last_name.asc(), Student.first_name.asc()).all():
        if not student_profile_is_former(s):
            continue
        seen_student_ids.add(s.id)
        students_former.append(
            serialize_former_student_row(s, former_student_user_by_sid.get(s.id))
        )
    for u in parts["students_former"]:
        sid = getattr(u, "student_id", None)
        if sid and sid in seen_student_ids:
            continue
        if sid is None:
            students_former.append(serialize_tech_mgmt_user_row(u))

    former_staff_user_by_tid: Dict[int, Any] = {}
    for u in parts["staff_former"] + parts["staff_current"]:
        tid = getattr(u, "teacher_staff_id", None)
        if tid and staff_profile_is_former(getattr(u, "teacher_staff_profile", None)):
            former_staff_user_by_tid.setdefault(tid, u)

    staff_former: List[Dict[str, Any]] = []
    seen_staff_ids: set[int] = set()
    for t in TeacherStaff.query.order_by(
        TeacherStaff.last_name.asc(), TeacherStaff.first_name.asc()
    ).all():
        if not staff_profile_is_former(t):
            continue
        seen_staff_ids.add(t.id)
        staff_former.append(serialize_former_staff_row(t, former_staff_user_by_tid.get(t.id)))
    for u in parts["staff_former"]:
        tid = getattr(u, "teacher_staff_id", None)
        if tid and tid in seen_staff_ids:
            continue
        if tid is None:
            staff_former.append(serialize_tech_mgmt_user_row(u))

    def _sort_key(row: Dict[str, Any]) -> str:
        return (row.get("username") or "").lower()

    students_current.sort(key=_sort_key)
    students_former.sort(key=_sort_key)
    parents.sort(key=_sort_key)
    staff_current.sort(key=_sort_key)
    staff_former.sort(key=_sort_key)

    return {
        "students_current": students_current,
        "students_former": students_former,
        "parents": parents,
        "staff_current": staff_current,
        "staff_former": staff_former,
    }
