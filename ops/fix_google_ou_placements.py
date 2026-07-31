#!/usr/bin/env python3
"""
Repair Google Workspace OU placement for known mis-placed students.

Targets (per ops request Jul 2026):
  - Zawadi Ajuwa     → /Students/High School/Class of … (active 9th)
  - Mason Jackson    → /Students/Alumni/Middle/Class of … (MS graduate)
  - Jayden Hope      → /Students/Alumni/Middle/Class of … (MS graduate / alumni)
  - Major Sharif     → /Students/Transferred & Removed/Class of … (withdrawn)

Usage (Render shell, after deploy):

  python ops/fix_google_ou_placements.py --dry-run
  python ops/fix_google_ou_placements.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _bootstrap_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


def _find_student(first: str, last: str):
    from models import Student

    matches = (
        Student.query.filter(
            Student.first_name.ilike(first),
            Student.last_name.ilike(last),
        ).all()
    )
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix Google OU placements for named students.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _bootstrap_path()

    from app import create_app
    from config import DevelopmentConfig, ProductionConfig

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    config_class = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=config_class)

    # Explicit overrides: policy is used unless force_ou / force_departure is set.
    targets = [
        {
            "first": "Zawadi",
            "last": "Ajuwa",
            "ensure": "active_hs",  # grade 9+, active
        },
        {
            "first": "Mason",
            "last": "Jackson",
            "ensure": "alumni",  # graduated MS → Alumni/Middle
        },
        {
            "first": "Jayden",
            "last": "Hope",
            "ensure": "alumni",
        },
        {
            "first": "Major",
            "last": "Sharif",
            "ensure": "transferred",  # withdrawn → Transferred & Removed
        },
    ]

    with app.app_context():
        from datetime import datetime, timezone

        from extensions import db
        from management_routes.students import _student_workspace_email
        from services.google_directory_service import (
            get_google_user,
            move_user_to_ou,
            suspend_user,
        )
        from services.google_ou_policy import resolve_student_ou
        from utils.student_departure import mark_student_graduated, mark_student_withdrawn

        results = []
        for t in targets:
            try:
                matches = _find_student(t["first"], t["last"])
                if not matches:
                    results.append({**t, "ok": False, "error": "not found in DB"})
                    continue
                if len(matches) > 1:
                    results.append(
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
                }

                # Align DB departure state to the intended OU destination.
                if t["ensure"] == "alumni":
                    if getattr(student, "departure_status", None) != "graduated":
                        if not args.dry_run:
                            mark_student_graduated(student, strip_login=False)
                    student.is_active = False
                    student.is_deleted = False
                    student.departure_status = "graduated"
                    student.status_updated_at = datetime.now(timezone.utc)
                elif t["ensure"] == "transferred":
                    if getattr(student, "departure_status", None) != "withdrawn":
                        if not args.dry_run:
                            mark_student_withdrawn(student, strip_login=False)
                    student.is_deleted = True
                    student.is_active = False
                    student.departure_status = "withdrawn"
                    student.status_updated_at = datetime.now(timezone.utc)
                elif t["ensure"] == "active_hs":
                    # Promoted 9th grader — leave active; do not mark departed.
                    student.is_active = True
                    student.is_deleted = False
                    student.departure_status = None
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
                    expected_graduation_year=getattr(student, "expected_graduation_year", None),
                    departure_status=getattr(student, "departure_status", None),
                )

                email = _student_workspace_email(student)
                g_user = get_google_user(email) if email else None
                current_ou = (g_user or {}).get("orgUnitPath")

                moved = None
                suspended = None
                if args.dry_run:
                    db.session.rollback()
                else:
                    db.session.commit()
                    if email:
                        moved = move_user_to_ou(email, decision.target_ou_path)
                        # Keep departed accounts suspended; active HS stays unsuspended.
                        if t["ensure"] in ("alumni", "transferred"):
                            suspended = suspend_user(email)

                results.append(
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
                results.append({**t, "ok": False, "error": str(exc)})

        print(json.dumps(results, indent=2, default=str))
        if args.dry_run:
            print("Dry run — no DB/Google changes saved.")
        else:
            print("Done.")
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
