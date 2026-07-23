#!/usr/bin/env python3
"""
Enroll students into classes for a school year based on matching grade levels.

Uses the same logic as core class setup (services.school_year_class_setup.auto_enroll_students_by_grade).
Idempotent: skips students already actively enrolled in a class.

Examples:
  python scripts/backfill_class_enrollments_by_grade.py --dry-run
  python scripts/backfill_class_enrollments_by_grade.py
  python scripts/backfill_class_enrollments_by_grade.py --school-year-id 3
"""

from __future__ import annotations

import argparse
import os
import sys


def _bootstrap_path() -> None:
    if "." not in sys.path:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _preview_enrollment(class_ids: list[int], school_year_id: int) -> dict:
    from models import Class, Enrollment, Student

    enrolled_count = 0
    by_class: list[dict] = []
    skipped_no_grades: list[dict] = []

    for class_id in class_ids:
        class_obj = Class.query.get(class_id)
        if not class_obj or class_obj.school_year_id != school_year_id:
            continue
        grade_levels = class_obj.get_grade_levels() or []
        if not grade_levels:
            skipped_no_grades.append({"class_id": class_id, "class_name": class_obj.name})
            continue

        students = Student.query.filter(
            Student.grade_level.in_(grade_levels),
            Student.is_deleted.is_(False),
        ).all()

        added = 0
        for student in students:
            if student.grade_level is None:
                continue
            exists = Enrollment.query.filter_by(
                class_id=class_id,
                student_id=student.id,
                is_active=True,
            ).first()
            if exists:
                continue
            added += 1

        if added:
            enrolled_count += added
            by_class.append(
                {
                    "class_id": class_id,
                    "class_name": class_obj.name,
                    "grade_levels": grade_levels,
                    "enrolled": added,
                }
            )

    return {
        "enrolled_count": enrolled_count,
        "by_class": by_class,
        "skipped_no_grades": skipped_no_grades,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill student enrollments by grade level for school-year classes.",
    )
    parser.add_argument(
        "--school-year-id",
        type=int,
        default=None,
        help="School year to process (default: active school year).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview enrollments without writing to the database.",
    )
    parser.add_argument(
        "--include-inactive-classes",
        action="store_true",
        help="Include classes marked inactive (default: active classes only).",
    )
    args = parser.parse_args()

    _bootstrap_path()

    try:
        from app import create_app
        from config import DevelopmentConfig, ProductionConfig
    except Exception as exc:
        print(f"[ERROR] Bootstrap import failed: {exc}")
        return 1

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    config_class = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=config_class)

    from models import Class
    from services.school_year_class_setup import auto_enroll_students_by_grade
    from utils.school_year_filters import get_active_school_year

    with app.app_context():
        if args.school_year_id:
            from models import SchoolYear

            school_year = SchoolYear.query.get(args.school_year_id)
            if not school_year:
                print(f"[ERROR] School year id={args.school_year_id} not found.")
                return 1
        else:
            school_year = get_active_school_year()
            if not school_year:
                print("[ERROR] No active school year. Pass --school-year-id explicitly.")
                return 1

        class_query = Class.query.filter_by(school_year_id=school_year.id)
        if not args.include_inactive_classes:
            class_query = class_query.filter_by(is_active=True)
        classes = class_query.order_by(Class.id).all()

        class_ids = [c.id for c in classes]
        with_grades = [c for c in classes if c.get_grade_levels()]
        without_grades = [c for c in classes if not c.get_grade_levels()]

        print(f"School year: {school_year.name} (id={school_year.id})")
        print(f"Classes: {len(classes)} total, {len(with_grades)} with grade levels, {len(without_grades)} without")
        if without_grades:
            print("Skipping classes with no grade levels:")
            for c in without_grades:
                print(f"  - id={c.id} {c.name!r}")

        target_ids = [c.id for c in with_grades]
        if not target_ids:
            print("[INFO] No classes with grade levels to process.")
            return 0

        if args.dry_run:
            result = _preview_enrollment(target_ids, school_year.id)
            print(f"\n[DRY RUN] Would enroll {result['enrolled_count']} student(s) across {len(result['by_class'])} class(es).")
            for row in result["by_class"]:
                grades = ", ".join(str(g) for g in row["grade_levels"])
                print(f"  - {row['class_name']!r} (id={row['class_id']}, grades={grades}): +{row['enrolled']}")
            return 0

        result = auto_enroll_students_by_grade(target_ids, school_year.id)
        enrolled = result.get("enrolled_count", 0)
        by_class = result.get("by_class") or []

        print(f"\nEnrolled {enrolled} student(s) across {len(by_class)} class(es).")
        if by_class:
            for row in by_class:
                print(f"  - {row['class_name']!r} (id={row['class_id']}): +{row['enrolled']}")
        else:
            print("No new enrollments were needed (rosters already match grade levels).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
