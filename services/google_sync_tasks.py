"""
Google Workspace Directory sync for a single user (e.g. after save in management UI).

Mirrors scripts/sync_all_to_google.py for one linked Student or TeacherStaff user:
ensure OU via policy, graduation-year group membership, school-level groups (students),
or /Staff + teachers group (staff).
"""

from __future__ import annotations

import logging
from typing import Optional

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
    sync_user_suspension_with_db_is_active,
)
from services.google_ou_policy import resolve_student_ou, school_level_group_for_grade

logger = logging.getLogger(__name__)

DOMAIN = "clarascienceacademy.org"
TEACHERS_GROUP_EMAIL = f"teachers@{DOMAIN}"
ELEMENTARY_GROUP_EMAIL = f"elementary@{DOMAIN}"
MIDDLE_SCHOOL_GROUP_EMAIL = f"middle_school@{DOMAIN}"
HIGH_SCHOOL_GROUP_EMAIL = f"highschool@{DOMAIN}"
STUDENT_ASSEMBLY_GROUP_EMAIL = f"studentassembly@{DOMAIN}"
DEFAULT_TEMP_PASSWORD = "Welcome2CSA!"


def _grad_year_group_email(grad_year: Optional[int]) -> Optional[str]:
    if grad_year is None:
        return None
    try:
        y = int(grad_year)
    except (TypeError, ValueError):
        return None
    return f"{y}@{DOMAIN}"


def _sync_student_workspace(student: Student, workspace_email: str, *, create_missing_groups: bool) -> None:
    """Apply Directory OU + groups for a student (same rules as bulk sync script)."""
    email = (workspace_email or "").strip()
    if not email:
        return

    db_active = bool(getattr(student, "is_active", True))
    sync_user_suspension_with_db_is_active(email, db_active)
    if not db_active:
        return

    decision = resolve_student_ou(
        grade_level=getattr(student, "grade_level", None),
        grad_year=getattr(student, "grad_year", None),
        expected_grad_date=getattr(student, "expected_grad_date", None),
        is_active=bool(getattr(student, "is_active", True)),
        marked_for_removal=bool(getattr(student, "marked_for_removal", False)),
        status_updated_at=getattr(student, "status_updated_at", None),
    )

    g_user = get_google_user(email)
    if not g_user:
        created = create_google_user(
            {
                "primaryEmail": email,
                "name": {"givenName": student.first_name, "familyName": student.last_name},
                "password": DEFAULT_TEMP_PASSWORD,
                "orgUnitPath": decision.target_ou_path,
                "changePasswordAtNextLogin": True,
            }
        )
        if not created:
            logger.warning("sync_single_user_to_google: create_google_user failed for student %s", email)
        else:
            g_user = get_google_user(email)
    else:
        current_ou = g_user.get("orgUnitPath")
        if current_ou != decision.target_ou_path:
            move_user_to_ou(email, decision.target_ou_path)

    grad_group = _grad_year_group_email(getattr(student, "grad_year", None))
    if grad_group:
        if create_missing_groups and not get_google_group(grad_group):
            create_google_group(
                grad_group,
                name=f"Class of {getattr(student, 'grad_year', '')}".strip() or grad_group,
                description="Auto-created by CSA sync to support filtering/group email.",
            )
        ensure_user_in_group(email, grad_group)

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

    if bool(getattr(student, "is_active", True)) and not bool(
        getattr(student, "marked_for_removal", False)
    ):
        if create_missing_groups:
            for g in desired_school_groups:
                if not get_google_group(g):
                    create_google_group(
                        g,
                        name=g.split("@", 1)[0].replace("_", " ").title(),
                        description="Auto-created by CSA sync.",
                    )
        sync_user_groups(email, desired_school_groups)


def _sync_staff_workspace(staff: TeacherStaff, workspace_email: str, *, create_missing_groups: bool) -> None:
    """Apply Directory OU + teachers group for staff (same rules as bulk sync script)."""
    email = (workspace_email or "").strip()
    if not email:
        return

    db_active = bool(getattr(staff, "is_active", True))
    sync_user_suspension_with_db_is_active(email, db_active)
    if not db_active:
        return

    g_user = get_google_user(email)
    if not g_user:
        created = create_google_user(
            {
                "primaryEmail": email,
                "name": {"givenName": staff.first_name, "familyName": staff.last_name},
                "password": DEFAULT_TEMP_PASSWORD,
                "orgUnitPath": "/Staff",
                "changePasswordAtNextLogin": True,
            }
        )
        if not created:
            logger.warning("sync_single_user_to_google: create_google_user failed for staff %s", email)
    else:
        current_ou = g_user.get("orgUnitPath")
        if current_ou != "/Staff":
            move_user_to_ou(email, "/Staff")

    if create_missing_groups and not get_google_group(TEACHERS_GROUP_EMAIL):
        create_google_group(
            TEACHERS_GROUP_EMAIL,
            name="Teachers",
            description="Auto-created by CSA sync.",
        )
    ensure_user_in_group(email, TEACHERS_GROUP_EMAIL)


def sync_single_user_to_google(user_id: int, *, create_missing_groups: bool = True) -> bool:
    """
    Look up User by id; if linked to a Student or TeacherStaff with a Workspace email,
    push OU + group membership to Google (same behavior as sync_all_to_google for that row).

    Returns True if a Workspace email existed and sync was attempted, False if skipped.
    Caller should wrap in try/except if failures must never propagate.
    """
    user = db.session.get(User, user_id)
    if not user:
        logger.warning("sync_single_user_to_google: user id %s not found", user_id)
        return False

    email = (user.google_workspace_email or "").strip()
    if not email:
        logger.debug("sync_single_user_to_google: user %s has no google_workspace_email; skip", user_id)
        return False

    if user.student_id:
        student = db.session.get(Student, user.student_id)
        if not student:
            logger.warning("sync_single_user_to_google: student id %s missing for user %s", user.student_id, user_id)
            return False
        _sync_student_workspace(student, email, create_missing_groups=create_missing_groups)
        return True

    if user.teacher_staff_id:
        staff = db.session.get(TeacherStaff, user.teacher_staff_id)
        if not staff:
            logger.warning(
                "sync_single_user_to_google: teacher_staff id %s missing for user %s",
                user.teacher_staff_id,
                user_id,
            )
            return False
        _sync_staff_workspace(staff, email, create_missing_groups=create_missing_groups)
        return True

    logger.debug("sync_single_user_to_google: user %s is not a student or staff link; skip", user_id)
    return False
