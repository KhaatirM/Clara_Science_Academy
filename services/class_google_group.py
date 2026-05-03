"""
Google Group per Class: stable group email, human-readable name, roster + teachers.

Group address: class-{id}-{YYYYYY}@clarascienceacademy.org (year digits from school year).
Teachers are included so they receive mail to the class list and match roster reality.

The **current** primary teacher (``Class.teacher``) is synced as the group **OWNER**;
co-teachers/subs are MEMBER. When the primary changes, the next sync promotes the new
primary to OWNER before demoting the former primary to MEMBER (if still on the roster).
"""

from __future__ import annotations

from flask import current_app

from extensions import db
from models import Class, Enrollment, Student, TeacherStaff, User
from services.google_directory_service import (
    create_google_group,
    get_google_group,
    sync_group_members,
)

CLASS_GROUP_DOMAIN = "clarascienceacademy.org"


def default_google_group_email_for_class(class_obj: Class) -> str:
    """Short, stable address; display name stays the full class title in Admin / Groups."""
    sy = class_obj.school_year
    if sy and getattr(sy, "start_date", None) and getattr(sy, "end_date", None):
        y1 = sy.start_date.year % 100
        y2 = sy.end_date.year % 100
        key = f"{y1:02d}{y2:02d}"
    else:
        key = "00"
    return f"class-{class_obj.id}-{key}@{CLASS_GROUP_DOMAIN}"


def primary_teacher_group_owner_email(class_obj: Class) -> str | None:
    """School email for the current primary teacher, if they have a linked User account."""
    if not class_obj.teacher or getattr(class_obj.teacher, "is_deleted", False):
        return None
    u = User.query.filter_by(teacher_staff_id=class_obj.teacher.id).first()
    if not u:
        return None
    e = (u.google_workspace_email or "").strip()
    return e if e else None


def _workspace_emails_for_staff(ts: TeacherStaff | None) -> list[str]:
    if not ts or getattr(ts, "is_deleted", False):
        return []
    u = User.query.filter_by(teacher_staff_id=ts.id).first()
    if not u:
        return []
    e = (u.google_workspace_email or "").strip()
    return [e] if e else []


def collect_class_group_member_emails(class_obj: Class) -> list[str]:
    """Active enrolled students (with school email) + primary/additional/substitute teachers."""
    raw: list[str] = []

    roster_rows = (
        db.session.query(User.google_workspace_email)
        .join(Student, Student.id == User.student_id)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(
            Enrollment.class_id == class_obj.id,
            Enrollment.is_active == True,
            Student.is_deleted == False,
            User.google_workspace_email.isnot(None),
        )
        .all()
    )
    for r in roster_rows:
        if r and r[0]:
            raw.append(str(r[0]).strip())

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


def provision_and_sync_class_google_group(class_id: int) -> bool:
    """
    Ensure Class.google_group_email is set (for active classes), Google Group exists,
    and membership matches roster + teachers.

    Inactive classes with no group: skip. Inactive with existing group: still sync membership.

    Returns True if nothing failed critically (including successful no-ops).
    """
    c = Class.query.get(class_id)
    if not c:
        current_app.logger.warning("provision_and_sync: class %s not found", class_id)
        return False

    group_email_stored = (c.google_group_email or "").strip()

    if not c.is_active and not group_email_stored:
        return True

    proposed = default_google_group_email_for_class(c)

    if not group_email_stored:
        c.google_group_email = proposed
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(
                "Could not save google_group_email for class %s: %s", class_id, exc
            )
            return False
        group_email_stored = proposed
    else:
        group_email_stored = (c.google_group_email or "").strip()

    if not get_google_group(group_email_stored):
        display = ((c.name or "").strip() or group_email_stored.split("@")[0])[:200]
        desc = (
            f"CSA class id {c.id}. School year: "
            f"{(c.school_year.name if c.school_year else 'n/a')}. Automated roster list."
        )
        if not create_google_group(group_email_stored, name=display, description=desc):
            current_app.logger.warning(
                "provision_and_sync: could not create Google group %s for class %s",
                group_email_stored,
                class_id,
            )
            return False

    members = collect_class_group_member_emails(c)
    primary_ws = primary_teacher_group_owner_email(c)
    member_lower = {m.lower() for m in members}
    if primary_ws and primary_ws.lower() in member_lower:
        sync_ok = sync_group_members(
            group_email_stored, members, owner_emails=[primary_ws]
        )
    else:
        sync_ok = sync_group_members(group_email_stored, members)

    if not sync_ok:
        current_app.logger.warning(
            "provision_and_sync: sync_group_members failed for %s (class %s)",
            group_email_stored,
            class_id,
        )
        return False
    return True


def try_provision_class_google_group(class_id: int) -> None:
    """Log warnings only; never raises (safe after HTTP handlers)."""
    try:
        provision_and_sync_class_google_group(class_id)
    except Exception as exc:
        current_app.logger.warning(
            "Class Google Group sync failed for class_id=%s: %s", class_id, exc
        )
