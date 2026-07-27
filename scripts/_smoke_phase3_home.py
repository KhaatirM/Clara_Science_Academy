#!/usr/bin/env python3
"""Smoke checks for Phase 3 Management home dashboard SPA."""
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

    r = s.get(f"{BASE}/api/spa/dashboard/home", timeout=15)
    ok("GET /api/spa/dashboard/home", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    ok("dashboard has profile", isinstance(data.get("profile"), dict))
    ok("dashboard has has_active_school_year", "has_active_school_year" in data)
    ok("dashboard has stats", isinstance(data.get("stats"), dict))
    ok("dashboard has notifications array", isinstance(data.get("notifications"), list))

    r = s.get(f"{BASE}/management/dashboard", allow_redirects=False, timeout=15)
    ok("legacy dashboard redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA home", "/app/management" in loc, loc)

    print("\nPhase 3 home dashboard smoke tests passed.")


if __name__ == "__main__":
    main()
