"""Role bundles for users with primary ``User.role`` plus optional ``secondary_roles`` JSON list."""

from __future__ import annotations

import json
from typing import Any, List, Set

_TECH_PICK_ROLES = frozenset({"Tech", "IT Support"})  # tech split vs management (not Director alone)
_MGMT_PICK_ROLES = frozenset({"School Administrator", "Director"})
_TECH_ROUTE_ROLES = frozenset({"Tech", "IT Support", "Director"})  # who may open /tech/* routes
_MGMT_ROLES = frozenset({"School Administrator", "Director"})

# Production DBs sometimes store lowercase or shorthand labels (e.g. admin, teacher).
_ROLE_CANON_ALIASES = {
    "admin": "School Administrator",
    "administrator": "School Administrator",
    "school administrator": "School Administrator",
    "school_administrator": "School Administrator",
    "director": "Director",
    "teacher": "Teacher",
    "tech": "Tech",
    "it support": "IT Support",
    "it_support": "IT Support",
    "student": "Student",
    "other staff": "Other Staff",
    "other_staff": "Other Staff",
}


def canonical_role_label(role: Any) -> str:
    """Normalize role strings for comparisons (case-insensitive + common aliases)."""
    if role is None:
        return ""
    s = str(role).strip()
    if not s:
        return ""
    key = s.lower()
    return _ROLE_CANON_ALIASES.get(key, s)


def parse_secondary_roles(raw: Any) -> List[str]:
    """Parse ``secondary_roles`` JSON list; tolerate legacy single-string or comma-separated values."""
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(x).strip() for x in raw if x and str(x).strip()]
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                data = json.loads(s)
            except Exception:
                return []
            if isinstance(data, list):
                return [str(x).strip() for x in data if x and str(x).strip()]
            return []
        # Legacy: one role stored as plain text, or "Role A, Role B"
        if "," in s:
            return [p.strip() for p in s.split(",") if p.strip()]
        return [s]
    return []


def all_role_strings(user) -> Set[str]:
    """Primary role plus any ``secondary_roles`` JSON entries (canonical labels)."""
    if not user:
        return set()
    roles: Set[str] = set()
    pr = getattr(user, "role", None)
    if pr:
        roles.add(canonical_role_label(pr))
    for s in parse_secondary_roles(getattr(user, "secondary_roles", None)):
        roles.add(canonical_role_label(s))
    return {r for r in roles if r}


def user_has_tech_route_access(user) -> bool:
    """Aligns with ``tech_required``: Tech, IT Support, or Director (any source)."""
    r = all_role_strings(user)
    return bool(r & _TECH_ROUTE_ROLES)


def user_has_management_entry_access(user) -> bool:
    """School Administrator or Director in primary or secondary roles."""
    r = all_role_strings(user)
    return bool(r & _MGMT_ROLES)


def staff_must_choose_dashboard(user) -> bool:
    """
    Both a tech-style role (Tech/IT Support) and a management role (School Admin/Director) —
    user must pick which dashboard to open (e.g. after merging two accounts).
    """
    if not user or canonical_role_label(getattr(user, "role", None)) == "Student":
        return False
    r = all_role_strings(user)
    return bool(r & _TECH_PICK_ROLES) and bool(r & _MGMT_PICK_ROLES)


def pick_tech_sidebar_canonical(user) -> str:
    """Label for IT sidebar when dual-role user is in the tech area."""
    r = all_role_strings(user) & _TECH_PICK_ROLES
    if "Tech" in r:
        return "Tech"
    if "IT Support" in r:
        return "IT Support"
    return "IT Support"


def pick_management_sidebar_canonical(user) -> str:
    """Label for school management sidebar when dual-role user is in the management area."""
    r = all_role_strings(user) & _MGMT_PICK_ROLES
    if "Director" in r:
        return "Director"
    if "School Administrator" in r:
        return "School Administrator"
    return canonical_role_label(getattr(user, "role", None)) or "School Administrator"


def ordered_role_labels_for_teacher_staff(teacher_staff) -> List[str]:
    """
    Ordered unique canonical roles for directory UI: login primary, then secondary_roles,
    then any extra segments from TeacherStaff.assigned_role (legacy / merged display).
    Without a User row, uses assigned_role only or ``No Account``.
    """
    ts = teacher_staff
    if ts is None:
        return []
    u = getattr(ts, "user", None)
    if u:
        seen: Set[str] = set()
        out: List[str] = []
        pr = canonical_role_label(getattr(u, "role", None))
        if pr:
            seen.add(pr)
            out.append(pr)
        for s in parse_secondary_roles(getattr(u, "secondary_roles", None)):
            c = canonical_role_label(s)
            if c and c not in seen:
                seen.add(c)
                out.append(c)
        ar = (getattr(ts, "assigned_role", None) or "").strip()
        for part in [p.strip() for p in ar.split(",") if p.strip()]:
            c = canonical_role_label(part)
            if c and c not in seen:
                seen.add(c)
                out.append(c)
        return out
    ar = (getattr(ts, "assigned_role", None) or "").strip()
    if ar:
        seen: Set[str] = set()
        out: List[str] = []
        for part in [p.strip() for p in ar.split(",") if p.strip()]:
            c = canonical_role_label(part)
            if c and c not in seen:
                seen.add(c)
                out.append(c)
        return out if out else ["No Account"]
    return ["No Account"]


def role_badge_bootstrap_class(role_label: str) -> str:
    """Bootstrap badge classes used on staff directory Role column."""
    r = (role_label or "").strip()
    if r == "Director":
        return "bg-danger"
    if r == "School Administrator":
        return "bg-warning"
    if r in ("Tech", "IT Support"):
        return "bg-secondary"
    if "Teacher" in r or r in (
        "Substitute",
        "Counselor",
        "Substitute Teacher",
        "School Counselor",
        "Math Teacher",
        "Science Teacher",
        "History Teacher",
        "Physics Teacher",
        "English Language Arts Teacher",
    ):
        return "bg-info"
    if r == "No Account":
        return "bg-warning"
    return "bg-light text-dark"
