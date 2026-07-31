#!/usr/bin/env python3
"""
Repair Google Workspace OU placements.

Named fixes (Jul 2026):
  - Zawadi Ajuwa  → /Students/High School/Class of 2029 (active)
  - Mason Jackson → /Students/Alumni/Middle/Class of 2029 (MS graduate)
  - Major Sharif  → /Students/Alumni/Middle/Class of 2029 (MS graduate)
  - Jayden Hope   → /Students/Transferred & Removed/Class of 2029 (withdrawn)

Also scans all suspended Workspace users still under active student OUs
(Elementary / Middle School / High School) and moves them to
Transferred & Removed (Class of year inferred from current OU when possible).

Usage (Render shell, after deploy):

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
    "/Students/Elementary/",
    "/Students/Middle School/",
    "/Students/High School/",
    # Edge: parked at school level without class folder
    "/Students/Elementary",
    "/Students/Middle School",
    "/Students/High School",
)


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
    for prefix in ACTIVE_STUDENT_OU_PREFIXES:
        p = prefix.rstrip("/")
        if path == p or path.startswith(p + "/"):
            # Exclude Alumni / Transferred even if nested oddly
            if "/Alumni" in path or "Transferred" in path:
                return False
            return True
    return False


def _set_cohort_year(student, year: int) -> None:
    student.expected_graduation_year = int(year)
    student.grad_year = int(year)
    # Keep month/year string in sync when present.
    if getattr(student, "expected_grad_date", None):
        student.expected_grad_date = f"06/{int(year)}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix Google OU placements.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-scan",
        action="store_true",
        help="Only fix named students; skip suspended-in-active-OU scan.",
    )
    args = parser.parse_args()
    _bootstrap_path()

    from app import create_app
    from config import DevelopmentConfig, ProductionConfig

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    config_class = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=config_class)

    # Same MS cohort as Zawadi (HS Class of 2029).
    COHORT_YEAR = 2029

    targets = [
        {"first": "Zawadi", "last": "Ajuwa", "ensure": "active_hs", "cohort_year": COHORT_YEAR},
        {"first": "Mason", "last": "Jackson", "ensure": "alumni", "cohort_year": COHORT_YEAR},
        {"first": "Major", "last": "Sharif", "ensure": "alumni", "cohort_year": COHORT_YEAR},
        {"first": "Jayden", "last": "Hope", "ensure": "transferred", "cohort_year": COHORT_YEAR},
    ]

    with app.app_context():
        from datetime import datetime, timezone

        from extensions import db
        from management_routes.students import _student_workspace_email
        from services.google_directory_service import (
            get_google_user,
            list_google_users,
            move_user_to_ou,
            suspend_user,
        )
        from services.google_ou_policy import (
            STUDENT_OU_TRANSFERRED_REMOVED,
            resolve_student_ou,
            _sanitize_ou_path,
        )

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
                    "grad_year": getattr(student, "grad_year", None),
                }

                cohort = int(t.get("cohort_year") or COHORT_YEAR)
                _set_cohort_year(student, cohort)

                if t["ensure"] == "alumni":
                    student.is_active = False
                    student.is_deleted = False
                    student.departure_status = "graduated"
                    student.marked_for_removal = False
                    # Keep finished MS grade (8) for alumni tier.
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

                email = (_student_workspace_email(student) or "").strip().lower()
                g_user = get_google_user(email) if email else None
                current_ou = (g_user or {}).get("orgUnitPath")

                moved = None
                suspended = None
                if args.dry_run:
                    db.session.rollback()
                else:
                    db.session.commit()
                    if email:
                        handled_emails.add(email)
                        moved = move_user_to_ou(email, decision.target_ou_path)
                        if t["ensure"] in ("alumni", "transferred"):
                            suspended = suspend_user(email)

                named_results.append(
                    {
                        **t,
                        "ok": True,
                        "email": email or None,
                        "before_db": before_db,
                        "after_db": {
                            "grade_level": student.grade_level,
                            "is_active": student.is_active,
                            "is_deleted": student.is_deleted,
                            "departure_status": getattr(student, "departure_status", None),
                            "expected_graduation_year": getattr(
                                student, "expected_graduation_year", None
                            ),
                        },
                        "current_ou": current_ou,
                        "target_ou": decision.target_ou_path,
                        "reason": decision.reason,
                        "moved": moved,
                        "suspended": suspended,
                    }
                )
            except Exception as exc:
                db.session.rollback()
                named_results.append({**t, "ok": False, "error": str(exc)})

        scan_results = []
        if not args.skip_scan:
            suspended_users = list_google_users(query="isSuspended=true")
            for gu in suspended_users:
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
                moved = None
                if args.dry_run:
                    moved = None
                else:
                    moved = move_user_to_ou(email, target_ou)

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

        payload = {
            "named": named_results,
            "suspended_in_active_ou": scan_results,
            "suspended_in_active_ou_count": len(scan_results),
        }
        print(json.dumps(payload, indent=2, default=str))
        if args.dry_run:
            print("Dry run — no DB/Google changes saved.")
        else:
            print(
                f"Done. Named={sum(1 for r in named_results if r.get('ok'))}/{len(named_results)}; "
                f"scan_moved={sum(1 for r in scan_results if r.get('moved'))}/{len(scan_results)}."
            )

        named_ok = all(r.get("ok") for r in named_results) if named_results else True
        scan_ok = all(r.get("ok") for r in scan_results) if scan_results else True
        return 0 if named_ok and scan_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
