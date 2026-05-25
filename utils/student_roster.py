"""
Active school roster vs archived (removed / transferred) students.

Archived students (``is_deleted``, ``marked_for_removal``, or ``is_active=False``)
stay in the database for records and former-student report cards, but must not
appear in day-to-day UI: academic concerns, attendance, class rosters, comms, etc.
"""

from __future__ import annotations

from sqlalchemy import and_, exists, select

from models import Enrollment, Student, db


def student_is_archived(student) -> bool:
    """True if the student is removed from the active school roster."""
    if student is None:
        return True
    if getattr(student, "is_deleted", False):
        return True
    if getattr(student, "marked_for_removal", False):
        return True
    if getattr(student, "is_active", True) is False:
        return True
    return False


def student_is_on_active_roster(student, *, require_active_enrollment: bool = True) -> bool:
    """
    True if the student should appear in operational school UI.

    ``require_active_enrollment``: when True (default), the student must have at
    least one active class enrollment. Use False only when checking profile flags.
    """
    if student_is_archived(student):
        return False
    if not require_active_enrollment:
        return True
    return (
        db.session.query(Enrollment.id)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.is_active.is_(True),
        )
        .first()
        is not None
    )


def active_roster_student_filters():
    """SQLAlchemy criteria for ``Student`` queries (profile flags only)."""
    return and_(
        Student.is_deleted.is_(False),
        Student.marked_for_removal.is_(False),
        Student.is_active.is_(True),
    )


def active_roster_students_query(*, require_active_enrollment: bool = True):
    """
    Query students on the active roster.

    Former / removed students (``status_filter=former``) use ``Student.is_deleted``.
    """
    q = Student.query.filter(active_roster_student_filters())
    if require_active_enrollment:
        enrolled = (
            select(Enrollment.student_id)
            .where(Enrollment.is_active.is_(True))
            .distinct()
        )
        q = q.filter(Student.id.in_(enrolled))
    return q


def active_roster_student_ids(*, require_active_enrollment: bool = True) -> list[int]:
    """IDs of students on the active roster."""
    return [
        row[0]
        for row in active_roster_students_query(
            require_active_enrollment=require_active_enrollment
        )
        .with_entities(Student.id)
        .all()
    ]


def filter_student_ids_on_roster(student_ids, *, require_active_enrollment: bool = True) -> list[int]:
    """Keep only IDs that belong to active-roster students."""
    if not student_ids:
        return []
    q = active_roster_students_query(require_active_enrollment=require_active_enrollment).filter(
        Student.id.in_(student_ids)
    )
    return [row[0] for row in q.with_entities(Student.id).all()]
