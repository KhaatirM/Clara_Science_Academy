#!/usr/bin/env python3
"""
Repair Google Workspace OU placements.

Named fixes:
  - Zawadi Ajuwa  → High School / Class of 2029
  - Mason Jackson → Alumni/Middle / Class of 2029
  - Major Sharif  → Alumni/Middle / Class of 2029
  - Jayden Hope   → Transferred & Removed / Class of 2029

Also:
  1) Suspended Workspace users still under active Elementary/Middle/High School OUs
     → Transferred & Removed
  2) All DB “Removed” / withdrawn students grade 3+ (portal Account=Removed)
     whose Workspace account is missing from Transferred & Removed
     → move + suspend (covers Emack Akili, Nathan Cassidy, Esther Hope, etc.)

Usage:

  python ops/fix_google_ou_placements.py --dry-run
  python ops/fix_google_ou_placements.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys


def _bootstrap_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


ACTIVE_STUDENT_OU_PREFIXES = (
    "/Students/Elementary",
    "/Students/Middle School",
    "/Students/High School",
)

TRANSFERRED_OU_MARKER = "Transferred & Removed"


def _find_student(first: str, last: str):
    from models import Student

    return Student.query.filter(
        Student.first_name.ilike(first),
        Student.last_name.ilike(last),
    ).all()


def _class_year_from_ou(ou_path: str | None) -> int | None:
    if not ou_path:
        return None
    m = re.search(r"Class of\s+(\d{4})", ou_path, flags=re.I)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _is_under_active_student_ou(ou_path: str | None) -> bool:
    if not ou_path:
        return False
    path = ou_path.rstrip("/")
    if TRANSFERRED_OU_MARKER in path or "/Alumni" in path:
        return False
    for prefix in ACTIVE_STUDENT_OU_PREFIXES:
        p = prefix.rstrip("/")
        if path == p or path.startswith(p + "/"):
            return True
    return False


def _is_under_transferred_ou(ou_path: str | None) -> bool:
    if not ou_path:
        return False
    return TRANSFERRED_OU_MARKER in ou_path


def _set_cohort_year(student, year: int) -> None:
    student.expected_graduation_year = int(year)
    student.grad_year = int(year)
    if getattr(student, "expected_grad_date", None):
        student.expected_grad_date = f"06/{int(year)}"


def _candidate_workspace_emails(student) -> list[str]:
    """Best-effort Workspace emails when the portal User row was stripped."""
    from management_routes.students import _student_workspace_email

    out: list[str] = []
    primary = (_student_workspace_email(student) or "").strip().lower()
    if primary:
        out.append(primary)

    def _add_generated_from_first(first_name: str) -> None:
        if not first_name or not student.last_name or not student.dob:
            return
        # Temporarily use a single given name (Esther Marie → Esther).
        original = student.first_name
        try:
            student.first_name = first_name
            generated = (student.generate_email() or "").strip().lower()
        except Exception:
            generated = ""
        finally:
            student.first_name = original
        if not generated:
            return
        if generated not in out:
            out.append(generated)
        if "@" in generated:
            local, _, domain = generated.partition("@")
            base_local = re.sub(r"\d+$", "", local) or local
            for n in range(2, 6):
                cand = f"{base_local}{n}@{domain}".lower()
                if cand not in out:
                    out.append(cand)

    first_full = (student.first_name or "").strip()
    _add_generated_from_first(first_full)
    # Also try first token only (Esther Marie Hope → Esther…).
    first_token = first_full.split()[0] if first_full else ""
    if first_token and first_token.lower() != first_full.lower().replace(" ", ""):
        _add_generated_from_first(first_token)

    email_field = (getattr(student, "email", None) or "").strip().lower()
    if email_field.endswith("@clarascienceacademy.org") and email_field not in out:
        out.append(email_field)

    return out


def _resolve_google_account(student):
    """Return (email, google_user_dict) for the first candidate that exists in Directory."""
    from services.google_directory_service import get_google_user

    for email in _candidate_workspace_emails(student):
        gu = get_google_user(email, quiet_404=True)
        if gu:
            return email, gu
    return None, None


def _transferred_target_ou(student, current_ou: str | None, fallback_year: int) -> str:
    from services.google_ou_policy import (
        STUDENT_OU_TRANSFERRED_REMOVED,
        resolve_student_ou,
        _sanitize_ou_path,
    )

    # Always prefer policy Class of (grade/cohort), not the (often stale) current OU year.
    decision = resolve_student_ou(
        grade_level=getattr(student, "grade_level", None),
        grad_year=getattr(student, "grad_year", None),
        expected_grad_date=getattr(student, "expected_grad_date", None),
        is_active=False,
        marked_for_removal=False,
        is_deleted=True,
        status_updated_at=getattr(student, "status_updated_at", None),
        expected_graduation_year=getattr(student, "expected_graduation_year", None),
        departure_status="withdrawn",
    )
    if decision.target_ou_path and TRANSFERRED_OU_MARKER in decision.target_ou_path:
        return decision.target_ou_path

    class_year = (
        getattr(student, "expected_graduation_year", None)
        or getattr(student, "grad_year", None)
        or _class_year_from_ou(current_ou)
        or fallback_year
    )
    return _sanitize_ou_path(
        f"/Students/{STUDENT_OU_TRANSFERRED_REMOVED}/Class of {int(class_year)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix Google OU placements.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-scan",
        action="store_true",
        help="Skip Google suspended-in-active-OU scan.",
    )
    parser.add_argument(
        "--skip-removed-roster",
        action="store_true",
        help="Skip DB Removed grade-3+ → Transferred scan.",
    )
    args = parser.parse_args()
    _bootstrap_path()

    from app import create_app
    from config import DevelopmentConfig, ProductionConfig

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    config_class = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=config_class)

    COHORT_YEAR = 2029

    targets = [
        {"first": "Zawadi", "last": "Ajuwa", "ensure": "active_hs", "cohort_year": COHORT_YEAR},
        {"first": "Mason", "last": "Jackson", "ensure": "alumni", "cohort_year": COHORT_YEAR},
        {"first": "Major", "last": "Sharif", "ensure": "alumni", "cohort_year": COHORT_YEAR},
        {"first": "Jayden", "last": "Hope", "ensure": "transferred", "cohort_year": COHORT_YEAR},
        # Explicit callouts from former roster (also covered by removed-roster scan).
        {"first": "Emack", "last": "Akili", "ensure": "transferred"},
        {"first": "Nathan", "last": "Cassidy", "ensure": "transferred"},
    ]

    with app.app_context():
        from datetime import datetime, timezone

        from extensions import db
        from models import Student
        from services.google_directory_service import (
            list_google_users,
            move_user_to_ou,
            suspend_user,
        )
        from services.google_ou_policy import (
            STUDENT_OU_TRANSFERRED_REMOVED,
            resolve_student_ou,
            _sanitize_ou_path,
        )
        from utils.student_login_policy import grade_may_have_login

        named_results = []
        handled_emails: set[str] = set()

        for t in targets:
            try:
                matches = _find_student(t["first"], t["last"])
                if not matches:
                    named_results.append({**t, "ok": False, "error": "not found in DB"})
                    continue
                if len(matches) > 1:
                    named_results.append(
                        {
                            **t,
                            "ok": False,
                            "error": "multiple matches",
                            "ids": [s.id for s in matches],
                        }
                    )
                    continue

                student = matches[0]
                before_db = {
                    "id": student.id,
                    "grade_level": student.grade_level,
                    "is_active": student.is_active,
                    "is_deleted": student.is_deleted,
                    "departure_status": getattr(student, "departure_status", None),
                    "expected_graduation_year": getattr(
                        student, "expected_graduation_year", None
                    ),
                }

                if t.get("cohort_year"):
                    _set_cohort_year(student, int(t["cohort_year"]))

                if t["ensure"] == "alumni":
                    student.is_active = False
                    student.is_deleted = False
                    student.departure_status = "graduated"
                    student.marked_for_removal = False
                    if student.grade_level is None or int(student.grade_level) > 8:
                        student.grade_level = 8
                    student.status_updated_at = datetime.now(timezone.utc)
                elif t["ensure"] == "transferred":
                    student.is_deleted = True
                    student.is_active = False
                    student.departure_status = "withdrawn"
                    student.marked_for_removal = False
                    student.status_updated_at = datetime.now(timezone.utc)
                elif t["ensure"] == "active_hs":
                    student.is_active = True
                    student.is_deleted = False
                    student.departure_status = None
                    student.marked_for_removal = False
                    if student.grade_level is None or int(student.grade_level) < 9:
                        student.grade_level = 9

                decision = resolve_student_ou(
                    grade_level=getattr(student, "grade_level", None),
                    grad_year=getattr(student, "grad_year", None),
                    expected_grad_date=getattr(student, "expected_grad_date", None),
                    is_active=bool(getattr(student, "is_active", True)),
                    marked_for_removal=bool(getattr(student, "marked_for_removal", False)),
                    is_deleted=bool(getattr(student, "is_deleted", False)),
                    status_updated_at=getattr(student, "status_updated_at", None),
                    expected_graduation_year=getattr(
                        student, "expected_graduation_year", None
                    ),
                    departure_status=getattr(student, "departure_status", None),
                )

                email, g_user = _resolve_google_account(student)
                current_ou = (g_user or {}).get("orgUnitPath")
                target_ou = decision.target_ou_path
                if t["ensure"] == "transferred":
                    target_ou = _transferred_target_ou(
                        student, current_ou, COHORT_YEAR
                    )

                moved = None
                suspended = None
                already_ok = bool(current_ou and current_ou == target_ou)

                if args.dry_run:
                    db.session.rollback()
                else:
                    db.session.commit()
                    if email:
                        handled_emails.add(email)
                        if not already_ok:
                            moved = move_user_to_ou(email, target_ou)
                        if t["ensure"] in ("alumni", "transferred"):
                            suspended = suspend_user(email)

                named_results.append(
                    {
                        **t,
                        "ok": True if email or t["ensure"] == "active_hs" else False,
                        "email": email,
                        "before_db": before_db,
                        "current_ou": current_ou,
                        "target_ou": target_ou,
                        "already_in_target": already_ok or (current_ou == target_ou),
                        "moved": moved,
                        "suspended": suspended,
                        "error": None if email else "no Workspace account found",
                    }
                )
            except Exception as exc:
                db.session.rollback()
                named_results.append({**t, "ok": False, "error": str(exc)})

        # --- Pass: suspended Google users still in active school OUs ---
        scan_results = []
        if not args.skip_scan:
            for gu in list_google_users(query="isSuspended=true"):
                email = (gu.get("primaryEmail") or "").strip().lower()
                if not email or email in handled_emails:
                    continue
                current_ou = gu.get("orgUnitPath") or ""
                if not _is_under_active_student_ou(current_ou):
                    continue
                class_year = _class_year_from_ou(current_ou) or COHORT_YEAR
                target_ou = _sanitize_ou_path(
                    f"/Students/{STUDENT_OU_TRANSFERRED_REMOVED}/Class of {class_year}"
                )
                moved = None if args.dry_run else move_user_to_ou(email, target_ou)
                handled_emails.add(email)
                scan_results.append(
                    {
                        "email": email,
                        "name": (gu.get("name") or {}).get("fullName"),
                        "current_ou": current_ou,
                        "target_ou": target_ou,
                        "moved": moved,
                        "ok": True if args.dry_run else bool(moved),
                    }
                )

        # --- Pass: DB Removed / withdrawn, grade 3+, not already in Transferred ---
        removed_results = []
        if not args.skip_removed_roster:
            removed_students = Student.query.filter(Student.is_deleted.is_(True)).all()
            for student in removed_students:
                if not grade_may_have_login(getattr(student, "grade_level", None)):
                    continue
                # Skip alumni graduates (kept as is_deleted=False usually, but be safe).
                if (getattr(student, "departure_status", None) or "").lower() == "graduated":
                    continue

                email, g_user = _resolve_google_account(student)
                if not email or not g_user:
                    removed_results.append(
                        {
                            "id": student.id,
                            "name": f"{student.first_name} {student.last_name}".strip(),
                            "grade_level": student.grade_level,
                            "ok": False,
                            "error": "no Workspace account found",
                        }
                    )
                    continue

                if email in handled_emails:
                    continue

                current_ou = g_user.get("orgUnitPath") or ""
                target_ou = _transferred_target_ou(student, current_ou, COHORT_YEAR)
                if current_ou == target_ou:
                    removed_results.append(
                        {
                            "id": student.id,
                            "name": f"{student.first_name} {student.last_name}".strip(),
                            "email": email,
                            "current_ou": current_ou,
                            "already_ok": True,
                            "ok": True,
                        }
                    )
                    handled_emails.add(email)
                    continue

                # Align DB withdrawal fields if missing.
                student.is_active = False
                student.departure_status = (
                    getattr(student, "departure_status", None) or "withdrawn"
                )
                if not getattr(student, "status_updated_at", None):
                    student.status_updated_at = datetime.now(timezone.utc)

                moved = None
                suspended = None
                if args.dry_run:
                    db.session.rollback()
                else:
                    db.session.commit()
                    moved = move_user_to_ou(email, target_ou)
                    suspended = suspend_user(email)
                handled_emails.add(email)
                removed_results.append(
                    {
                        "id": student.id,
                        "name": f"{student.first_name} {student.last_name}".strip(),
                        "grade_level": student.grade_level,
                        "email": email,
                        "current_ou": current_ou,
                        "target_ou": target_ou,
                        "moved": moved,
                        "suspended": suspended,
                        "ok": True if args.dry_run else bool(moved),
                    }
                )

        payload = {
            "named": named_results,
            "suspended_in_active_ou": scan_results,
            "removed_roster_grade3plus": removed_results,
            "counts": {
                "named_ok": sum(1 for r in named_results if r.get("ok")),
                "suspended_scan": len(scan_results),
                "removed_need_move": sum(
                    1 for r in removed_results if r.get("moved") or (args.dry_run and r.get("target_ou"))
                ),
                "removed_already_ok": sum(1 for r in removed_results if r.get("already_ok")),
                "removed_missing_email": sum(
                    1 for r in removed_results if r.get("error") == "no Workspace account found"
                ),
            },
        }
        print(json.dumps(payload, indent=2, default=str))
        if args.dry_run:
            print("Dry run — no DB/Google changes saved.")
        else:
            print("Done.")

        named_ok = all(r.get("ok") for r in named_results) if named_results else True
        # Missing Workspace email for old removals is reported but not a hard failure.
        return 0 if named_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
