#!/usr/bin/env python3
"""
Maintenance script: sync all records to Google Workspace Directory.

Behavior:
- Students (grade 3+ only; K–2 are skipped — no Directory sync):
  - Only rows where User.google_workspace_email is already set in the database
  - Ensure Google account exists for that email (create if missing)
  - Ensure OU matches policy (active division OUs, Alumni/{Elementary|Middle|High}, or Transferred & Removed).
    Cohort folders are Org Units only (e.g. ``/Students/High School/Class of 2030``), not Google Groups named ``2030@…``.
- Staff:
  - Ensure Google account exists for User.google_workspace_email (create if missing)
  - Ensure OU under ``/Staff/<…>`` subfolders including Terminated & Removed, Administrator, … (see get_staff_ou_path)
  - Ensure missing OUs exist (ensure_ou_exists) before create/move
  - Ensure membership in teachers@clarascienceacademy.org

Dry run:
  Default is DRY RUN (prints actions). To apply changes set APPLY_CHANGES=1.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

# Repo root must be on sys.path before local imports (Render cron cwd may not be project root).
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils.google_workspace_passwords import google_workspace_initial_password_for_sync
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


def main() -> int:
    """
    Run bulk Workspace sync. Return value is ignored when run as __main__; the process always
    ends with sys.exit(0) so Render Cron stays green. Check logs / summary['errors'] for issues.
    """
    import logging

    # Google's Regional Access Boundary lookup can log transient 500 INTERNAL warnings while
    # retrying token refresh; the client retries automatically and sync usually succeeds.
    for _logger_name in ("google.oauth2._client", "google.auth", "google.auth.transport.requests"):
        logging.getLogger(_logger_name).setLevel(logging.ERROR)

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
    except Exception as e:
        print(f"[ERROR] Failed to import app bootstrap: {e}")
        return 0

    config_name = (os.environ.get("FLASK_ENV", "development") or "development").lower()
    if config_name == "production":
        from config import ProductionConfig as ConfigClass
    else:
        from config import DevelopmentConfig as ConfigClass

    print(f"FLASK_ENV={config_name} config={ConfigClass.__name__}")

    try:
        from extensions import db
        from models import Student, TeacherStaff, User
        from utils.student_login_policy import (
            google_workspace_sync_should_skip_student,
            parse_grade_level_for_policy,
        )
        from services.google_directory_service import (
            create_google_group,
            create_google_user,
            ensure_ou_exists,
            ensure_user_in_group,
            get_google_group,
            get_google_user,
            move_user_to_ou,
            suspend_user,
            sync_user_groups,
        )
        from services.google_ou_policy import (
            STAFF_OU_TERMINATED_REMOVED,
            get_staff_ou_path,
            resolve_student_ou,
            school_level_group_for_grade,
            staff_google_account_eligible,
            sync_staff_google_suspension,
            sync_student_google_suspension,
        )
    except Exception as e:
        print(f"[ERROR] Failed to import required modules: {e}")
        return 0

    app = create_app(config_class=ConfigClass)

    created_users = 0
    moved_ous = 0
    group_adds = 0
    errors = 0

    with app.app_context():
        db_uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
        if db_uri:
            # Log host/db only — never print credentials.
            db_target = db_uri.split("@")[-1].split("?")[0] if "@" in db_uri else "(local sqlite)"
            print(f"Database source: {db_target} (live app DB — not hardcoded file data)")
        else:
            print("Database source: (SQLALCHEMY_DATABASE_URI not set)")

        # ------------------------
        # Students: must have User row with non-empty google_workspace_email (no guessed emails)
        # ------------------------
        student_q = (
            db.session.query(Student, User)
            .join(User, User.student_id == Student.id)
            .filter(User.google_workspace_email.isnot(None))
            .filter(User.google_workspace_email != "")
            .order_by(Student.last_name, Student.first_name)
        )
        if max_students:
            student_q = student_q.limit(max_students)
        student_rows = student_q.all()

        print(
            f"\n[Students] {len(student_rows)} row(s) with User.google_workspace_email set "
            "(includes inactive/deleted for Alumni / Transferred & Removed OU moves when grade >= 3)."
        )

        for student, u in student_rows:
            email = (u.google_workspace_email or "").strip()
            if not email:
                continue

            if google_workspace_sync_should_skip_student(getattr(student, "grade_level", None)):
                gl = parse_grade_level_for_policy(getattr(student, "grade_level", None))
                print(
                    f"[INFO] Grade Gate: Skipping {(student.first_name or '').strip()} "
                    f"{(student.last_name or '').strip()} (Grade {gl})."
                )
                continue

            print(f"[DEBUG] Syncing database record for: {email}")

            db_active = bool(getattr(student, "is_active", True))
            marked_for_removal = bool(getattr(student, "marked_for_removal", False))
            is_deleted = bool(getattr(student, "is_deleted", False))

            decision = resolve_student_ou(
                grade_level=getattr(student, "grade_level", None),
                grad_year=getattr(student, "grad_year", None),
                expected_grad_date=getattr(student, "expected_grad_date", None),
                is_active=db_active,
                marked_for_removal=marked_for_removal,
                is_deleted=is_deleted,
                status_updated_at=getattr(student, "status_updated_at", None),
                expected_graduation_year=getattr(student, "expected_graduation_year", None),
            )

            if apply_changes:
                sync_student_google_suspension(
                    email,
                    decision=decision,
                    is_active=db_active,
                    marked_for_removal=marked_for_removal,
                    is_deleted=is_deleted,
                )
                _sleep_ms(sleep_ms)

            g_user = get_google_user(email)
            _sleep_ms(sleep_ms)

            if not g_user:
                if db_active and not marked_for_removal and not is_deleted:
                    if apply_changes:
                        if not ensure_ou_exists(decision.target_ou_path):
                            errors += 1
                            print(f"[ERROR] could not ensure OU for student {email}: {decision.target_ou_path}")
                            continue
                        created = create_google_user(
                            {
                                "primaryEmail": email,
                                "name": {"givenName": student.first_name, "familyName": student.last_name},
                                "password": google_workspace_initial_password_for_sync(),
                                "orgUnitPath": decision.target_ou_path,
                                "changePasswordAtNextLogin": True,
                            }
                        )
                        _sleep_ms(sleep_ms)
                        if created:
                            created_users += 1
                            print(f"[CREATE] student {email} in OU {decision.target_ou_path}")
                        else:
                            errors += 1
                            print(f"[ERROR] failed to create student {email}")
                    else:
                        print(f"[DRY] would create student {email} in OU {decision.target_ou_path}")
                continue
            else:
                if apply_changes and decision.reason in (
                    "alumni_completed_level",
                    "transferred_removed",
                ) and not getattr(student, "status_updated_at", None):
                    from datetime import datetime

                    try:
                        student.status_updated_at = datetime.utcnow()
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

                current_ou = g_user.get("orgUnitPath")
                if current_ou != decision.target_ou_path:
                    if apply_changes:
                        ou_res = move_user_to_ou(email, decision.target_ou_path)
                        if ou_res is True:
                            moved_ous += 1
                            print(f"[MOVE] student {email}: {current_ou} -> {decision.target_ou_path}")
                        elif ou_res is False:
                            errors += 1
                            print(f"[ERROR] failed OU move for student {email}")
                        else:
                            print(f"[INFO] Skipping protected/admin user: {email}")
                        _sleep_ms(sleep_ms)
                    else:
                        print(f"[DRY] would move student {email}: {current_ou} -> {decision.target_ou_path}")

                if apply_changes and decision.should_suspend_now and not bool(g_user.get("suspended", False)):
                    if suspend_user(email):
                        print(f"[SUSPEND] student {email} ({decision.reason})")
                    else:
                        errors += 1
                        print(f"[ERROR] failed to suspend student {email}")
                    _sleep_ms(sleep_ms)

            # School-level groups: exactly one of Elementary/Middle/High + Student Assembly for active students
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

            if db_active and not marked_for_removal and not is_deleted:
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

                    sg_res = sync_user_groups(email, desired_school_groups)
                    if sg_res is True:
                        group_adds += 1
                        print(f"[GROUP] synced school-level groups for {email} -> {', '.join(desired_school_groups)}")
                    elif sg_res is False:
                        errors += 1
                        print(f"[ERROR] failed syncing school-level groups for {email}")
                    else:
                        print(f"[INFO] Skipping protected/admin user: {email}")
                    _sleep_ms(sleep_ms)
                else:
                    print(f"[DRY] would sync school-level groups for {email} -> {', '.join(desired_school_groups)}")

        # ------------------------
        # Staff (Teachers/Staff)
        # ------------------------
        # Include soft-deleted / inactive rows so Directory OU can be moved to Terminated & Removed.
        staff_q = TeacherStaff.query.order_by(TeacherStaff.last_name, TeacherStaff.first_name)
        if max_staff:
            staff_q = staff_q.limit(max_staff)
        staff_list = staff_q.all()

        user_by_teacher_id: dict = {}
        if staff_list:
            tids = [t.id for t in staff_list]
            for u in User.query.filter(User.teacher_staff_id.in_(tids)).all():
                if u.teacher_staff_id is not None:
                    user_by_teacher_id[u.teacher_staff_id] = u

        print(
            f"\n[Staff] {len(staff_list)} row(s) from TeacherStaff (all retention states; Directory OU from get_staff_ou_path)."
        )

        for staff in staff_list:
            u = user_by_teacher_id.get(staff.id)
            email = (u.google_workspace_email or "").strip() if u else ""
            if not email:
                continue

            # Staff OU tiers require TeacherStaff + linked User (u may be None if no login row).
            target_staff_ou = get_staff_ou_path(staff, u)

            print(
                f"[DEBUG] Syncing staff id={staff.id} "
                f"{(staff.first_name or '').strip()} {(staff.last_name or '').strip()} "
                f"(deleted={bool(getattr(staff, 'is_deleted', False))}, "
                f"employment={getattr(staff, 'employment_status', None)}, "
                f"portal_login={getattr(staff, 'portal_login', None)}): "
                f"{email} (staff OU -> {target_staff_ou})"
            )

            if not staff_google_account_eligible(staff):
                if apply_changes:
                    sync_staff_google_suspension(email, staff)
                    _sleep_ms(sleep_ms)
                print(
                    f"[SKIP] {email} — not eligible for active Directory sync "
                    "(removed, inactive, or portal login off). Suspended if account exists."
                )
                continue

            if apply_changes:
                sync_staff_google_suspension(email, staff)
                _sleep_ms(sleep_ms)

            g_user = get_google_user(email)
            _sleep_ms(sleep_ms)

            if not g_user:
                if apply_changes:
                    if not staff_google_account_eligible(staff):
                        print(f"[SKIP] would not create Workspace account for ineligible staff {email}")
                        continue
                    if not ensure_ou_exists(target_staff_ou):
                        errors += 1
                        print(f"[ERROR] could not ensure OU exists for staff {email}: {target_staff_ou}")
                        continue
                    created = create_google_user(
                        {
                            "primaryEmail": email,
                            "name": {"givenName": staff.first_name, "familyName": staff.last_name},
                            "password": google_workspace_initial_password_for_sync(),
                            "orgUnitPath": target_staff_ou,
                            "changePasswordAtNextLogin": True,
                        }
                    )
                    _sleep_ms(sleep_ms)
                    if created:
                        created_users += 1
                        print(f"[CREATE] staff {email} in OU {target_staff_ou}")
                    else:
                        errors += 1
                        print(f"[ERROR] failed to create staff {email}")
                        continue
                else:
                    print(f"[DRY] would ensure OU {target_staff_ou} then create staff {email}")
                    continue
            else:
                current_ou = g_user.get("orgUnitPath")
                if current_ou != target_staff_ou:
                    if apply_changes:
                        ou_res = move_user_to_ou(email, target_staff_ou)
                        if ou_res is True:
                            moved_ous += 1
                            print(f"[MOVE] staff {email}: {current_ou} -> {target_staff_ou}")
                        elif ou_res is False:
                            errors += 1
                            print(f"[ERROR] failed OU move for staff {email}")
                        else:
                            print(f"[INFO] Skipping protected/admin user: {email}")
                        _sleep_ms(sleep_ms)
                    else:
                        print(f"[DRY] would move staff {email}: {current_ou} -> {target_staff_ou}")

            # Teachers Google Group: not for accounts parked under Terminated & Removed.
            if STAFF_OU_TERMINATED_REMOVED not in target_staff_ou:
                if apply_changes:
                    if create_missing_groups and not get_google_group(TEACHERS_GROUP_EMAIL):
                        create_google_group(
                            TEACHERS_GROUP_EMAIL,
                            name="Teachers",
                            description="Auto-created by CSA sync.",
                        )
                        _sleep_ms(sleep_ms)
                    if ensure_user_in_group(email, TEACHERS_GROUP_EMAIL):
                        group_adds += 1
                        print(f"[GROUP] ensured {email} in {TEACHERS_GROUP_EMAIL}")
                    else:
                        errors += 1
                        print(f"[ERROR] failed ensuring {email} in {TEACHERS_GROUP_EMAIL}")
                    _sleep_ms(sleep_ms)
                else:
                    print(f"[DRY] would ensure {email} in {TEACHERS_GROUP_EMAIL}")
            else:
                print(f"[INFO] Skipping {TEACHERS_GROUP_EMAIL} for {email} (OU {target_staff_ou})")

    summary = {
        "created_users": created_users,
        "moved_ous": moved_ous,
        "group_ensures": group_adds,
        "errors": errors,
    }
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"created_users={summary['created_users']}")
    print(f"moved_ous={summary['moved_ous']}")
    print(f"group_ensures={summary['group_ensures']}")
    print(f"errors={summary['errors']}")
    print("=" * 80)
    if not apply_changes:
        print("DRY RUN completed. Set APPLY_CHANGES=1 to perform changes.")
    if summary["errors"] > 0:
        print(
            f"!!! Completed with {summary['errors']} warnings/errors, but continuing automation."
        )
        print("(Exiting with code 0 so the cron schedule keeps running; see errors above.)")

    # Never use summary['errors'] for process exit code — per-user API issues must not fail the job.
    return 0


if __name__ == "__main__":
    main()
    sys.exit(0)

