#!/usr/bin/env python3
"""Smoke checks for Phase 2 Students SPA."""
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:5000"


def login(session: requests.Session) -> None:
    r = session.get(f"{BASE}/login", timeout=15)
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    if not m:
        print("FAIL: no csrf on login page", file=sys.stderr)
        sys.exit(1)
    session.post(
        f"{BASE}/login",
        data={"username": "vmuhammad", "password": "ClaraDev2026!", "csrf_token": m.group(1)},
        allow_redirects=True,
        timeout=15,
    )


def ok(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"{status}: {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        sys.exit(1)


def test_permission_logic() -> None:
    """Unit checks mirroring can_admin_ui without needing a view-only login."""
    from management_routes.students import _can_student_admin_ui

    class FakeUser:
        def __init__(self, role: str, permissions: str | None = None):
            self.role = role
            self.permissions = permissions
            self.secondary_roles = None

    ok("view-only staff not admin UI", not _can_student_admin_ui(FakeUser("School Counselor", '["students:view"]')))
    ok("edit permission grants admin UI", _can_student_admin_ui(FakeUser("School Counselor", '["students:view","students:edit"]')))
    ok("director has admin UI", _can_student_admin_ui(FakeUser("Director")))


def main() -> None:
    test_permission_logic()

    s = requests.Session()
    login(s)

    r = s.get(f"{BASE}/api/spa/students", timeout=15)
    ok("GET /api/spa/students", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    ok("students list has items array", isinstance(data.get("items"), list))
    ok("students stats has high_gpa", "high_gpa" in data.get("stats", {}))
    ok("director can_admin_ui", data.get("meta", {}).get("can_admin_ui") is True)

    r = s.get(f"{BASE}/management/students", allow_redirects=False, timeout=15)
    ok("legacy students redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA", "/app/management/students" in loc, loc)

    items = data.get("items") or []
    if items:
        sid = items[0]["id"]
        r = s.get(f"{BASE}/api/spa/students/{sid}", timeout=15)
        ok("GET /api/spa/students/:id", r.status_code == 200, f"status={r.status_code}")
        detail = r.json()
        ok("detail has parent_portal", "parent_portal" in detail)
        ok("detail has notes field", "notes" in detail and "medical_concerns" in detail)
        ok("detail has middle_name", "middle_name" in detail)
        ok("detail has classes school year", "assigned_classes_school_year" in detail)
        print("sample detail keys:", ", ".join(sorted(detail.keys())[:10]), "...")
    else:
        print("SKIP: no students to test detail endpoint")

    r = s.get(f"{BASE}/management/add-student", allow_redirects=False, timeout=15)
    ok("add-student redirect", r.status_code in (301, 302, 303, 307, 308))
    ok("add-student SPA path", "/app/management/students/new" in r.headers.get("Location", ""))

    r = s.get(f"{BASE}/api/spa/me", timeout=15)
    ok("GET /api/spa/me", r.status_code == 200)
    me = r.json().get("user") or {}
    ok("session has permissions array", isinstance(me.get("permissions"), list))

    print("\nPhase 2 students smoke tests passed.")


if __name__ == "__main__":
    main()
