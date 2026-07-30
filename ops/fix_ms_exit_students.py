#!/usr/bin/env python3
"""
One-shot fixes for middle-school exit / promotion after year close.

Examples (Render shell):

  python ops/fix_ms_exit_students.py --dry-run
  python ops/fix_ms_exit_students.py
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix named MS exit/promotion students.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _bootstrap_path()

    from app import create_app
    from config import DevelopmentConfig, ProductionConfig

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    config_class = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=config_class)

    with app.app_context():
        from extensions import db
        from models import Student
        from utils.student_departure import apply_outcome_now, promote_student_one_grade

        targets = [
            {"first": "Zawadi", "last": "Ajuwa", "action": "promote"},
            {"first": "Mason", "last": "Jackson", "action": "graduate"},
            {"first": "Major", "last": "Sharif", "action": "graduate"},
        ]
        results = []
        for t in targets:
            try:
                with db.session.no_autoflush:
                    matches = (
                        Student.query.filter(
                            Student.first_name.ilike(t["first"]),
                            Student.last_name.ilike(t["last"]),
                        ).all()
                    )
                if not matches:
                    results.append({**t, "ok": False, "error": "not found"})
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
                before = {
                    "id": student.id,
                    "grade_level": student.grade_level,
                    "is_active": student.is_active,
                    "is_deleted": student.is_deleted,
                    "departure_status": getattr(student, "departure_status", None),
                }
                if t["action"] == "promote":
                    ok = promote_student_one_grade(student)
                    action_result = "promoted" if ok else "skipped"
                else:
                    action_result = apply_outcome_now(student, t["action"])
                after = {
                    "grade_level": student.grade_level,
                    "is_active": student.is_active,
                    "is_deleted": student.is_deleted,
                    "departure_status": getattr(student, "departure_status", None),
                }
                if args.dry_run:
                    db.session.rollback()
                else:
                    db.session.commit()
                results.append(
                    {
                        **t,
                        "ok": action_result != "skipped",
                        "result": action_result,
                        "before": before,
                        "after": after,
                    }
                )
            except Exception as exc:
                db.session.rollback()
                results.append({**t, "ok": False, "error": str(exc)})

        print(json.dumps(results, indent=2, default=str))
        if args.dry_run:
            print("Dry run — no changes saved.")
        else:
            print("Done (per-student commits).")
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
