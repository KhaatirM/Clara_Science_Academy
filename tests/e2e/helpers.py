"""Shared helpers for Playwright E2E tests."""
from __future__ import annotations

import os
import sys
from datetime import date

# Repo root on path for app imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:5000")
E2E_PASSWORD = os.environ.get("E2E_PASSWORD")
if not E2E_PASSWORD:
    raise RuntimeError("Set E2E_PASSWORD in the environment before running Playwright e2e tests.")

USERS = {
    "director": os.environ.get("E2E_DIRECTOR_USER", "vmuhammad"),
    "admin": os.environ.get("E2E_ADMIN_USER", "kmuhammad1"),
    "teacher": os.environ.get("E2E_TEACHER_USER", "jabdullah"),
    "student": os.environ.get("E2E_STUDENT_USER", "jhope"),
}


def prepare_database():
    """Activate year data, set known passwords, cancel any in-flight closure."""
    from werkzeug.security import generate_password_hash

    from app import create_app
    from models import (
        Assignment,
        Class,
        Enrollment,
        SchoolYear,
        SchoolYearClosure,
        User,
        db,
    )
    from services import school_year_closure as syc

    app = create_app()
    with app.app_context():
        sy = SchoolYear.query.filter_by(name="2025-2026").first() or SchoolYear.query.first()
        if not sy:
            raise RuntimeError("No school year in database — cannot run E2E.")

        for y in SchoolYear.query.all():
            y.is_active = y.id == sy.id
        sy.is_active = True

        class_ids = []
        for c in Class.query.filter_by(school_year_id=sy.id).all():
            c.is_active = True
            class_ids.append(c.id)

        if class_ids:
            Enrollment.query.filter(Enrollment.class_id.in_(class_ids)).update(
                {Enrollment.is_active: True, Enrollment.dropped_at: None},
                synchronize_session=False,
            )

        for a in Assignment.query.filter(
            (Assignment.school_year_id == sy.id) | Assignment.class_id.in_(class_ids)
        ).all():
            a.status = "Active"
            if not a.school_year_id:
                a.school_year_id = sy.id

        for username in USERS.values():
            u = User.query.filter_by(username=username).first()
            if u:
                u.password_hash = generate_password_hash(E2E_PASSWORD)
                u.is_temporary_password = False

        for c in SchoolYearClosure.query.filter(
            SchoolYearClosure.phase.notin_(syc.TERMINAL_PHASES)
        ).all():
            c.phase = syc.PHASE_CANCELLED
            c.cancellation_reason = "E2E test cleanup"

        db.session.commit()
        return {"school_year_id": sy.id, "school_year_name": sy.name}


def login(page, username: str, password: str | None = None):
    password = password or E2E_PASSWORD
    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#loginBtn")
    page.wait_for_load_state("networkidle", timeout=30_000)
    dismiss_toasts(page)


def logout(page):
    page.goto(f"{BASE_URL}/logout", wait_until="domcontentloaded")


def csrf_token(page) -> str:
    """Read CSRF token from the current page (dashboard layouts)."""
    if page.locator('meta[name="csrf-token"]').count() == 0:
        page.goto(f"{BASE_URL}/dashboard", wait_until="domcontentloaded")
    token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    if not token:
        raise RuntimeError("Could not read csrf-token meta tag")
    return token


class PostResult:
    """Minimal response wrapper for in-browser fetch POSTs."""

    def __init__(self, status: int, url: str = "", text: str = ""):
        self.status = status
        self.url = url
        self.text = text

    @property
    def blocked_by_closure(self) -> bool:
        """True when closure gate stopped the write (not a bare validation 400)."""
        if self.status in (302, 303, 403):
            return True
        if self.status == 400 and "no file selected" in self.text.lower():
            return False
        if self.status == 200 and "read-only" in self.text.lower():
            return True
        return self.status != 400


def post_with_csrf(page, url: str, form: dict | None = None) -> PostResult:
    """
    POST using the logged-in browser session (same cookies as the UI).
    Playwright's page.request does not always share the page cookie jar on Windows.
    """
    form = form or {}
    payload = page.evaluate(
        """async ([url, fields]) => {
          const token = document.querySelector('meta[name="csrf-token"]')?.content || '';
          const fd = new FormData();
          for (const [k, v] of Object.entries(fields)) fd.append(k, v);
          const resp = await fetch(url, {
            method: 'POST',
            body: fd,
            credentials: 'same-origin',
            headers: token ? { 'X-CSRFToken': token } : {},
          });
          const text = await resp.text();
          return { status: resp.status, url: resp.url, text: text.slice(0, 500) };
        }""",
        [url, form],
    )
    return PostResult(payload["status"], payload.get("url", ""), payload.get("text", ""))


def dismiss_toasts(page):
    """Close Bootstrap toasts that block clicks (e.g. academic alerts on login)."""
    page.evaluate(
        """() => {
          document.querySelectorAll('.toast.show .btn-close').forEach((btn) => btn.click());
          document.querySelectorAll('.toast.show').forEach((t) => t.classList.remove('show'));
        }"""
    )


def set_hidden_select(page, select_id: str, value: str):
    """Set a d-none <select> and fire change (pretty-select UIs)."""
    page.evaluate(
        """([id, val]) => {
          const el = document.getElementById(id);
          if (!el) throw new Error('Missing select #' + id);
          el.value = val;
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        [select_id, value],
    )
    page.wait_for_timeout(300)
