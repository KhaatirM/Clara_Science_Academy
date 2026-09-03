"""
School-managed Google Classroom provisioning per Clara Class.

Creates courses as botadmin, direct-enrolls teachers/students (no invite accept),
and deletes courses when a school year is archived.
"""

from __future__ import annotations

from flask import current_app

from extensions import db
from models import Class, TeacherStaff, User
from services.class_google_group import (
    class_needs_google_integration,
    primary_teacher_group_owner_email,
)
from services.google_classroom_admin import (
    add_student_direct,
    add_teacher_direct,
    classroom_api_subject,
    classroom_owner_email,
    create_course_as_admin,
    delete_course,
    get_course,
    list_course_student_emails,
    list_course_teacher_emails,
    remove_student,
    remove_teacher,
)


def _workspace_emails_for_staff(ts: TeacherStaff | None) -> list[str]:
    if not ts or getattr(ts, "is_deleted", False):
        return []
    u = User.query.filter_by(teacher_staff_id=ts.id).first()
    if not u:
        return []
    e = (u.google_workspace_email or "").strip()
    return [e] if e else []


def collect_classroom_teacher_emails(class_obj: Class) -> list[str]:
    raw: list[str] = []
    if class_obj.teacher:
        raw.extend(_workspace_emails_for_staff(class_obj.teacher))
    for ts in class_obj.additional_teachers:
        raw.extend(_workspace_emails_for_staff(ts))
    for ts in class_obj.substitute_teachers:
        raw.extend(_workspace_emails_for_staff(ts))
    seen: set[str] = set()
    out: list[str] = []
    for e in raw:
        e = (e or "").strip()
        if not e:
            continue
        low = e.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(e)
    return out


def collect_classroom_student_emails(class_obj: Class) -> list[str]:
    """School emails for active enrolled students who can be added to Classroom.

    Prefer ``User.google_workspace_email``. When that field is blank but the student
    has a portal account and a generated school address, use the generated address
    so roster sync matches Directory naming (common for students rostered before
    Workspace email was backfilled onto their User row).
    """
    from management_routes.students import _student_workspace_email
    from utils.student_roster import active_class_roster_students_query

    seen: set[str] = set()
    out: list[str] = []
    for student in active_class_roster_students_query(class_obj.id).all():
        e = (_student_workspace_email(student) or "").strip()
        if not e:
            continue
        low = e.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(e)
    return out


def students_missing_workspace_email(class_obj: Class) -> list[str]:
    """Enrolled students that cannot be added to Classroom because they have no school email.

    After ``ensure_roster_workspace_emails``, this should mainly catch students with
    no portal User / no generatable address (e.g. K–2 without login).
    """
    from management_routes.students import _student_workspace_email
    from utils.student_roster import active_class_roster_students_query

    missing: list[str] = []
    for student in active_class_roster_students_query(class_obj.id).all():
        if (_student_workspace_email(student) or "").strip():
            continue
        missing.append(
            f"{(student.first_name or '').strip()} {(student.last_name or '').strip()}".strip()
            or f"Student {student.id}"
        )
    return missing


def ensure_roster_workspace_emails(class_obj: Class) -> int:
    """Persist blank ``User.google_workspace_email`` values for enrolled students.

    Returns how many User rows were updated. Commits when any were filled.
    """
    from management_routes.students import _ensure_student_google_workspace_email
    from utils.student_roster import active_class_roster_students_query

    filled = 0
    for student in active_class_roster_students_query(class_obj.id).all():
        try:
            if _ensure_student_google_workspace_email(student):
                filled += 1
        except Exception as exc:
            current_app.logger.warning(
                "Could not ensure workspace email for student %s in class %s: %s",
                getattr(student, "id", None),
                class_obj.id,
                exc,
            )
    if not filled:
        return 0
    try:
        db.session.commit()
        current_app.logger.info(
            "Filled google_workspace_email for %d enrolled student(s) in class %s (%s)",
            filled,
            class_obj.id,
            class_obj.name,
        )
        return filled
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(
            "Failed committing workspace email backfill for class %s: %s",
            class_obj.id,
            exc,
        )
        return 0


