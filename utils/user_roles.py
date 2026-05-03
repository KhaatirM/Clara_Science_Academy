"""Role bundles for users with primary ``User.role`` plus optional ``secondary_roles`` JSON list."""

from __future__ import annotations

import json
from typing import Any, List, Set

_TECH_PICK_ROLES = frozenset({"Tech", "IT Support"})  # tech split vs management (not Director alone)
_MGMT_PICK_ROLES = frozenset({"School Administrator", "Director"})
_TECH_ROUTE_ROLES = frozenset({"Tech", "IT Support", "Director"})  # who may open /tech/* routes
_MGMT_ROLES = frozenset({"School Administrator", "Director"})


def _parse_secondary_roles(raw: Any) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(x).strip() for x in raw if x and str(x).strip()]
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if isinstance(data, list):
            return [str(x).strip() for x in data if x and str(x).strip()]
    return []


def all_role_strings(user) -> Set[str]:
    """Primary role plus any ``secondary_roles`` JSON entries."""
    if not user:
        return set()
    roles: Set[str] = set()
    pr = getattr(user, "role", None)
    if pr:
        roles.add(str(pr).strip())
    for s in _parse_secondary_roles(getattr(user, "secondary_roles", None)):
        roles.add(s)
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
    if not user or getattr(user, "role", None) == "Student":
        return False
    r = all_role_strings(user)
    return bool(r & _TECH_PICK_ROLES) and bool(r & _MGMT_PICK_ROLES)
