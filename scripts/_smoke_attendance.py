#!/usr/bin/env python3
"""Smoke checks for Attendance management SPA."""
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

    r = s.get(f"{BASE}/api/spa/attendance/hub", timeout=15)
    ok("GET /api/spa/attendance/hub", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    ok("hub has school_day_students array", isinstance(data.get("school_day_students"), list))
    ok("hub has classes array", isinstance(data.get("classes"), list))
    ok("hub has insights", isinstance(data.get("insights"), dict))
    ok("hub has urls.analytics", isinstance(data.get("urls", {}).get("analytics"), str))
    ok("hub has meta.has_active_school_year", "meta" in data and "has_active_school_year" in data["meta"])
    ok("hub has urls.reports", isinstance(data.get("urls", {}).get("reports"), str))

    r = s.get(f"{BASE}/api/spa/attendance/reports", timeout=15)
    ok("GET /api/spa/attendance/reports", r.status_code == 200, f"status={r.status_code}")
    reports = r.json()
    ok("reports has records array", isinstance(reports.get("records"), list))
    ok("reports has summary_stats", isinstance(reports.get("summary_stats"), dict))

    r = s.get(f"{BASE}/api/spa/attendance/analytics", timeout=15)
    ok("GET /api/spa/attendance/analytics", r.status_code == 200, f"status={r.status_code}")
    analytics = r.json()
    ok("analytics has at_risk_students array", isinstance(analytics.get("at_risk_students"), list))
    ok("analytics has daily_trend array", isinstance(analytics.get("daily_trend"), list))

    r = s.get(f"{BASE}/management/attendance-analytics", allow_redirects=False, timeout=15)
    ok("legacy analytics redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA analytics", "/app/management/attendance/analytics" in loc, loc)

    r = s.get(f"{BASE}/management/attendance/reports", allow_redirects=False, timeout=15)
    ok("legacy reports redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA reports", "/app/management/attendance/reports" in loc, loc)

    r = s.get(f"{BASE}/management/unified-attendance", allow_redirects=False, timeout=15)
    ok("legacy unified-attendance redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA attendance", "/app/management/attendance" in loc, loc)

    print("All attendance SPA smoke checks passed.")


if __name__ == "__main__":
    main()