def provision_and_sync_class_google_classroom(class_id: int) -> bool:
    """
    Ensure an active class has a school-managed Google Classroom and that
    teacher/student membership matches Clara enrollments (direct add, no invites).
    """
    c = Class.query.get(class_id)
    if not c:
        current_app.logger.warning("classroom provision: class %s not found", class_id)
        return False

    if not c.is_active:
        return True

    if not class_needs_google_integration(c):
        return True

    if not classroom_owner_email():
        current_app.logger.warning(
            "classroom provision skipped for class %s: delegated Classroom user not configured",
            class_id,
        )
        return False

    # Students rostered on the site often have a portal User but a blank
    # google_workspace_email; fill from naming rules before collecting the roster.
    ensure_roster_workspace_emails(c)

    course_id = (c.google_classroom_id or "").strip() or None
    if course_id:
        existing = get_course(course_id)
        if not existing:
            current_app.logger.warning(
                "Stored google_classroom_id %s missing in Google for class %s; recreating",
                course_id,
                class_id,
            )
            course_id = None
            c.google_classroom_id = None
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    if not course_id:
        course = create_course_as_admin(
            name=c.name or f"Class {c.id}",
            section=c.subject or None,
            description=c.description or f"Welcome to {c.name}",
            room=c.room_number or None,
        )
        if not course or not course.get("id"):
            return False
        c.google_classroom_id = str(course["id"])
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(
                "Could not save google_classroom_id for class %s: %s", class_id, exc
            )
            return False
        course_id = c.google_classroom_id

    desired_teachers = {e.lower(): e for e in collect_classroom_teacher_emails(c)}
    desired_students = {e.lower(): e for e in collect_classroom_student_emails(c)}
    owner = (classroom_owner_email() or "").lower()
    api_subject = (classroom_api_subject() or "").lower()
    protected_teachers = {e for e in (owner, api_subject) if e}

    # Prefer adding primary teacher first so they appear promptly.
    primary = primary_teacher_group_owner_email(c)
    if primary:
        add_teacher_direct(course_id, primary)

    current_teachers = list_course_teacher_emails(course_id)
    current_students = list_course_student_emails(course_id)

    for low, email in desired_teachers.items():
        if low not in current_teachers:
            add_teacher_direct(course_id, email)

    for low in current_teachers:
        if low in protected_teachers:
            continue
        if low not in desired_teachers:
            remove_teacher(course_id, low)

    failed_students: list[str] = []
    for low, email in desired_students.items():
        if low not in current_students:
            if not add_student_direct(course_id, email):
                failed_students.append(email)

    for low in current_students:
        if low not in desired_students:
            remove_student(course_id, low)

    # Surface the two ways a roster silently ends up incomplete.
    missing_email = students_missing_workspace_email(c)
    if missing_email:
        current_app.logger.warning(
            "Classroom roster for class %s (%s) is missing %d student(s) with no Google "
            "Workspace email: %s",
            c.id,
            c.name,
            len(missing_email),
            ", ".join(missing_email),
        )
    if failed_students:
        current_app.logger.error(
            "Classroom roster for class %s (%s): %d student(s) could not be added: %s",
            c.id,
            c.name,
            len(failed_students),
            ", ".join(failed_students),
        )

    return not failed_students


def try_provision_class_google_classroom(class_id: int) -> None:
    """Log warnings only; never raises."""
    try:
        provision_and_sync_class_google_classroom(class_id)
    except Exception as exc:
        current_app.logger.warning(
            "Class Google Classroom sync failed for class_id=%s: %s", class_id, exc
        )


def try_delete_class_google_classroom(class_obj: Class) -> bool:
    """
    Best-effort delete of the class's school-managed Google Classroom.
    Clears ``google_classroom_id`` on success. Never raises.
    """
    if not class_obj:
        return True
    course_id = (class_obj.google_classroom_id or "").strip()
    if not course_id:
        return True
    try:
        if delete_course(course_id):
            class_obj.google_classroom_id = None
            current_app.logger.info(
                "Deleted Google Classroom %s for class_id=%s",
                course_id,
                getattr(class_obj, "id", None),
            )
            return True
        current_app.logger.warning(
            "Could not delete Google Classroom %s for class_id=%s",
            course_id,
            getattr(class_obj, "id", None),
        )
        return False
    except Exception as exc:
        current_app.logger.warning(
            "Google Classroom delete failed for class_id=%s course=%s: %s",
            getattr(class_obj, "id", None),
            course_id,
            exc,
        )
        return False


def delete_class_google_classrooms_for_school_year(school_year_id: int) -> dict:
    """
    Delete school-managed Google Classroom courses for all classes in a school year.
    Clears ``Class.google_classroom_id`` after a successful delete (or if already gone).
    """
    classes = Class.query.filter_by(school_year_id=school_year_id).all()
    deleted = 0
    failed = 0
    skipped = 0
    errors: list[str] = []

    for class_obj in classes:
        course_id = (class_obj.google_classroom_id or "").strip()
        if not course_id:
            skipped += 1
            continue
        if delete_course(course_id):
            deleted += 1
            class_obj.google_classroom_id = None
        else:
            failed += 1
            if len(errors) < 10:
                errors.append(f"{class_obj.name} ({course_id})")

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(
            "Failed committing Classroom id clears for school_year_id=%s: %s",
            school_year_id,
            exc,
        )

    current_app.logger.info(
        "Class Google Classroom deletion for school_year_id=%s: deleted=%s failed=%s skipped=%s",
        school_year_id,
        deleted,
        failed,
        skipped,
    )
    return {
        "deleted": deleted,
        "failed": failed,
        "skipped": skipped,
        "errors_sample": errors,
    }
