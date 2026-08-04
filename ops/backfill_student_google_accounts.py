#!/usr/bin/env python3
"""
Create missing Google Workspace accounts for grade 3+ students who already have
a portal User + google_workspace_email in Clara but no Directory user yet.

Run from Render Shell (same DATABASE_URL + GOOGLE_DIRECTORY_* as the web service):

  FLASK_ENV=production python ops/backfill_student_google_accounts.py --dry-run
  FLASK_ENV=production python ops/backfill_student_google_accounts.py
  FLASK_ENV=production python ops/backfill_student_google_accounts.py --sleep-ms 500
  FLASK_ENV=production python ops/backfill_student_google_accounts.py --student-id 42

K–2 are skipped (policy: no school email until 3rd grade).
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill missing Google Workspace accounts for grade 3+ students."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep-ms", type=int, default=400)
    parser.add_argument("--student-id", type=int, action="append", default=[])
    parser.add_argument(
        "--also-fill-email",
        action="store_true",
        help="If User exists but google_workspace_email is blank, generate and save it first.",
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

    from extensions import db
    from models import Student, User
    from services.google_directory_service import get_directory_service, get_google_user
    from services.google_sync_tasks import sync_single_user_to_google
    from utils.google_workspace_passwords import new_google_workspace_initial_password
    from utils.student_login_policy import grade_may_have_login

    def _fill_workspace_email(student: Student, user: User) -> bool:
        if (user.google_workspace_email or "").strip():
            return False
        if not grade_may_have_login(student.grade_level):
            return False
        generated = student.generate_email()
        if not generated:
            return False
        user.google_workspace_email = generated
        if not (student.email or "").strip():
            student.email = generated
        if not (user.email or "").strip():
            user.email = generated
        return True

    with app.app_context():
        if not get_directory_service():
            print("[ERROR] Directory service unavailable — check GOOGLE_DIRECTORY_* env vars.")
            return 2

        q = (
            db.session.query(User)
            .join(Student, Student.id == User.student_id)
            .filter(
                User.student_id.isnot(None),
                Student.is_deleted.is_(False),
            )
            .order_by(Student.id)
        )
        if args.student_id:
            q = q.filter(Student.id.in_([int(x) for x in args.student_id]))

        rows = q.all()
        print(f"Scanning {len(rows)} student portal user(s)…")

        candidates: list[tuple[User, Student]] = []
        for user in rows:
            student = db.session.get(Student, user.student_id)
            if not student:
                continue
            if not grade_may_have_login(student.grade_level):
                continue
            email = (user.google_workspace_email or "").strip()
            if not email and args.also_fill_email:
                if _fill_workspace_email(student, user):
                    db.session.commit()
                    email = (user.google_workspace_email or "").strip()
                    print(
                        f"  filled email for student_id={student.id} "
                        f"{student.first_name} {student.last_name} -> {email}"
                    )
            if not email:
                continue
            existing = get_google_user(email, quiet_404=True)
            if existing:
                continue
            candidates.append((user, student))

        print(f"Missing in Google Directory: {len(candidates)}")
        if not candidates:
            print("Nothing to do.")
            return 0

        ok = 0
        fail = 0
        for i, (user, student) in enumerate(candidates, start=1):
            email = (user.google_workspace_email or "").strip()
            label = (
                f"[{i}/{len(candidates)}] student_id={student.id} "
                f"name={student.first_name!r} {student.last_name!r} "
                f"grade={student.grade_level} email={email}"
            )
            if args.dry_run:
                print(f"{label} DRY-RUN would create")
                ok += 1
                continue
            print(f"{label} creating…")
            try:
                pw = new_google_workspace_initial_password()
                sync_single_user_to_google(user.id, initial_google_password=pw)
                if get_google_user(email, quiet_404=True):
                    print(f"  OK {email}")
                    ok += 1
                else:
                    print("  FAIL still missing in Directory after sync")
                    fail += 1
            except Exception as exc:
                print(f"  FAIL {exc}")
                fail += 1
            if args.sleep_ms > 0 and i < len(candidates):
                time.sleep(args.sleep_ms / 1000.0)

        print(f"Done. ok={ok} failed={fail} dry_run={args.dry_run}")
        return 0 if fail == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
