#!/usr/bin/env python3
"""
Create school-managed Google Classrooms (and Groups) for grade 3+ classes
that still lack a Classroom id. K–2 are skipped (no student Workspace accounts).

Run from the Render Shell (or locally) with the same DATABASE_URL and
GOOGLE_DIRECTORY_* / Classroom env vars as the web service:

  FLASK_ENV=production python ops/backfill_class_google_classrooms.py
  FLASK_ENV=production python ops/backfill_class_google_classrooms.py --dry-run
  FLASK_ENV=production python ops/backfill_class_google_classrooms.py --school-year-id 12
  FLASK_ENV=production python ops/backfill_class_google_classrooms.py --all-years
  FLASK_ENV=production python ops/backfill_class_google_classrooms.py --sleep-ms 750

This runs synchronously (not a background thread), so it will keep going until
finished even if the web request would have timed out.
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill missing school-managed Google Classrooms for grade 3+ classes."
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
        "--dry-run",
        action="store_true",
        help="List classes that would be provisioned; do not call Google.",
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
    from services.class_google_group import (
        class_ids_needing_google_classroom,
        class_needs_google_integration,
        try_provision_class_google_group,
    )
    from services.class_google_classroom import provision_and_sync_class_google_classroom
    from services.google_classroom_admin import classroom_owner_email

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
            ids = class_ids_needing_google_classroom(year_id)
            print(f"Classes missing Google Classroom (grade 3+): {len(ids)}")

        if not ids:
            print("Nothing to do.")
            return 0

        ok = 0
        fail = 0
        skipped = 0
        for i, cid in enumerate(ids, start=1):
            class_obj = Class.query.get(cid)
            if not class_obj:
                print(f"[{i}/{len(ids)}] class_id={cid} NOT FOUND")
                fail += 1
                continue
            grades = class_obj.get_grade_levels() if hasattr(class_obj, "get_grade_levels") else []
            already = (class_obj.google_classroom_id or "").strip()
            label = (
                f"[{i}/{len(ids)}] class_id={cid} name={class_obj.name!r} "
                f"grades={grades} year={class_obj.school_year_id}"
            )
            if not class_needs_google_integration(class_obj):
                print(f"{label} SKIP (K–2 / no Google needed)")
                skipped += 1
                continue
            if already and not args.class_id:
                print(f"{label} SKIP (already linked {already})")
                skipped += 1
                continue

            if args.dry_run:
                print(f"{label} DRY-RUN would provision")
                ok += 1
                continue

            print(f"{label} provisioning…")
            try:
                # Group + Classroom (Classroom alone is also fine if Group already exists).
                try_provision_class_google_group(cid)
                class_obj = Class.query.get(cid)
                course_id = (getattr(class_obj, "google_classroom_id", None) or "").strip()
                if course_id:
                    print(f"  OK google_classroom_id={course_id}")
                    ok += 1
                else:
                    # One more direct attempt for clearer failure signal.
                    provision_and_sync_class_google_classroom(cid)
                    class_obj = Class.query.get(cid)
                    course_id = (getattr(class_obj, "google_classroom_id", None) or "").strip()
                    if course_id:
                        print(f"  OK google_classroom_id={course_id}")
                        ok += 1
                    else:
                        print("  FAIL still no google_classroom_id after provision")
                        fail += 1
            except Exception as exc:
                print(f"  FAIL {exc}")
                fail += 1

            if args.sleep_ms > 0 and i < len(ids):
                time.sleep(args.sleep_ms / 1000.0)

        print(f"Done. ok={ok} failed={fail} skipped={skipped} dry_run={args.dry_run}")
        return 0 if fail == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
