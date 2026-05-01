#!/usr/bin/env python3
"""
Maintenance script: sync all records to Google Workspace Directory.

Behavior:
- Students:
  - Ensure Google account exists for User.google_workspace_email (create if missing)
  - Ensure OU matches policy derived from grade_level + grad_year (and removal/alumni rules)
  - Ensure membership in grad-year group (e.g., 2030@clarascienceacademy.org)
- Staff:
  - Ensure Google account exists for User.google_workspace_email (create if missing)
  - Ensure OU is /Staff
  - Ensure membership in teachers@clarascienceacademy.org

Dry run:
  Default is DRY RUN (prints actions). To apply changes set APPLY_CHANGES=1.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import Optional, Tuple


DEFAULT_TEMP_PASSWORD = "Welcome2CSA!"
DOMAIN = "clarascienceacademy.org"
TEACHERS_GROUP_EMAIL = f"teachers@{DOMAIN}"
ELEMENTARY_GROUP_EMAIL = f"elementary@{DOMAIN}"
MIDDLE_SCHOOL_GROUP_EMAIL = f"middle_school@{DOMAIN}"
HIGH_SCHOOL_GROUP_EMAIL = f"highschool@{DOMAIN}"
STUDENT_ASSEMBLY_GROUP_EMAIL = f"studentassembly@{DOMAIN}"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int((os.environ.get(name, "") or "").strip() or default)
    except Exception:
        return default


def _sleep_ms(ms: int) -> None:
    if ms and ms > 0:
        time.sleep(ms / 1000.0)


def _grad_year_group_email(grad_year: Optional[int]) -> Optional[str]:
    if not grad_year:
        return None
    try:
        y = int(grad_year)
    except Exception:
        return None
    return f"{y}@{DOMAIN}"


def main() -> int:
    # Ensure repo root is on sys.path when running from scripts/
    if "." not in sys.path:
        sys.path.append(".")

    apply_changes = _env_bool("APPLY_CHANGES", default=False)
    create_missing_groups = _env_bool("CREATE_MISSING_GROUPS", default=False)
    sleep_ms = _env_int("SLEEP_MS", 50)
    max_students = _env_int("MAX_STUDENTS", 0)  # 0 = all
    max_staff = _env_int("MAX_STAFF", 0)  # 0 = all

    print("=" * 80)
    print("SYNC ALL TO GOOGLE")
    print("=" * 80)
    print(f"Mode: {'APPLY' if apply_changes else 'DRY RUN'}")
    print(
        f"SLEEP_MS={sleep_ms} MAX_STUDENTS={max_students or 'ALL'} MAX_STAFF={max_staff or 'ALL'} "
        f"CREATE_MISSING_GROUPS={'1' if create_missing_groups else '0'}"
    )
    print("=" * 80)

    try:
        from app import create_app
        from config import DevelopmentConfig
    except Exception as e:
        print(f"[ERROR] Failed to import app bootstrap: {e}")
        return 1

    try:
        from extensions import db
        from models import Student, TeacherStaff, User
        from services.google_directory_service import (
            create_google_group,
            create_google_user,
            ensure_user_in_group,
            get_google_group,
            get_google_user,
            move_user_to_ou,
            sync_user_groups,
        )
        from services.google_ou_policy import resolve_student_ou, school_level_group_for_grade
    except Exception as e:
        print(f"[ERROR] Failed to import required modules: {e}")
        return 1

    app = create_app(config_class=DevelopmentConfig)

    created_users = 0
    moved_ous = 0
    group_adds = 0
    errors = 0

    with app.app_context():
        # ------------------------
        # Students
        # ------------------------
        student_q = (
            db.session.query(Student, User.google_workspace_email)
            .join(User, User.student_id == Student.id)
            .filter(
                Student.is_deleted == False,
                Student.is_active == True,
                User.google_workspace_email.isnot(None),
            )
            .order_by(Student.last_name, Student.first_name)
        )
        if max_students:
            student_q = student_q.limit(max_students)
        student_rows = student_q.all()

        print(f"\n[Students] Found {len(student_rows)} active student(s) with Workspace emails.")

        for student, ws_email in student_rows:
            ws_email = (ws_email or "").strip()
            if not ws_email:
                continue

            # Compute desired OU (uses grade + grad_year + alumni/removal rules)
            decision = resolve_student_ou(
                grade_level=getattr(student, "grade_level", None),
                grad_year=getattr(student, "grad_year", None),
                expected_grad_date=getattr(student, "expected_grad_date", None),
                is_active=bool(getattr(student, "is_active", True)),
                marked_for_removal=bool(getattr(student, "marked_for_removal", False)),
                status_updated_at=getattr(student, "status_updated_at", None),
            )

            g_user = get_google_user(ws_email)
            _sleep_ms(sleep_ms)

            if not g_user:
                # Auto-create missing account
                if apply_changes:
                    created = create_google_user(
                        {
                            "primaryEmail": ws_email,
                            "name": {"givenName": student.first_name, "familyName": student.last_name},
                            "password": DEFAULT_TEMP_PASSWORD,
                            "orgUnitPath": decision.target_ou_path,
                            "changePasswordAtNextLogin": True,
                        }
                    )
                    _sleep_ms(sleep_ms)
                    if created:
                        created_users += 1
                        print(f"[CREATE] student {ws_email} in OU {decision.target_ou_path}")
                    else:
                        errors += 1
                        print(f"[ERROR] failed to create student {ws_email}")
                        continue
                else:
                    print(f"[DRY] would create student {ws_email} in OU {decision.target_ou_path}")
                    continue
            else:
                current_ou = g_user.get("orgUnitPath")
                if current_ou != decision.target_ou_path:
                    if apply_changes:
                        if move_user_to_ou(ws_email, decision.target_ou_path):
                            moved_ous += 1
                            print(f"[MOVE] student {ws_email}: {current_ou} -> {decision.target_ou_path}")
                        else:
                            errors += 1
                            print(f"[ERROR] failed OU move for student {ws_email}")
                        _sleep_ms(sleep_ms)
                    else:
                        print(f"[DRY] would move student {ws_email}: {current_ou} -> {decision.target_ou_path}")

            # Graduation-year group membership (add-only)
            grad_group = _grad_year_group_email(getattr(student, "grad_year", None))
            if grad_group:
                if apply_changes:
                    if create_missing_groups and not get_google_group(grad_group):
                        create_google_group(
                            grad_group,
                            name=f"Class of {getattr(student, 'grad_year', '')}".strip() or grad_group,
                            description="Auto-created by CSA sync to support filtering/group email.",
                        )
                        _sleep_ms(sleep_ms)
                    if ensure_user_in_group(ws_email, grad_group):
                        group_adds += 1
                        print(f"[GROUP] ensured {ws_email} in {grad_group}")
                    else:
                        errors += 1
                        print(f"[ERROR] failed ensuring {ws_email} in {grad_group}")
                    _sleep_ms(sleep_ms)
                else:
                    print(f"[DRY] would ensure {ws_email} in {grad_group}")

            # School-level groups: exactly one of Elementary/Middle/High + Student Assembly for all active students
            level_key = school_level_group_for_grade(getattr(student, "grade_level", None))
            level_email = None
            if level_key == "elementary":
                level_email = ELEMENTARY_GROUP_EMAIL
            elif level_key == "middle_school":
                level_email = MIDDLE_SCHOOL_GROUP_EMAIL
            elif level_key == "highschool":
                level_email = HIGH_SCHOOL_GROUP_EMAIL

            desired_school_groups = [STUDENT_ASSEMBLY_GROUP_EMAIL]
            if level_email:
                desired_school_groups.insert(0, level_email)

            if apply_changes:
                if create_missing_groups:
                    for g in desired_school_groups:
                        if not get_google_group(g):
                            create_google_group(
                                g,
                                name=g.split("@", 1)[0].replace("_", " ").title(),
                                description="Auto-created by CSA sync.",
                            )
                            _sleep_ms(sleep_ms)

                if sync_user_groups(ws_email, desired_school_groups):
                    group_adds += 1
                    print(f"[GROUP] synced school-level groups for {ws_email} -> {', '.join(desired_school_groups)}")
                else:
                    errors += 1
                    print(f"[ERROR] failed syncing school-level groups for {ws_email}")
                _sleep_ms(sleep_ms)
            else:
                print(f"[DRY] would sync school-level groups for {ws_email} -> {', '.join(desired_school_groups)}")

        # ------------------------
        # Staff (Teachers/Staff)
        # ------------------------
        staff_q = (
            db.session.query(TeacherStaff, User.google_workspace_email)
            .join(User, User.teacher_staff_id == TeacherStaff.id)
            .filter(User.google_workspace_email.isnot(None))
            .order_by(TeacherStaff.last_name, TeacherStaff.first_name)
        )
        if max_staff:
            staff_q = staff_q.limit(max_staff)
        staff_rows = staff_q.all()

        print(f"\n[Staff] Found {len(staff_rows)} staff member(s) with Workspace emails.")

        for staff, ws_email in staff_rows:
            ws_email = (ws_email or "").strip()
            if not ws_email:
                continue

            g_user = get_google_user(ws_email)
            _sleep_ms(sleep_ms)

            if not g_user:
                if apply_changes:
                    created = create_google_user(
                        {
                            "primaryEmail": ws_email,
                            "name": {"givenName": staff.first_name, "familyName": staff.last_name},
                            "password": DEFAULT_TEMP_PASSWORD,
                            "orgUnitPath": "/Staff",
                            "changePasswordAtNextLogin": True,
                        }
                    )
                    _sleep_ms(sleep_ms)
                    if created:
                        created_users += 1
                        print(f"[CREATE] staff {ws_email} in OU /Staff")
                    else:
                        errors += 1
                        print(f"[ERROR] failed to create staff {ws_email}")
                        continue
                else:
                    print(f"[DRY] would create staff {ws_email} in OU /Staff")
                    continue
            else:
                current_ou = g_user.get("orgUnitPath")
                if current_ou != "/Staff":
                    if apply_changes:
                        if move_user_to_ou(ws_email, "/Staff"):
                            moved_ous += 1
                            print(f"[MOVE] staff {ws_email}: {current_ou} -> /Staff")
                        else:
                            errors += 1
                            print(f"[ERROR] failed OU move for staff {ws_email}")
                        _sleep_ms(sleep_ms)
                    else:
                        print(f"[DRY] would move staff {ws_email}: {current_ou} -> /Staff")

            if apply_changes:
                if create_missing_groups and not get_google_group(TEACHERS_GROUP_EMAIL):
                    create_google_group(
                        TEACHERS_GROUP_EMAIL,
                        name="Teachers",
                        description="Auto-created by CSA sync.",
                    )
                    _sleep_ms(sleep_ms)
                if ensure_user_in_group(ws_email, TEACHERS_GROUP_EMAIL):
                    group_adds += 1
                    print(f"[GROUP] ensured {ws_email} in {TEACHERS_GROUP_EMAIL}")
                else:
                    errors += 1
                    print(f"[ERROR] failed ensuring {ws_email} in {TEACHERS_GROUP_EMAIL}")
                _sleep_ms(sleep_ms)
            else:
                print(f"[DRY] would ensure {ws_email} in {TEACHERS_GROUP_EMAIL}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"created_users={created_users}")
    print(f"moved_ous={moved_ous}")
    print(f"group_ensures={group_adds}")
    print(f"errors={errors}")
    print("=" * 80)
    if not apply_changes:
        print("DRY RUN completed. Set APPLY_CHANGES=1 to perform changes.")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

