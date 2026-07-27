"""School-year helpers for report card generation (tenure, grade-at-year, enrollments)."""

from __future__ import annotations

from typing import Any

from extensions import db
from models import Class, Enrollment, SchoolYear, Student, StudentSchoolYear
from utils.student_roster import student_is_archived


def school_year_start_year(school_year: SchoolYear | str | None) -> int | None:
    """Parse the leading calendar year from a school year name like '2024-2025'."""
    if school_year is None:
        return None
    name = school_year.name if isinstance(school_year, SchoolYear) else str(school_year)
    name = (name or "").strip()
    if len(name) < 4:
        return None
    try:
        return int(name.split("-", 1)[0])
    except (TypeError, ValueError):
        return None


def is_valid_entrance_school_year(value: Any) -> bool:
    if not value or not isinstance(value, str):
        return False
    raw = value.strip()
    if len(raw) != 9 or raw[4] != "-":
        return False
    left, right = raw.split("-", 1)
    if not (left.isdigit() and right.isdigit()):
        return False
    return int(right) == int(left) + 1


def grade_display(grade_level: int | None) -> str:
    if grade_level == 0:
        return "K"
    if grade_level is not None:
        return str(grade_level)
    return "N/A"


def _derive_grade_level_for_school_year(student: Student, school_year: SchoolYear) -> int | None:
    """Estimate grade from current level and year offset (fallback when no stored record)."""
    current = getattr(student, "grade_level", None)
    if current is None or school_year is None:
        return None

    target_start = school_year_start_year(school_year)
    if target_start is None:
        return int(current)

    entrance = getattr(student, "entrance_date", None)
    if is_valid_entrance_school_year(entrance):
        entrance_start = school_year_start_year(entrance)
        if entrance_start is not None and target_start < entrance_start:
            return None

    active_sy = SchoolYear.query.filter_by(is_active=True).first()
    if not active_sy:
        return int(current)

    active_start = school_year_start_year(active_sy)
    if active_start is None:
        return int(current)

    years_diff = active_start - target_start
    grade = int(current) - years_diff
    return max(0, min(12, grade))


def get_student_school_year_record(
    student_id: int, school_year_id: int
) -> StudentSchoolYear | None:
    return StudentSchoolYear.query.filter_by(
        student_id=student_id,
        school_year_id=school_year_id,
    ).first()


def upsert_student_school_year(
    student_id: int,
    school_year_id: int,
    grade_level: int,
    *,
    enrolled: bool = True,
) -> StudentSchoolYear:
    record = get_student_school_year_record(student_id, school_year_id)
    if record is None:
        record = StudentSchoolYear(
            student_id=student_id,
            school_year_id=school_year_id,
            grade_level=int(grade_level),
            enrolled=bool(enrolled),
        )
        db.session.add(record)
    else:
        record.grade_level = int(grade_level)
        record.enrolled = bool(enrolled)
    return record


def record_student_school_year_grade(
    student_id: int,
    school_year_id: int,
    grade_level: int,
    *,
    enrolled: bool = True,
    commit: bool = False,
) -> None:
    if grade_level is None:
        return
    upsert_student_school_year(
        student_id, school_year_id, int(grade_level), enrolled=enrolled
    )
    if commit:
        db.session.commit()


def grade_level_for_school_year(student: Student, school_year: SchoolYear) -> int | None:
    """
    Return the student's grade during ``school_year``.

    Uses ``StudentSchoolYear`` when present; otherwise derives and persists when
    the student has enrollment in that year.
    """
    if student is None or school_year is None:
        return None

    record = get_student_school_year_record(student.id, school_year.id)
    if record is not None:
        return int(record.grade_level)

    derived = _derive_grade_level_for_school_year(student, school_year)
    if derived is not None and student_has_enrollment_in_year(student.id, school_year.id):
        upsert_student_school_year(student.id, school_year.id, derived, enrolled=True)
    return derived


def enrollment_must_be_active_for_report_card(
    student: Student,
    school_year: SchoolYear | None,
) -> bool:
    """
    Whether only active enrollments should be considered.

    Closed/archived years and withdrawn students include inactive enrollments so
    historical report cards can still be generated.
    """
    if student_is_archived(student):
        return False
    if school_year is not None and not bool(getattr(school_year, "is_active", True)):
        return False
    return True


def student_has_enrollment_in_year(student_id: int, school_year_id: int) -> bool:
    """True if the student has any enrollment in a class for this school year."""
    return (
        Enrollment.query.filter_by(student_id=student_id)
        .join(Class)
        .filter(Class.school_year_id == school_year_id)
        .count()
        > 0
    )


def grade_from_report_card_snapshot(grades_details: str | None) -> int | None:
    if not grades_details:
        return None
    try:
        import json

        data = json.loads(grades_details)
        if not isinstance(data, dict):
            return None
        display = data.get("student_display") or {}
        grade = display.get("grade")
        if grade is None:
            return None
        return int(grade)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def record_student_year_grades_before_close(
    school_year_id: int, student_ids: set[int] | list[int]
) -> None:
    """Snapshot each enrolled student's grade before year-end promotion."""
    for sid in student_ids:
        student = Student.query.get(sid)
        if not student or student.grade_level is None:
            continue
        record_student_school_year_grade(
            sid,
            school_year_id,
            int(student.grade_level),
            enrolled=True,
        )
