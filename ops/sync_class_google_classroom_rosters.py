#!/usr/bin/env python3
"""
One-time / on-demand: sync Google Classroom membership so every enrolled
grade 3+ student (with a Workspace email) is on their class course.

Also adds missing teachers and removes people who are no longer on the Clara
roster. Classes without a Classroom yet are provisioned, then synced.

Run from the Render Shell (same DATABASE_URL + Google env as the web service):

  FLASK_ENV=production python ops/sync_class_google_classroom_rosters.py --dry-run
  FLASK_ENV=production python ops/sync_class_google_classroom_rosters.py
  FLASK_ENV=production python ops/sync_class_google_classroom_rosters.py --school-year-id 12
  FLASK_ENV=production python ops/sync_class_google_classroom_rosters.py --class-id 42
  FLASK_ENV=production python ops/sync_class_google_classroom_rosters.py --linked-only --sleep-ms 500

This runs synchronously so it finishes even if a web request would time out.
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sync Google Classroom rosters for grade 3+ classes "
            "(add missing students/teachers)."
        )
    )
    parser.add_argument(
        "--school-year-id",
        type=int,
        default=None,
        help="Limit to this school year id (default: active year only).",
    )
    parser.add_argument(
        "--all-years",
        action="store_true",
        help="Include every school year (ignore active-year default).",
    )
    parser.add_argument(
        "--linked-only",
        action="store_true",
        help="Only classes that already have a google_classroom_id.",
    )
    parser.add_argument(
        "--also-groups",
        action="store_true",
        help="Also sync each class Google Group membership before Classroom.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report missing students/teachers; do not call Google writes.",
    )
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=400,
        help="Pause between classes to ease Google API rate limits (default 400).",
    )
    parser.add_argument(
        "--class-id",
        type=int,
        action="append",
        default=[],
        help="Only process this class id (repeatable).",
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

    from models import Class, SchoolYear
    from services.class_google_classroom import (
        collect_classroom_student_emails,
        collect_classroom_teacher_emails,
        provision_and_sync_class_google_classroom,
    )
    from services.class_google_group import (
        class_needs_google_integration,
        provision_and_sync_class_google_group,
    )
    from services.google_classroom_admin import (
        classroom_owner_email,
        list_course_student_emails,
        list_course_teacher_emails,
    )

    with app.app_context():
        owner = (classroom_owner_email() or "").strip()
        if not owner and not args.dry_run:
            print(
                "[ERROR] Classroom owner/botadmin email is not configured "
                "(GOOGLE_CLASSROOM_OWNER_EMAIL / related config)."
            )
            return 2
        if owner:
            print(f"Classroom owner: {owner}")

        year_id: int | None
        if args.all_years:
            year_id = None
            print("Scope: all school years")
        elif args.school_year_id is not None:
            year_id = int(args.school_year_id)
            sy = SchoolYear.query.get(year_id)
            print(f"Scope: school_year_id={year_id} name={getattr(sy, 'name', None)!r}")
        else:
            active = SchoolYear.query.filter_by(is_active=True).first()
            if not active:
                print("[ERROR] No active school year. Pass --school-year-id or --all-years.")
                return 3
            year_id = int(active.id)
            print(f"Scope: active school year id={year_id} name={active.name!r}")

        if args.class_id:
            ids = sorted({int(cid) for cid in args.class_id})
            print(f"Explicit class ids: {ids}")
        else:
            q = Class.query.filter(Class.is_active.is_(True))
            if year_id is not None:
                q = q.filter(Class.school_year_id == year_id)
            ids = []
            for class_obj in q.order_by(Class.id).all():
                if not class_needs_google_integration(class_obj):
                    continue
                course_id = (class_obj.google_classroom_id or "").strip()
                if args.linked_only and not course_id:
                    continue
                ids.append(int(class_obj.id))
            print(
                f"Classes to sync (grade 3+, "
                f"{'linked only' if args.linked_only else 'linked or create'}): {len(ids)}"
            )

        if not ids:
            print("Nothing to do.")
            return 0

        ok = 0
        fail = 0
        skipped = 0
        students_missing_total = 0
        teachers_missing_total = 0

        for i, cid in enumerate(ids, start=1):
            class_obj = Class.query.get(cid)
            if not class_obj:
                print(f"[{i}/{len(ids)}] class_id={cid} NOT FOUND")
                fail += 1
                continue

            grades = class_obj.get_grade_levels() if hasattr(class_obj, "get_grade_levels") else []
            course_id = (class_obj.google_classroom_id or "").strip()
            label = (
                f"[{i}/{len(ids)}] class_id={cid} name={class_obj.name!r} "
                f"grades={grades} year={class_obj.school_year_id} "
                f"classroom={course_id or 'NONE'}"
            )

            if not class_needs_google_integration(class_obj):
                print(f"{label} SKIP (K–2 / no Google needed)")
                skipped += 1
                continue

            desired_students = collect_classroom_student_emails(class_obj)
            desired_teachers = collect_classroom_teacher_emails(class_obj)

            missing_students = 0
            missing_teachers = 0
            if course_id and not args.dry_run:
                # Live sync path reports after sync; dry-run compares now.
                pass
            if course_id:
                try:
                    current_students = list_course_student_emails(course_id)
                    current_teachers = list_course_teacher_emails(course_id)
                    desired_s = {e.lower() for e in desired_students}
                    desired_t = {e.lower() for e in desired_teachers}
                    missing_students = len(desired_s - current_students)
                    missing_teachers = len(desired_t - current_teachers)
                except Exception as exc:
                    print(f"{label} WARN could not list current roster: {exc}")

            students_missing_total += missing_students
            teachers_missing_total += missing_teachers

            if args.dry_run:
                print(
                    f"{label} DRY-RUN "
                    f"clara_students={len(desired_students)} "
                    f"missing_students≈{missing_students} "
                    f"missing_teachers≈{missing_teachers}"
                    + (" (no classroom yet — would provision)" if not course_id else "")
                )
                ok += 1
                continue

            print(
                f"{label} syncing… "
                f"(clara_students={len(desired_students)}, "
                f"missing_before≈{missing_students})"
            )
            try:
                if args.also_groups:
                    if not provision_and_sync_class_google_group(cid):
                        print("  WARN Google Group sync returned False")
                if not provision_and_sync_class_google_classroom(cid):
                    print("  FAIL classroom sync returned False")
                    fail += 1
                else:
                    class_obj = Class.query.get(cid)
                    new_id = (getattr(class_obj, "google_classroom_id", None) or "").strip()
                    print(f"  OK google_classroom_id={new_id or 'NONE'}")
                    ok += 1
            except Exception as exc:
                print(f"  FAIL {exc}")
                fail += 1

            if args.sleep_ms > 0 and i < len(ids):
                time.sleep(args.sleep_ms / 1000.0)

        print(
            f"Done. ok={ok} failed={fail} skipped={skipped} "
            f"missing_students_before≈{students_missing_total} "
            f"missing_teachers_before≈{teachers_missing_total} "
            f"dry_run={args.dry_run}"
        )
        return 0 if fail == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
