#!/usr/bin/env python3
"""
Fix student core-class rosters + re-issue / email temporary student logins.

1) Enroll students into matching core classes for the active school year
   (covers kids added after core setup).
2) Align existing core enrollments to each student's *current* grade
   (covers mid-year grade changes).
3) Re-issue website temporary passwords for grade 3+ students who still have
   ``is_temporary_password=True``, optionally reset their Google password, and
   email Directors / School Administrators a digest.

Run on Render Shell:

  FLASK_ENV=production python ops/fix_student_core_enrollments_and_temp_creds.py --dry-run
  FLASK_ENV=production python ops/fix_student_core_enrollments_and_temp_creds.py
  FLASK_ENV=production python ops/fix_student_core_enrollments_and_temp_creds.py --enroll-only
  FLASK_ENV=production python ops/fix_student_core_enrollments_and_temp_creds.py --creds-only
  FLASK_ENV=production python ops/fix_student_core_enrollments_and_temp_creds.py --no-google-password-reset
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill core enrollments, align grades, re-issue student temp logins."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--enroll-only", action="store_true", help="Skip credential re-issue/email.")
    parser.add_argument("--creds-only", action="store_true", help="Skip enrollment / grade align.")
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Re-issue passwords but do not email admins.",
    )
    parser.add_argument(
        "--no-google-password-reset",
        action="store_true",
        help="Only reset website passwords; leave Google passwords alone.",
    )
    parser.add_argument("--student-id", type=int, action="append", default=[])
    parser.add_argument("--school-year-id", type=int, default=None)
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

    from extensions import db
    from models import Class, Enrollment, SchoolYear, Student, User
    from services.email_service import notify_school_admins_student_credentials_digest
    from services.google_directory_service import get_google_user, set_google_user_password
    from services.school_year_class_setup import (
        align_student_core_enrollments_to_current_grade,
        auto_enroll_students_by_grade,
    )
    from utils.google_workspace_passwords import new_google_workspace_initial_password
    from utils.student_login_policy import grade_may_have_login
    from utils.temporary_passwords import generate_temporary_password
    from werkzeug.security import generate_password_hash

    with app.app_context():
        if args.school_year_id:
            school_year = db.session.get(SchoolYear, args.school_year_id)
        else:
            school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not school_year:
            print("[ERROR] No school year found.")
            return 1

        print(f"School year: {school_year.name} (id={school_year.id})")
        print(f"Mode: dry_run={args.dry_run} enroll_only={args.enroll_only} creds_only={args.creds_only}")

        # -------- Enrollment / grade align --------
        if not args.creds_only:
            classes = (
                Class.query.filter_by(school_year_id=school_year.id, is_active=True)
                .order_by(Class.id)
                .all()
            )
            with_grades = [c for c in classes if c.get_grade_levels()]
            print(f"\n[Enroll] {len(with_grades)} active class(es) with grade levels")

            if args.dry_run:
                would_add = 0
                for c in with_grades:
                    levels = c.get_grade_levels() or []
                    students = Student.query.filter(
                        Student.grade_level.in_(levels),
                        Student.is_deleted.is_(False),
                    ).all()
                    if args.student_id:
                        students = [s for s in students if s.id in set(args.student_id)]
                    for s in students:
                        if Enrollment.query.filter_by(
                            class_id=c.id, student_id=s.id, is_active=True
                        ).first():
                            continue
                        would_add += 1
                print(f"[DRY RUN] Would add ~{would_add} missing grade-matched enrollment(s)")
            else:
                result = auto_enroll_students_by_grade(
                    [c.id for c in with_grades], school_year.id
                )
                print(
                    f"Enrolled {result.get('enrolled_count', 0)} student(s) "
                    f"across {len(result.get('by_class') or [])} class(es)"
                )

            # Align every active student (or filtered) to current-grade cores.
            sq = Student.query.filter(Student.is_deleted.is_(False)).order_by(Student.id)
            if args.student_id:
                sq = sq.filter(Student.id.in_([int(x) for x in args.student_id]))
            students = sq.all()
            aligned = 0
            dropped_n = 0
            enrolled_n = 0
            missing_notes: list[str] = []
            for student in students:
                if student.grade_level is None:
                    continue
                if args.dry_run:
                    # Preview via real function against a savepoint? Skip writes — use align
                    # only when not dry-run. For dry-run, call and rollback.
                    db.session.begin_nested()
                    try:
                        info = align_student_core_enrollments_to_current_grade(
                            student, school_year_id=school_year.id
                        )
                        if not info.get("skipped") and (
                            info.get("dropped") or info.get("enrolled")
                        ):
                            aligned += 1
                            dropped_n += len(info.get("dropped") or [])
                            enrolled_n += len(info.get("enrolled") or [])
                        for name in info.get("missing_classes") or []:
                            missing_notes.append(
                                f"student_id={student.id} grade={student.grade_level} missing {name}"
                            )
                    finally:
                        db.session.rollback()
                else:
                    info = align_student_core_enrollments_to_current_grade(
                        student, school_year_id=school_year.id
                    )
                    if not info.get("skipped") and (
                        info.get("dropped") or info.get("enrolled")
                    ):
                        aligned += 1
                        dropped_n += len(info.get("dropped") or [])
                        enrolled_n += len(info.get("enrolled") or [])
                        print(
                            f"  aligned student_id={student.id} "
                            f"{student.first_name} {student.last_name} "
                            f"grade={student.grade_level} "
                            f"dropped={len(info.get('dropped') or [])} "
                            f"enrolled={len(info.get('enrolled') or [])}"
                        )
                    for name in info.get("missing_classes") or []:
                        missing_notes.append(
                            f"student_id={student.id} grade={student.grade_level} missing {name}"
                        )
            if not args.dry_run:
                db.session.commit()
            print(
                f"[Align] students_changed={aligned} drops={dropped_n} adds={enrolled_n} "
                f"dry_run={args.dry_run}"
            )
            if missing_notes:
                uniq = sorted(set(missing_notes))[:40]
                print(f"[Align] missing core classes ({len(set(missing_notes))} note(s)):")
                for line in uniq:
                    print(f"  - {line}")

        # -------- Temp credentials --------
        if args.enroll_only:
            print("\nDone (enroll-only).")
            return 0

        print("\n[Creds] Scanning grade 3+ users with temporary portal passwords…")
        q = (
            db.session.query(User)
            .join(Student, Student.id == User.student_id)
            .filter(
                User.student_id.isnot(None),
                User.is_temporary_password.is_(True),
                Student.is_deleted.is_(False),
            )
            .order_by(Student.id)
        )
        if args.student_id:
            q = q.filter(Student.id.in_([int(x) for x in args.student_id]))
        users = q.all()

        cred_rows: list[dict] = []
        for user in users:
            student = db.session.get(Student, user.student_id)
            if not student or not grade_may_have_login(student.grade_level):
                continue
            school_email = (user.google_workspace_email or "").strip() or None
            portal_pw = generate_temporary_password(12)
            google_pw = None
            google_reset_ok = None

            if args.dry_run:
                print(
                    f"  DRY-RUN would re-issue student_id={student.id} "
                    f"{student.first_name} {student.last_name} "
                    f"user={user.username} email={school_email or '—'}"
                )
                cred_rows.append(
                    {
                        "student_name": f"{student.first_name} {student.last_name}".strip(),
                        "student_id": student.student_id or str(student.id),
                        "grade_level": student.grade_level,
                        "username": user.username,
                        "portal_password": "(new temp)",
                        "school_email": school_email,
                        "google_initial_password": (
                            "(new temp)" if not args.no_google_password_reset and school_email else None
                        ),
                    }
                )
                continue

            user.password_hash = generate_password_hash(portal_pw)
            user.is_temporary_password = True
            user.password_changed_at = None

            if school_email and not args.no_google_password_reset:
                google_pw = new_google_workspace_initial_password()
                # Only reset if the Google account exists.
                if get_google_user(school_email, quiet_404=True):
                    google_reset_ok = set_google_user_password(school_email, google_pw)
                    if not google_reset_ok:
                        google_pw = None
                else:
                    google_reset_ok = False
                    google_pw = None

            cred_rows.append(
                {
                    "student_name": f"{student.first_name} {student.last_name}".strip(),
                    "student_id": student.student_id or str(student.id),
                    "grade_level": student.grade_level,
                    "username": user.username,
                    "portal_password": portal_pw,
                    "school_email": school_email,
                    "google_initial_password": google_pw,
                }
            )
            print(
                f"  re-issued student_id={student.id} user={user.username} "
                f"google_reset={google_reset_ok}"
            )

        if not args.dry_run and cred_rows:
            db.session.commit()

        print(f"[Creds] {len(cred_rows)} student(s) with temporary passwords")

        if args.dry_run:
            print("[DRY RUN] Would email admins a digest (skipped).")
            return 0

        if not cred_rows:
            print("No temporary-password students to email.")
            return 0

        if args.no_email:
            print("Skipping admin email (--no-email). Passwords were re-issued in DB.")
            return 0

        sent = notify_school_admins_student_credentials_digest(
            cred_rows,
            context_note=(
                "Ops backfill: temporary passwords re-issued because prior admins "
                "did not retain the originals. Share securely with families."
            ),
        )
        print(f"[Creds] Admin digest emailed to {sent} recipient(s).")
        return 0 if sent > 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
