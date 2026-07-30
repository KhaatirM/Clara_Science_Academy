"""
Active school-year GPA helpers.

Roster GPA / academic status should reflect the *active* school year
(assignments with Assignment.school_year_id == active year), not all-time grades.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Iterable

from models import Assignment, Grade, SchoolYear, Student, db

_last_sync_at = 0.0
_SYNC_TTL_SEC = 45.0


def get_active_school_year_id() -> int | None:
    active = SchoolYear.query.filter_by(is_active=True).first()
    return int(active.id) if active else None


def grades_for_gpa(
    student_id: int,
    *,
    class_ids: Iterable[int] | None = None,
    school_year_id: int | None = None,
) -> list:
    """Non-voided grades used for GPA (optionally limited to classes / school year)."""
    q = (
        Grade.query.join(Assignment)
        .filter(
            Grade.student_id == student_id,
            Grade.is_voided.is_(False),
            Assignment.status != "Voided",
        )
    )
    if class_ids is not None:
        q = q.filter(Assignment.class_id.in_(list(class_ids)))
    if school_year_id is not None:
        q = q.filter(Assignment.school_year_id == school_year_id)
    return q.all()


def compute_scoped_gpa(
    student_id: int,
    *,
    class_ids: Iterable[int] | None = None,
    school_year_id: int | None = None,
) -> float | None:
    """
    GPA for a student from matching grades.
    Returns None when there are no qualifying grades (Academic Status: No Data).
    """
    from services.gpa_scheduler import calculate_student_gpa

    grades = grades_for_gpa(
        student_id, class_ids=class_ids, school_year_id=school_year_id
    )
    if not grades:
        return None
    return float(calculate_student_gpa(grades))


def compute_active_year_gpa(student_id: int) -> float | None:
    """GPA scoped to the active school year (all-time if no active year exists)."""
    year_id = get_active_school_year_id()
    return compute_scoped_gpa(student_id, school_year_id=year_id)


def academic_status_for_gpa(gpa: float | None) -> tuple[str, str]:
    """Return (label, tone) for roster Academic Status."""
    if gpa is None:
        return "No Data", "muted"
    if gpa >= 3.5:
        return "Honors", "success"
    if gpa >= 3.0:
        return "Good Standing", "primary"
    if gpa >= 2.0:
        return "Needs Improvement", "warning"
    return "At Risk", "danger"


def gpa_alert_level(gpa: float | None) -> str:
    if gpa is None:
        return "none"
    if gpa < 2.0:
        return "critical"
    if gpa < 3.0:
        return "warning"
    if gpa >= 3.5:
        return "excellent"
    return "none"


def sync_active_year_gpas(*, commit: bool = True, force: bool = False) -> dict:
    """
    Rewrite Student.gpa from active-year assignment grades for every student.

    Students with no grades in the active year get gpa=None (No Data).
    If there is no active school year, falls back to all non-voided grades.
    Throttled (~45s) unless force=True (scheduler / ops).
    """
    global _last_sync_at

    now = time.time()
    if not force and (now - _last_sync_at) < _SYNC_TTL_SEC:
        return {
            "skipped": True,
            "school_year_id": get_active_school_year_id(),
        }

    from services.gpa_scheduler import calculate_student_gpa

    year_id = get_active_school_year_id()
    q = (
        Grade.query.join(Assignment)
        .filter(
            Grade.is_voided.is_(False),
            Assignment.status != "Voided",
        )
    )
    if year_id is not None:
        q = q.filter(Assignment.school_year_id == year_id)

    by_student: dict[int, list] = defaultdict(list)
    for grade in q.all():
        by_student[int(grade.student_id)].append(grade)

    updated = 0
    cleared = 0
    for student in Student.query.all():
        grades = by_student.get(int(student.id))
        if grades:
            student.gpa = float(calculate_student_gpa(grades))
            updated += 1
        else:
            if student.gpa is not None:
                cleared += 1
            student.gpa = None

    if commit:
        db.session.commit()

    _last_sync_at = time.time()
    return {
        "skipped": False,
        "school_year_id": year_id,
        "updated": updated,
        "cleared": cleared,
    }
