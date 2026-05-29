#!/usr/bin/env python3
"""
End-to-end browser tests for school-year closure, filters, and role dashboards.

Prerequisites:
  pip install -r tests/e2e/requirements-e2e.txt
  playwright install chromium
  python app.py   # running on E2E_BASE_URL (default http://127.0.0.1:5000)

Run (from repo root):
  python tests/e2e/run_closure_e2e.py

Environment:
  E2E_BASE_URL, E2E_PASSWORD, E2E_DIRECTOR_USER, E2E_TEACHER_USER, E2E_STUDENT_USER
"""
from __future__ import annotations

import re
import sys
import traceback
from datetime import date

from playwright.sync_api import sync_playwright, expect

from helpers import (
    BASE_URL,
    USERS,
    dismiss_toasts,
    login,
    logout,
    post_with_csrf,
    prepare_database,
    set_hidden_select,
)


class Result:
    def __init__(self, name: str, ok: bool, detail: str = ""):
        self.name = name
        self.ok = ok
        self.detail = detail


def run_test(name: str, fn, results: list[Result]):
    try:
        fn()
        results.append(Result(name, True))
        print(f"  PASS  {name}")
    except Exception as exc:
        results.append(Result(name, False, str(exc)))
        print(f"  FAIL  {name}: {exc}")


def get_student_assignment_id():
    from app import create_app
    from models import Assignment, Enrollment, SchoolYear, Student, User

    app = create_app()
    with app.app_context():
        student = Student.query.join(User).filter(User.username == USERS["student"]).first()
        sy = SchoolYear.query.filter_by(is_active=True).first()
        if not student or not sy:
            return None
        class_ids = [
            e.class_id
            for e in Enrollment.query.filter_by(
                student_id=student.id, is_active=True
            ).all()
        ]
        if not class_ids:
            return None
        a = (
            Assignment.query.filter(
                Assignment.class_id.in_(class_ids),
                Assignment.school_year_id == sy.id,
                Assignment.status == "Active",
            )
            .order_by(Assignment.id.asc())
            .first()
        )
        return a.id if a else None


def wait_for_year_option(page, select_id: str, year_id: int, timeout: int = 15_000):
    page.wait_for_function(
        """([sid, yid]) => {
            const el = document.getElementById(sid);
            return el && Array.from(el.options).some(o => o.value === String(yid));
        }""",
        arg=[select_id, year_id],
        timeout=timeout,
    )


def clear_year_filters(page):
    """Reset management class / assignment year filters to 'none selected'."""
    for btn_id in ("resetFilters", "resetAsgClassFilters"):
        if page.locator(f"#{btn_id}").count():
            page.locator(f"#{btn_id}").click()
            page.wait_for_timeout(400)
            return
    for sid in ("schoolYearFilter", "asgSchoolYearFilter"):
        if page.locator(f"#{sid}").count():
            set_hidden_select(page, sid, "")


