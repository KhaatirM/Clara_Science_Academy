#!/usr/bin/env python3
"""Smoke checks for Phase 4 Classes management SPA."""
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


def main() -> None:
    s = requests.Session()
    login(s)

    r = s.get(f"{BASE}/api/spa/classes", timeout=15)
    ok("GET /api/spa/classes", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    ok("classes has items array", isinstance(data.get("items"), list))
    ok("classes has school_years", isinstance(data.get("school_years"), list))
    ok("classes has meta.has_active_school_year", "meta" in data and "has_active_school_year" in data["meta"])
    ok("classes has meta.default_school_year_id", "meta" in data and "default_school_year_id" in data["meta"])

    r = s.get(f"{BASE}/management/classes", allow_redirects=False, timeout=15)
    ok("legacy classes redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA classes", "/app/management/classes" in loc, loc)

    r = s.get(f"{BASE}/management/classes/core-class-setup", allow_redirects=False, timeout=15)
    ok("legacy core setup redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA core-setup", "/app/management/classes/core-setup" in loc, loc)

    if data["items"]:
        cid = data["items"][0]["id"]
        r = s.get(f"{BASE}/api/spa/classes/{cid}", timeout=15)
        ok("GET /api/spa/classes/:id", r.status_code == 200, f"status={r.status_code}")

    print("\nPhase 4 Classes smoke tests passed.")


if __name__ == "__main__":
    main()
