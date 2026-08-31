#!/usr/bin/env python3
"""
On-demand: put every active student in the Google Group that matches their
current grade level (elementary / middle_school / highschool + studentassembly)
and remove them from the school-level groups they have outgrown.

Grade promotions used to update only the Clara database and the Workspace org
unit, so students who moved up a school level kept their old group. Run this
once to repair existing membership; new promotions now sync automatically.

Per-class groups (class-*@…) are NOT touched here — use
ops/sync_class_google_classroom_rosters.py --also-groups for those.

Run from the Render Shell (same DATABASE_URL + Google env as the web service):

  FLASK_ENV=production python ops/sync_student_school_level_groups.py --dry-run
  FLASK_ENV=production python ops/sync_student_school_level_groups.py
  FLASK_ENV=production python ops/sync_student_school_level_groups.py --grade 6 --grade 7
  FLASK_ENV=production python ops/sync_student_school_level_groups.py --student-id 42

This runs synchronously so it finishes even if a web request would time out.
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync student school-level Google Group membership to their current grade."
    )
    parser.add_argument(
        "--grade",
        type=int,
        action="append",
        default=[],
        help="Only students in this grade level (repeatable).",
    )
    parser.add_argument(
        "--student-id",
        type=int,
        action="append",
        default=[],
        help="Only this student id (repeatable).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change; do not call Google writes.",
    )
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=250,
        help="Pause between students to ease Google API rate limits (default 250).",
    )
    args = parser.parse_args()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)

    try:
        from app import create_app
        from config import DevelopmentConfig, ProductionConfig
    except Exception as exc:
        print(f"[ERROR] Bootstrap import failed: {exc}")
        return 1

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    ConfigClass = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=ConfigClass)

    from models import Student, User
    from services.google_sync_tasks import sync_single_user_to_google
    from services.google_ou_policy import school_level_group_for_grade

    with app.app_context():
        query = (
            Student.query.join(User, User.student_id == Student.id)
            .filter(
                Student.is_deleted.is_(False),
                Student.is_active.is_(True),
                User.google_workspace_email.isnot(None),
                User.google_workspace_email != "",
            )
        )
        if args.student_id:
            query = query.filter(Student.id.in_([int(x) for x in args.student_id]))
        if args.grade:
            query = query.filter(Student.grade_level.in_([int(g) for g in args.grade]))

        students = query.order_by(Student.grade_level, Student.last_name).all()
        print(f"Students to sync: {len(students)}")
        if not students:
            print("Nothing to do.")
            return 0

        ok = 0
        skipped = 0
        failed = 0

        for index, student in enumerate(students, start=1):
            user = User.query.filter_by(student_id=student.id).first()
            email = (getattr(user, "google_workspace_email", "") or "").strip()
            level = school_level_group_for_grade(getattr(student, "grade_level", None))
            label = (
                f"[{index}/{len(students)}] {student.first_name} {student.last_name} "
                f"grade={student.grade_level} level={level or 'none'} {email}"
            )

            if not email or not user:
                print(f"{label} SKIP (no Workspace email)")
                skipped += 1
                continue

            if args.dry_run:
                print(f"{label} DRY-RUN would sync groups")
                ok += 1
                continue

            try:
                if sync_single_user_to_google(user.id):
                    print(f"{label} OK")
                    ok += 1
                else:
                    print(f"{label} SKIP (sync reported nothing to do)")
                    skipped += 1
            except Exception as exc:
                print(f"{label} FAIL {exc}")
                failed += 1

            if args.sleep_ms > 0 and index < len(students):
                time.sleep(args.sleep_ms / 1000.0)

        print(f"Done. ok={ok} skipped={skipped} failed={failed} dry_run={args.dry_run}")
        return 0 if failed == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
