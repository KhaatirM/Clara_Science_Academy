#!/usr/bin/env python3
"""Smoke checks for Report Cards management SPA."""
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

    r = s.get(f"{BASE}/api/spa/report-cards/hub", timeout=15)
    ok("GET /api/spa/report-cards/hub", r.status_code == 200, f"status={r.status_code}")
    hub = r.json()
    ok("hub has categories array", isinstance(hub.get("categories"), list))
    ok("hub has recent_reports array", isinstance(hub.get("recent_reports"), list))
    ok("hub has stats", isinstance(hub.get("stats"), dict))

    r = s.get(f"{BASE}/api/spa/report-cards/pending", timeout=15)
    ok("GET /api/spa/report-cards/pending", r.status_code == 200, f"status={r.status_code}")
    pending = r.json()
    ok("pending has report_cards array", isinstance(pending.get("report_cards"), list))
    ok("pending has total", isinstance(pending.get("total"), int))

    r = s.get(f"{BASE}/api/spa/report-cards/search", timeout=15)
    ok("GET /api/spa/report-cards/search", r.status_code == 200, f"status={r.status_code}")
    search = r.json()
    ok("search has report_cards array", isinstance(search.get("report_cards"), list))
    ok("search has pagination", isinstance(search.get("pagination"), dict))
    ok("search has filters", isinstance(search.get("filters"), dict))

    r = s.get(f"{BASE}/api/spa/report-cards/categories/elementary", timeout=15)
    ok("GET /api/spa/report-cards/categories/elementary", r.status_code == 200, f"status={r.status_code}")
    category = r.json()
    ok("category has students array", isinstance(category.get("students"), list))
    ok("category has category slug", category.get("category", {}).get("slug") == "elementary")

    r = s.get(f"{BASE}/management/report-cards", allow_redirects=False, timeout=15)
    ok("legacy report-cards redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA report-cards", "/app/management/report-cards" in loc, loc)

    r = s.get(f"{BASE}/management/report-cards/category/6-8", allow_redirects=False, timeout=15)
    ok("legacy category redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA category", "/app/management/report-cards/category/6-8" in loc, loc)

    r = s.get(f"{BASE}/api/spa/report-cards/generate-form", timeout=15)
    ok("GET /api/spa/report-cards/generate-form", r.status_code == 200, f"status={r.status_code}")
    form = r.json()
    ok("generate-form has students", isinstance(form.get("students"), list))

    r = s.get(f"{BASE}/management/report/card/generate", allow_redirects=False, timeout=15)
    ok("legacy generate redirect", r.status_code in (301, 302, 303, 307, 308))
    loc = r.headers.get("Location", "")
    ok("redirect targets SPA generate", "/app/management/report-cards/generate" in loc, loc)

    if hub.get("recent_reports"):
        rc_id = hub["recent_reports"][0]["id"]
        r = s.get(f"{BASE}/api/spa/report-cards/{rc_id}", timeout=15)
        ok("GET /api/spa/report-cards/:id detail", r.status_code == 200, f"status={r.status_code}")
        detail = r.json()
        ok("detail has report_card", isinstance(detail.get("report_card"), dict))

        r = s.get(f"{BASE}/management/report/card/view/{rc_id}", allow_redirects=False, timeout=15)
        ok("legacy view redirect", r.status_code in (301, 302, 303, 307, 308))
        loc = r.headers.get("Location", "")
        ok("redirect targets SPA detail", f"/app/management/report-cards/{rc_id}" in loc, loc)

        student_id = hub["recent_reports"][0].get("student", {}).get("id")
        if student_id:
            r = s.get(f"{BASE}/api/spa/report-cards/students/{student_id}/history", timeout=15)
            ok("GET student history", r.status_code == 200, f"status={r.status_code}")
            history = r.json()
            ok("history has student", isinstance(history.get("student"), dict))
            ok("history has school_years", isinstance(history.get("school_years"), list))

            r = s.get(f"{BASE}/api/spa/report-cards/students/{student_id}/school-years", timeout=15)
            ok("GET student school-years", r.status_code == 200, f"status={r.status_code}")
            school_years = r.json()
            ok("school-years payload has years", isinstance(school_years.get("school_years"), list))

            r = s.get(
                f"{BASE}/management/report-cards/student/{student_id}",
                allow_redirects=False,
                timeout=15,
            )
            ok("legacy history redirect", r.status_code in (301, 302, 303, 307, 308))
            loc = r.headers.get("Location", "")
            ok(
                "redirect targets SPA history",
                f"/app/management/report-cards/student/{student_id}" in loc,
                loc,
            )

        r = s.get(f"{BASE}/api/spa/report-cards/{rc_id}/pdf", timeout=30)
        ok("GET PDF endpoint", r.status_code == 200, f"status={r.status_code}")
        ok("PDF content-type", "pdf" in (r.headers.get("Content-Type") or "").lower())

    print("All report cards SPA smoke checks passed.")


if __name__ == "__main__":
    main()
