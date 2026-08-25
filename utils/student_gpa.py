"""
Roster GPA / academic status helpers.

- Grades K–8: GPA from the *active* school year only.
- High school (9–12): cumulative GPA across high-school tenure
  (every school year the student was enrolled at grade 9+), so early
  graduates (e.g. after 11th) only include those HS years.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Iterable

from models import Assignment, Grade, SchoolYear, Student, StudentSchoolYear, db

_last_sync_at = 0.0
_SYNC_TTL_SEC = 45.0

HS_GRADE_MIN = 9
HS_GRADE_MAX = 12


def get_active_school_year_id() -> int | None:
    active = SchoolYear.query.filter_by(is_active=True).first()
    return int(active.id) if active else None


def is_high_school_grade(grade_level) -> bool:
    try:
        g = int(grade_level)
    except (TypeError, ValueError):
        return False
    return HS_GRADE_MIN <= g <= HS_GRADE_MAX


def high_school_year_ids_for_student(student: Student | int) -> list[int]:
    """
    School-year IDs that count toward high-school tenure GPA.

    Uses StudentSchoolYear rows with grade_level 9–12. Always includes the active
    year when the student is currently in high school (covers missing SSY rows and
    early in a new year before upsert).
    """
    student_id = int(student.id if hasattr(student, "id") else student)
    rows = (
        StudentSchoolYear.query.filter(
            StudentSchoolYear.student_id == student_id,
            StudentSchoolYear.grade_level >= HS_GRADE_MIN,
            StudentSchoolYear.grade_level <= HS_GRADE_MAX,
        )
        .all()
    )
    year_ids = {int(r.school_year_id) for r in rows}

    grade = getattr(student, "grade_level", None) if hasattr(student, "grade_level") else None
    if grade is None:
        st = db.session.get(Student, student_id)
        grade = getattr(st, "grade_level", None) if st else None
    if is_high_school_grade(grade):
        active_id = get_active_school_year_id()
        if active_id is not None:
            year_ids.add(active_id)
    return sorted(year_ids)


def grades_for_gpa(
    student_id: int,
    *,
    class_ids: Iterable[int] | None = None,
    school_year_id: int | None = None,
    school_year_ids: Iterable[int] | None = None,
) -> list:
    """Non-voided grades used for GPA (optionally limited to classes / school year(s))."""
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
    if school_year_ids is not None:
        ids = list(school_year_ids)
        if not ids:
            return []
        q = q.filter(Assignment.school_year_id.in_(ids))
    elif school_year_id is not None:
        q = q.filter(Assignment.school_year_id == school_year_id)
    return q.all()


def compute_scoped_gpa(
    student_id: int,
    *,
    class_ids: Iterable[int] | None = None,
    school_year_id: int | None = None,
    school_year_ids: Iterable[int] | None = None,
) -> float | None:
    """
    GPA for a student from matching grades.
    Returns None when there are no qualifying grades (Academic Status: No Data).
    """
    from services.gpa_scheduler import calculate_student_gpa

    grades = grades_for_gpa(
        student_id,
        class_ids=class_ids,
        school_year_id=school_year_id,
        school_year_ids=school_year_ids,
    )
    if not grades:
        return None
    return float(calculate_student_gpa(grades))


def compute_active_year_gpa(student_id: int) -> float | None:
    """GPA scoped to the active school year (all-time if no active year exists)."""
    from utils.gpa_period_visibility import roster_gpa_unlocked

    year_id = get_active_school_year_id()
    if year_id is not None and not roster_gpa_unlocked(year_id):
        return None
    return compute_scoped_gpa(student_id, school_year_id=year_id)


def compute_high_school_tenure_gpa(student: Student) -> float | None:
    """
    Cumulative GPA across school years the student was in grades 9–12.

    Until the active year's Q1 GPA is released, exclude the active year so
    early assignments do not drag tenure GPA / academic concerns.
    """
    from utils.gpa_period_visibility import roster_gpa_unlocked

    year_ids = high_school_year_ids_for_student(student)
    if not year_ids:
        return None
    active_id = get_active_school_year_id()
    if active_id is not None and not roster_gpa_unlocked(active_id):
        year_ids = [y for y in year_ids if int(y) != int(active_id)]
        if not year_ids:
            return None
    return compute_scoped_gpa(int(student.id), school_year_ids=year_ids)


def compute_roster_gpa(student: Student) -> float | None:
    """
    Roster GPA used for Students list / Academic Status.

    High school (9–12): high-school tenure. Everyone else: active school year.
    Gated until active-year Q1 official GPA release.
    """
    if is_high_school_grade(getattr(student, "grade_level", None)):
        return compute_high_school_tenure_gpa(student)
    return compute_active_year_gpa(int(student.id))


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


def _gpa_from_grades(grades: list) -> float | None:
    from services.gpa_scheduler import calculate_student_gpa

    if not grades:
        return None
    return float(calculate_student_gpa(grades))


def sync_active_year_gpas(*, commit: bool = True, force: bool = False) -> dict:
    """
    Rewrite Student.gpa for roster display.

    K–8: active school year. High school (9–12): cumulative HS tenure years.
    Students with no qualifying grades get gpa=None (No Data).
    Until active-year Q1 GPA is officially released, K–8 stay None and HS
    exclude the active year's grades.
    Throttled (~45s) unless force=True (scheduler / ops).
    """
    global _last_sync_at

    now = time.time()
    if not force and (now - _last_sync_at) < _SYNC_TTL_SEC:
        return {
            "skipped": True,
            "school_year_id": get_active_school_year_id(),
        }

    from utils.gpa_period_visibility import roster_gpa_unlocked

    year_id = get_active_school_year_id()
    year_unlocked = True if year_id is None else roster_gpa_unlocked(year_id)
    students = Student.query.all()

    hs_years_by_student: dict[int, set[int]] = defaultdict(set)
    for row in StudentSchoolYear.query.filter(
        StudentSchoolYear.grade_level >= HS_GRADE_MIN,
        StudentSchoolYear.grade_level <= HS_GRADE_MAX,
    ).all():
        hs_years_by_student[int(row.student_id)].add(int(row.school_year_id))

    for student in students:
        sid = int(student.id)
        if is_high_school_grade(student.grade_level):
            # Include active year for current HS students only after Q1 release.
            if year_id is not None and year_unlocked:
                hs_years_by_student[sid].add(year_id)
            elif year_id is not None and not year_unlocked:
                hs_years_by_student[sid].discard(year_id)

    all_hs_year_ids = set()
    for ids in hs_years_by_student.values():
        all_hs_year_ids |= ids

    active_by_student: dict[int, list] = defaultdict(list)
    if year_id is not None and year_unlocked:
        for grade in (
            Grade.query.join(Assignment)
            .filter(
                Grade.is_voided.is_(False),
                Assignment.status != "Voided",
                Assignment.school_year_id == year_id,
            )
            .all()
        ):
            active_by_student[int(grade.student_id)].append(grade)
    elif year_id is None:
        for grade in (
            Grade.query.join(Assignment)
            .filter(
                Grade.is_voided.is_(False),
                Assignment.status != "Voided",
            )
            .all()
        ):
            active_by_student[int(grade.student_id)].append(grade)

    hs_by_student_year: dict[tuple[int, int], list] = defaultdict(list)
    if all_hs_year_ids:
        for grade, assignment in (
            db.session.query(Grade, Assignment)
            .join(Assignment, Grade.assignment_id == Assignment.id)
            .filter(
                Grade.is_voided.is_(False),
                Assignment.status != "Voided",
                Assignment.school_year_id.in_(list(all_hs_year_ids)),
            )
            .all()
        ):
            hs_by_student_year[(int(grade.student_id), int(assignment.school_year_id))].append(
                grade
            )

    updated = 0
    cleared = 0
    hs_count = 0
    for student in students:
        sid = int(student.id)
        if is_high_school_grade(student.grade_level):
            hs_count += 1
            grades: list = []
            for yid in hs_years_by_student.get(sid, set()):
                grades.extend(hs_by_student_year.get((sid, yid), []))
            gpa = _gpa_from_grades(grades)
        else:
            if year_id is not None and not year_unlocked:
                gpa = None
            else:
                gpa = _gpa_from_grades(active_by_student.get(sid, []))

        if gpa is not None:
            student.gpa = gpa
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
        "roster_gpa_unlocked": year_unlocked,
        "updated": updated,
        "cleared": cleared,
        "high_school_students": hs_count,
    }
