"""Smoke tests for Family Portal, report card approval, and related routes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _force_login(client, user_id: int) -> None:
    """Authenticate for route smoke tests without posting credentials."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def _resolve_smoke_parent():
    """First Parent with at least one linked child, or user id from SMOKE_PARENT_USER_ID."""
    from models import ParentStudentLink, User

    raw_id = (os.environ.get("SMOKE_PARENT_USER_ID") or "").strip()
    if raw_id.isdigit():
        candidate = User.query.get(int(raw_id))
        if candidate and candidate.role == "Parent":
            return candidate

    return (
        User.query.filter_by(role="Parent")
        .join(ParentStudentLink, ParentStudentLink.parent_user_id == User.id)
        .first()
    )


def main() -> int:
    from app import create_app, db
    from models import ParentStudentLink, ReportCard, Student, User
    from sqlalchemy import inspect
    from utils.report_card_portal import (
        get_parent_visible_report_cards,
        is_official_report_card,
        parent_can_download_report_card,
    )

    app = create_app()
    failures: list[str] = []
    passes: list[str] = []

    def ok(msg: str) -> None:
        passes.append(msg)
        print(f"  PASS  {msg}")

    def fail(msg: str) -> None:
        failures.append(msg)
        print(f"  FAIL  {msg}")

    with app.app_context():
        # --- Schema ---
        insp = inspect(db.engine)
        tables = set(insp.get_table_names())
        if "parent_student_link" in tables:
            ok("parent_student_link table exists")
        else:
            fail("parent_student_link table missing")

        rc_cols = {c["name"] for c in insp.get_columns("report_card")}
        for col in ("director_approved", "approved_at", "approved_by_user_id"):
            if col in rc_cols:
                ok(f"report_card.{col} column exists")
            else:
                fail(f"report_card.{col} column missing")

        # --- Routes registered ---
        rules = {r.rule: r.endpoint for r in app.url_map.iter_rules()}
        for rule, label in (
            ("/parent/dashboard", "parent dashboard"),
            ("/parent/settings", "parent settings"),
            ("/parent/child/<int:student_id>/report-cards", "parent report cards list"),
            ("/parent/report-card/<int:report_card_id>/pdf", "parent report card PDF"),
            ("/management/parents", "management parents hub"),
            ("/management/report-cards/approve/<int:report_card_id>", "director approve"),
            ("/management/report-cards/revoke/<int:report_card_id>", "director revoke"),
        ):
            if rule in rules:
                ok(f"Route registered: {label}")
            else:
                fail(f"Route missing: {label} ({rule})")

        # --- Parent user + links ---
        parent = _resolve_smoke_parent()
        if parent:
            ok(f"Test parent account exists ({parent.username})")
            children = (
                Student.query.join(ParentStudentLink)
                .filter(ParentStudentLink.parent_user_id == parent.id)
                .all()
            )
            if len(children) >= 1:
                ok(f"Parent linked to {len(children)} child(ren)")
            else:
                fail("Test parent has no linked children")
        else:
            fail("No Parent account with linked children found (skip login tests)")

        director = User.query.filter_by(role="Director").first()
        if director:
            ok(f"Director account found ({director.username})")
        else:
            fail("No Director account for approval tests")

    client = app.test_client()

    # --- Unauthenticated redirects ---
    for path in ("/parent/dashboard", "/parent/settings", "/management/parents"):
        resp = client.get(path, follow_redirects=False)
        if resp.status_code in (302, 401):
            ok(f"GET {path} requires auth ({resp.status_code})")
        else:
            fail(f"GET {path} expected 302/401, got {resp.status_code}")

    # --- Parent authenticated routes ---
    if parent:
        _force_login(client, parent.id)
        ok("Parent session established for smoke tests")

        for path, name in (
            ("/parent/dashboard", "dashboard"),
            ("/parent/settings", "settings"),
        ):
            resp = client.get(path)
            if resp.status_code == 200:
                ok(f"Parent {name} loads (200)")
            else:
                fail(f"Parent {name} returned {resp.status_code}")

        with app.app_context():
            child = (
                Student.query.join(ParentStudentLink)
                .filter(ParentStudentLink.parent_user_id == parent.id)
                .first()
            )
        if child:
            for suffix, name in (
                (f"/parent/child/{child.id}/grades", "grades"),
                (f"/parent/child/{child.id}/attendance", "attendance"),
                (f"/parent/child/{child.id}/classes", "classes"),
                (f"/parent/child/{child.id}/report-cards", "report cards"),
            ):
                resp = client.get(suffix)
                if resp.status_code == 200:
                    ok(f"Parent {name} tab loads (200)")
                else:
                    fail(f"Parent {name} tab returned {resp.status_code}")

            # Report card PDF: only if an approved card exists
            with app.app_context():
                visible = get_parent_visible_report_cards(child.id)
                all_rc = ReportCard.query.filter_by(student_id=child.id).all()
                official = [rc for rc in all_rc if is_official_report_card(rc)]
                if official:
                    pending = [rc for rc in official if not rc.director_approved]
                    if pending:
                        ok(f"Official report cards exist; {len(pending)} awaiting Director approval")
                    if visible:
                        rc = visible[0]
                        if parent_can_download_report_card(parent.id, rc.id):
                            pdf = client.get(f"/parent/report-card/{rc.id}/pdf")
                            if pdf.status_code == 200 and "pdf" in (pdf.content_type or "").lower():
                                ok("Approved report card PDF downloads (200, application/pdf)")
                            else:
                                fail(f"Report card PDF returned {pdf.status_code} / {pdf.content_type}")
                        else:
                            fail("parent_can_download_report_card returned False for visible card")
                    else:
                        ok("No Director-approved report cards yet (expected until approval)")
                else:
                    ok("No official report cards for test child (PDF gate N/A)")

            # Block unapproved PDF
            with app.app_context():
                unapproved = (
                    ReportCard.query.filter_by(student_id=child.id, director_approved=False)
                    .first()
                )
            if unapproved and is_official_report_card(unapproved):
                blocked = client.get(
                    f"/parent/report-card/{unapproved.id}/pdf",
                    follow_redirects=False,
                )
                if blocked.status_code in (403, 302):
                    loc = blocked.headers.get("Location") or ""
                    if blocked.status_code == 403 or "parent" in loc or "login" in loc:
                        ok(f"Unapproved report card PDF blocked ({blocked.status_code})")
                    else:
                        fail(f"Unapproved PDF blocked oddly: {blocked.status_code} → {loc}")
                else:
                    fail(f"Unapproved PDF should be blocked, got {blocked.status_code}")

            # Approve one card in-process, then verify parent can download
            with app.app_context():
                from utils.report_card_portal import approve_report_card_for_parents

                to_approve = (
                    ReportCard.query.filter_by(student_id=child.id, director_approved=False)
                    .order_by(ReportCard.generated_at.desc())
                    .first()
                )
                if to_approve and is_official_report_card(to_approve) and director:
                    approve_report_card_for_parents(to_approve, director.id)
                    ok(f"Director approved report card #{to_approve.id} for smoke test")
                    pdf = client.get(f"/parent/report-card/{to_approve.id}/pdf")
                    if pdf.status_code == 200 and "pdf" in (pdf.content_type or "").lower():
                        ok("Approved report card PDF downloads after Director approval")
                    else:
                        fail(
                            f"Approved PDF failed: {pdf.status_code} / {pdf.content_type}"
                        )

        # Theme update endpoint
        theme_resp = client.post(
            "/update-theme",
            data={"theme": "ocean"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        if theme_resp.status_code == 200:
            data = theme_resp.get_json(silent=True) or {}
            if data.get("success"):
                ok("Parent theme save via /update-theme (200)")
            else:
                fail(f"Theme update JSON not success: {data}")
        else:
            fail(f"Theme update returned {theme_resp.status_code}")

        client.get("/logout", follow_redirects=True)

    # --- Director approve route (auth only) ---
    if director:
        with app.app_context():
            rc = ReportCard.query.filter_by(director_approved=False).first()
            rc_id = rc.id if rc else 1
        _force_login(client, director.id)
        ok("Director session established for smoke tests")
        resp = client.post(f"/management/report-cards/approve/{rc_id}", follow_redirects=False)
        if resp.status_code in (302, 303, 200):
            ok("Director approve endpoint responds")
        else:
            fail(f"Director approve returned {resp.status_code}")
        client.get("/logout", follow_redirects=True)

    print()
    print(f"Results: {len(passes)} passed, {len(failures)} failed")
    for f in failures:
        print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
