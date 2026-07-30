#!/usr/bin/env python3
"""
Repair off-by-one StudentSchoolYear / report-card display grades, and optionally
promote students whose live grade_level is still stuck on a closed year's grade.

Typical production case after closing 2025-2026 without (or before) a clean
promotion:

  1) Rebuild closed-year grades from single-grade class enrollments
  2) Promote anyone still on that closed-year grade into the active year

Examples (from repo root, with DATABASE_URL / app config available):

  python ops/repair_school_year_grades.py --list-years
  python ops/repair_school_year_grades.py --closed-year 2025-2026 --dry-run
  python ops/repair_school_year_grades.py --closed-year 2025-2026
  python ops/repair_school_year_grades.py --closed-year-id 2 --promote
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


def _resolve_closed_year(args):
    from models import SchoolYear

    if args.closed_year_id:
        sy = SchoolYear.query.get(int(args.closed_year_id))
        if not sy:
            raise SystemExit(f"No school year with id={args.closed_year_id}")
        return sy
    if args.closed_year:
        name = args.closed_year.strip()
        sy = SchoolYear.query.filter_by(name=name).first()
        if not sy:
            raise SystemExit(f"No school year named {name!r}")
        return sy
    raise SystemExit("Pass --closed-year NAME or --closed-year-id ID (or --list-years).")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair historical grades and optionally promote stuck students."
    )
    parser.add_argument("--list-years", action="store_true", help="Print school years and exit.")
    parser.add_argument("--closed-year", help="Closed school year name, e.g. 2025-2026")
    parser.add_argument("--closed-year-id", type=int, help="Closed school year id")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Also promote students still on the closed-year grade into the active year.",
    )
    parser.add_argument(
        "--no-snapshots",
        action="store_true",
        help="Do not rewrite report-card student_display.grade JSON.",
    )
    parser.add_argument(
        "--inspect-student",
        type=int,
        help="Print enrollment grade signals for one student id, then exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute changes but roll back instead of committing.",
    )
    args = parser.parse_args()
    _bootstrap_path()

    from app import create_app
    from config import DevelopmentConfig, ProductionConfig

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    config_class = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=config_class)
    with app.app_context():
        from models import Class, Enrollment, SchoolYear, Student, StudentSchoolYear
        from utils.report_card_school_year import (
            _grade_from_year_enrollments,
            _grades_from_class_name,
            grade_level_for_school_year,
            promote_students_still_on_prior_year_grade,
            repair_student_school_year_grades,
        )

        if args.list_years:
            years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
            for sy in years:
                flag = "active" if sy.is_active else "closed"
                print(f"  id={sy.id}  {sy.name}  ({flag})")
            return 0

        if args.inspect_student:
            student = Student.query.get(args.inspect_student)
            if not student:
                raise SystemExit(f"No student id={args.inspect_student}")
            print(
                f"Student {student.id} {student.first_name} {student.last_name} "
                f"live_grade={student.grade_level}"
            )
            years = SchoolYear.query.order_by(SchoolYear.name).all()
            for sy in years:
                inferred = _grade_from_year_enrollments(student.id, sy.id)
                resolved = grade_level_for_school_year(student, sy)
                ssy = StudentSchoolYear.query.filter_by(
                    student_id=student.id, school_year_id=sy.id
                ).first()
                print(
                    f"\n{sy.name} (id={sy.id}, {'active' if sy.is_active else 'closed'}): "
                    f"inferred={inferred} resolved={resolved} "
                    f"ssy={ssy.grade_level if ssy else None}"
                )
                classes = (
                    Class.query.join(Enrollment, Enrollment.class_id == Class.id)
                    .filter(
                        Enrollment.student_id == student.id,
                        Class.school_year_id == sy.id,
                    )
                    .all()
                )
                for class_obj in classes:
                    levels = class_obj.get_grade_levels() if hasattr(class_obj, "get_grade_levels") else []
                    print(
                        f"  - {class_obj.name!r} grade_levels={levels} "
                        f"name_grades={_grades_from_class_name(class_obj.name)}"
                    )
            return 0

        closed = _resolve_closed_year(args)
        if closed.is_active:
            raise SystemExit(
                f"{closed.name} is still active. Pass the closed year (e.g. 2025-2026)."
            )

        repair = repair_student_school_year_grades(
            closed.id,
            fix_report_card_snapshots=not args.no_snapshots,
            commit=False,
        )
        print("Repair StudentSchoolYear / report-card snapshots:")
        print(json.dumps(repair, indent=2))

        promo = None
        if args.promote:
            promo = promote_students_still_on_prior_year_grade(closed.id, commit=False)
            print("Promote students still on closed-year grade:")
            print(json.dumps(promo, indent=2))

        from extensions import db

        if args.dry_run:
            db.session.rollback()
            print("Dry run — rolled back; no changes saved.")
        else:
            db.session.commit()
            print("Committed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