def main() -> int:
    print("=== Clara Science — Closure E2E ===\n")
    print(f"Base URL: {BASE_URL}")
    print("Preparing database (active year, passwords, cancel stale closures)...")
    meta = prepare_database()
    print(f"  School year: {meta['school_year_name']} (id={meta['school_year_id']})\n")

    assignment_id = get_student_assignment_id()
    if not assignment_id:
        print("WARNING: No active assignment for test student — submit tests may skip.\n")

    results: list[Result] = []
    year_id = meta["school_year_id"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        closure_id = None

        def test_director_calendar_closure_button():
            login(page, USERS["director"])
            page.goto(f"{BASE_URL}/management/calendar", wait_until="networkidle")
            expect(page.get_by_role("link", name="End-of-year closure")).to_be_visible()

        def test_report_cards_no_closure_button():
            page.goto(f"{BASE_URL}/management/report-cards", wait_until="networkidle")
            expect(page.get_by_role("link", name=re.compile(r"Schedule year closure", re.I))).to_have_count(0)

        def test_classes_require_school_year():
            page.goto(f"{BASE_URL}/management/classes", wait_until="networkidle")
            expect(page.locator("#classesGrid")).to_be_visible(timeout=15_000)
            clear_year_filters(page)
            expect(page.locator("#classesShownCount")).to_contain_text("select a school year")
            expect(page.locator(".class-card:visible")).to_have_count(0)

        def test_classes_show_after_year_select():
            wait_for_year_option(page, "schoolYearFilter", year_id)
            set_hidden_select(page, "schoolYearFilter", str(year_id))
            expect(page.locator(".class-card:visible").first).to_be_visible(timeout=10_000)
            expect(page.locator("#classesShownCount")).to_contain_text("shown")

        def test_assignments_filters():
            page.goto(f"{BASE_URL}/management/assignments-and-grades", wait_until="networkidle")
            expect(page.locator("#asgSchoolYearFilter")).to_be_attached()
            clear_year_filters(page)
            expect(page.locator("#classSelectionGrid")).to_be_hidden()
            wait_for_year_option(page, "asgSchoolYearFilter", year_id)
            set_hidden_select(page, "asgSchoolYearFilter", str(year_id))
            expect(page.locator("#classSelectionGrid")).not_to_have_class("d-none")
            expect(page.locator(".class-search-item:visible").first).to_be_visible(timeout=10_000)

        def test_schedule_closure():
            nonlocal closure_id
            dismiss_toasts(page)
            page.goto(f"{BASE_URL}/management/school-year/closure/schedule", wait_until="networkidle")
            dismiss_toasts(page)
            page.select_option("#school_year_id", value=str(year_id))
            page.fill("#closure_date", date.today().isoformat())
            page.fill("#confirm", "SCHEDULE CLOSURE")
            page.get_by_role("button", name=re.compile(r"Schedule closure", re.I)).click(force=True)
            page.wait_for_load_state("networkidle")
            expect(page.locator(".mgmt-syc-phase-badge")).to_be_visible()
            assert "/school-year/closure/" in page.url
            closure_id = int(page.url.rstrip("/").split("/")[-1])

        run_test("Director: Calendar has End-of-year closure", test_director_calendar_closure_button, results)
        run_test("Director: Report cards has no closure button", test_report_cards_no_closure_button, results)
        run_test("Director: Classes hidden until school year", test_classes_require_school_year, results)
        run_test("Director: Classes visible after year filter", test_classes_show_after_year_select, results)
        run_test("Director: Assignments & Grades year filter", test_assignments_filters, results)
        run_test("Director: Schedule closure", test_schedule_closure, results)

        if not closure_id:
            closure_id = _closure_id_from_db()

        if closure_id:

            def test_student_assignments_student_window():
                logout(page)
                login(page, USERS["student"])
                page.goto(f"{BASE_URL}/student/assignments", wait_until="networkidle")
                expect(page.locator("body")).to_contain_text("Assignment", timeout=15_000)

            run_test("Student window: student can open assignments", test_student_assignments_student_window, results)

            def test_advance_teacher_window():
                logout(page)
                login(page, USERS["director"])
                dismiss_toasts(page)
                page.goto(f"{BASE_URL}/management/school-year/closure/{closure_id}", wait_until="networkidle")
                dismiss_toasts(page)
                page.get_by_role("button", name=re.compile(r"Advance phase", re.I)).click()
                page.wait_for_selector("#mgmtSycAdvanceModal.show, #mgmtSycAdvanceModal[style*='display: block']", timeout=5_000)
                page.select_option("#target_phase", value="teacher_window")
                page.locator("#mgmtSycAdvanceModal button.btn-primary[type=submit]").click()
                page.wait_for_load_state("networkidle")
                expect(page.locator(".mgmt-syc-phase-badge")).to_contain_text("Teacher window")

            run_test("Advance phase: teacher window", test_advance_teacher_window, results)

            def test_student_submit_blocked_teacher_window():
                if not assignment_id:
                    raise RuntimeError("No assignment id for student submit test")
                logout(page)
                login(page, USERS["student"])
                page.goto(f"{BASE_URL}/student/assignments", wait_until="domcontentloaded")
                resp = post_with_csrf(
                    page,
                    f"{BASE_URL}/student/submit/{assignment_id}",
                    form={"notes": "e2e"},
                )
                assert resp.blocked_by_closure, (
                    f"Expected closure lockout, got HTTP {resp.status}: {resp.text[:120]!r}"
                )

            run_test("Teacher window: student submit blocked", test_student_submit_blocked_teacher_window, results)

            def test_teacher_can_open_assignments():
                logout(page)
                login(page, USERS["teacher"])
                page.goto(f"{BASE_URL}/teacher/assignments-and-grades", wait_until="networkidle")
                expect(page.locator("body")).not_to_contain_text("403")
                expect(
                    page.locator("h1, h2, .mgmt-asg-title, .class-search-item, .assignments-empty-state").first
                ).to_be_visible(timeout=15_000)

            run_test("Teacher window: teacher assignments page loads", test_teacher_can_open_assignments, results)

            def test_advance_admin_window():
                logout(page)
                login(page, USERS["director"])
                dismiss_toasts(page)
                page.goto(f"{BASE_URL}/management/school-year/closure/{closure_id}", wait_until="networkidle")
                dismiss_toasts(page)
                page.get_by_role("button", name=re.compile(r"Advance phase", re.I)).click()
                page.wait_for_selector("#mgmtSycAdvanceModal.show, #mgmtSycAdvanceModal[style*='display: block']", timeout=5_000)
                page.select_option("#target_phase", value="admin_window")
                page.locator("#mgmtSycAdvanceModal button.btn-primary[type=submit]").click()
                page.wait_for_load_state("networkidle")
                expect(page.locator(".mgmt-syc-phase-badge")).to_contain_text("Admin window")

            run_test("Advance phase: admin window", test_advance_admin_window, results)

            def test_teacher_grade_blocked_admin_window():
                grade_assignment_id = assignment_id or 1
                logout(page)
                login(page, USERS["teacher"])
                page.goto(
                    f"{BASE_URL}/teacher/assignments-and-grades",
                    wait_until="domcontentloaded",
                )
                resp = post_with_csrf(
                    page,
                    f"{BASE_URL}/teacher/grade/assignment/{grade_assignment_id}",
                    form={},
                )
                assert resp.blocked_by_closure, (
                    f"Expected closure lockout, got HTTP {resp.status}: {resp.text[:120]!r}"
                )

            run_test("Admin window: teacher grade POST blocked", test_teacher_grade_blocked_admin_window, results)

            def test_cancel_closure():
                logout(page)
                login(page, USERS["director"])
                dismiss_toasts(page)
                page.goto(f"{BASE_URL}/management/school-year/closure/{closure_id}", wait_until="networkidle")
                dismiss_toasts(page)
                page.get_by_role("button", name=re.compile(r"Cancel closure", re.I)).click()
                page.wait_for_selector("#mgmtSycCancelModal.show, #mgmtSycCancelModal[style*='display: block']", timeout=5_000)
                page.fill("#cancel_reason", "E2E automated test cleanup")
                page.fill("#cancel_confirm", "CANCEL")
                page.locator("#mgmtSycCancelModal button.btn-danger[type=submit]").click()
                page.wait_for_load_state("networkidle")
                expect(page.locator(".mgmt-syc-phase-badge")).to_contain_text("Cancelled")

            run_test("Cancel closure (cleanup)", test_cancel_closure, results)
        else:
            results.append(Result("Closure workflow", False, "Could not determine closure_id"))
            print("  FAIL  Closure workflow: no closure_id")

        browser.close()

    passed = sum(1 for r in results if r.ok)
    failed = len(results) - passed
    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    if failed:
        for r in results:
            if not r.ok:
                print(f"  - {r.name}: {r.detail}")
        return 1
    return 0


def _closure_id_from_db():
    from app import create_app
    from models import SchoolYearClosure
    from services import school_year_closure as syc

    app = create_app()
    with app.app_context():
        c = (
            SchoolYearClosure.query.filter(
                SchoolYearClosure.phase.notin_(syc.TERMINAL_PHASES)
            )
            .order_by(SchoolYearClosure.id.desc())
            .first()
        )
        if c:
            return c.id
        c = SchoolYearClosure.query.order_by(SchoolYearClosure.id.desc()).first()
        return c.id if c else None


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
