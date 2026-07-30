"""School-year helpers for report card generation (tenure, grade-at-year, enrollments)."""

from __future__ import annotations

from collections import Counter
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


_ORDINAL_TO_GRADE = {
    "k": 0,
    "kindergarten": 0,
    "1st": 1,
    "2nd": 2,
    "3rd": 3,
    "4th": 4,
    "5th": 5,
    "6th": 6,
    "7th": 7,
    "8th": 8,
    "9th": 9,
    "10th": 10,
    "11th": 11,
    "12th": 12,
}


def _parse_grade_token(token: str) -> int | None:
    raw = (token or "").strip().lower()
    if not raw:
        return None
    if raw in _ORDINAL_TO_GRADE:
        return _ORDINAL_TO_GRADE[raw]
    if raw.isdigit():
        value = int(raw)
        if 0 <= value <= 12:
            return value
    return None


def _grades_from_class_name(name: str | None) -> list[int]:
    """
    Pull grade hints from names like \"Math [4th]\", \"LA [4th-5th]\", \"4th Grade Homeroom\".
    """
    import re

    if not name:
        return []
    text = str(name)

    bracket = re.search(r"\[([^\]]+)\]", text)
    if bracket:
        inner = bracket.group(1).strip().lower()
        if "-" in inner:
            left_s, right_s = [p.strip() for p in inner.split("-", 1)]
            left = _parse_grade_token(left_s)
            right = _parse_grade_token(right_s)
            if left is not None and right is not None and left <= right:
                return list(range(left, right + 1))
            return [g for g in (left, right) if g is not None]
        single = _parse_grade_token(inner)
        return [single] if single is not None else []

    found: list[int] = []
    for match in re.finditer(
        r"\b(kindergarten|k|1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|11th|12th)\b",
        text,
        flags=re.IGNORECASE,
    ):
        grade = _parse_grade_token(match.group(1))
        if grade is not None:
            found.append(grade)
    for match in re.finditer(r"\bgrade\s*([0-9]{1,2})\b", text, flags=re.IGNORECASE):
        grade = _parse_grade_token(match.group(1))
        if grade is not None:
            found.append(grade)
    # Preserve order, drop duplicates.
    out: list[int] = []
    for g in found:
        if g not in out:
            out.append(g)
    return out


def _grade_from_year_enrollments(student_id: int, school_year_id: int) -> int | None:
    """
    Infer grade from classes the student attended that year.

    Uses configured grade_levels when present, and falls back to grade tags in
    class names (e.g. \"Math [4th]\") when grade_levels were never set. Narrow
    single-grade signals outweigh broad multi-grade bands; if single-grade
    signals conflict, multi-grade / range hints break the tie.
    """
    classes = (
        Class.query.join(Enrollment, Enrollment.class_id == Class.id)
        .filter(
            Enrollment.student_id == student_id,
            Class.school_year_id == school_year_id,
        )
        .all()
    )
    hard_votes: list[int] = []
    soft_votes: list[int] = []
    for class_obj in classes:
        levels: list[int] = []
        if hasattr(class_obj, "get_grade_levels"):
            for g in class_obj.get_grade_levels() or []:
                try:
                    levels.append(int(g))
                except (TypeError, ValueError):
                    continue
        name_grades = _grades_from_class_name(getattr(class_obj, "name", None))

        if len(levels) == 1:
            hard_votes.append(levels[0])
        elif not levels and len(name_grades) == 1:
            hard_votes.append(name_grades[0])
        elif len(levels) > 1:
            soft_votes.extend(levels)
        elif len(name_grades) > 1:
            soft_votes.extend(name_grades)

    if hard_votes:
        tallies = Counter(hard_votes)
        top_grade, top_count = tallies.most_common(1)[0]
        # Clear majority among single-grade classes.
        if top_count > sum(1 for g in hard_votes if g != top_grade):
            return top_grade
        # Tie / weak hard signal — let multi-grade name bands break it.
        if soft_votes:
            return Counter(hard_votes + soft_votes).most_common(1)[0][0]
        return top_grade

    if soft_votes:
        return Counter(soft_votes).most_common(1)[0][0]
    return None



def _derive_grade_level_for_school_year(student: Student, school_year: SchoolYear) -> int | None:
    """
    Estimate grade from current level and year offset.

    Only valid when ``student.grade_level`` already reflects the *active* year
    (i.e. promotions have been applied). Prefer enrollment-based inference.
    """
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

    # Active year: current grade is authoritative.
    if school_year.id == active_sy.id or (
        school_year_start_year(school_year) == active_start
    ):
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

    Priority:
    1. Active year → live ``Student.grade_level``
    2. Grade inferred from that year's class enrollments (single-grade classes)
    3. Stored ``StudentSchoolYear`` row
    4. Year-offset derivation from current grade (not auto-persisted)
    """
    if student is None or school_year is None:
        return None

    # Live roster grade is source of truth for the open year.
    if bool(getattr(school_year, "is_active", False)):
        current = getattr(student, "grade_level", None)
        if current is not None:
            try:
                upsert_student_school_year(
                    student.id, school_year.id, int(current), enrolled=True
                )
            except Exception:
                pass
            return int(current)
        return None

    from_classes = _grade_from_year_enrollments(student.id, school_year.id)
    record = get_student_school_year_record(student.id, school_year.id)

    if from_classes is not None:
        # Heal stale / wrongly derived StudentSchoolYear rows.
        if record is None or int(record.grade_level) != int(from_classes):
            try:
                upsert_student_school_year(
                    student.id, school_year.id, int(from_classes), enrolled=True
                )
            except Exception:
                pass
        return int(from_classes)

    if record is not None:
        return int(record.grade_level)

    derived = _derive_grade_level_for_school_year(student, school_year)
    # Do not persist offset-derived grades — if promotions never ran, they are
    # off-by-one and would poison StudentSchoolYear.
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
        # Prefer class-band grade for the year being closed when available.
        from_classes = _grade_from_year_enrollments(sid, school_year_id)
        grade = from_classes if from_classes is not None else int(student.grade_level)
        record_student_school_year_grade(
            sid,
            school_year_id,
            int(grade),
            enrolled=True,
        )


def repair_student_school_year_grades(
    school_year_id: int,
    *,
    fix_report_card_snapshots: bool = True,
    commit: bool = True,
) -> dict[str, Any]:
    """
    Rebuild StudentSchoolYear (and optional report-card display grades) from
    that year's class enrollments. Fixes off-by-one rows created by deriving
    from an un-promoted live grade_level.
    """
    from models import ReportCard
    import json

    school_year = SchoolYear.query.get(school_year_id)
    if not school_year:
        return {"ok": False, "error": "School year not found."}

    student_ids = {
        row[0]
        for row in (
            db.session.query(Enrollment.student_id)
            .join(Class, Class.id == Enrollment.class_id)
            .filter(Class.school_year_id == school_year_id)
            .distinct()
            .all()
        )
    }

    updated_ssy = 0
    skipped = 0
    fixed_cards = 0

    for sid in student_ids:
        inferred = _grade_from_year_enrollments(sid, school_year_id)
        if inferred is None:
            skipped += 1
            continue
        record = get_student_school_year_record(sid, school_year_id)
        if record is None or int(record.grade_level) != int(inferred):
            upsert_student_school_year(sid, school_year_id, int(inferred), enrolled=True)
            updated_ssy += 1

        if fix_report_card_snapshots:
            cards = ReportCard.query.filter_by(
                student_id=sid, school_year_id=school_year_id
            ).all()
            for card in cards:
                try:
                    data = json.loads(card.grades_details) if card.grades_details else {}
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(data, dict):
                    continue
                display = data.get("student_display")
                if not isinstance(display, dict):
                    display = {}
                    data["student_display"] = display
                prev = display.get("grade")
                try:
                    prev_i = int(prev) if prev is not None else None
                except (TypeError, ValueError):
                    prev_i = None
                if prev_i != int(inferred):
                    display["grade"] = int(inferred)
                    display["grade_display"] = grade_display(int(inferred))
                    card.grades_details = json.dumps(data)
                    fixed_cards += 1

    if commit:
        db.session.commit()

    return {
        "ok": True,
        "school_year_id": school_year_id,
        "school_year_name": school_year.name,
        "students_considered": len(student_ids),
        "student_school_year_updated": updated_ssy,
        "skipped_no_single_grade_class": skipped,
        "skipped_no_grade_signal": skipped,
        "report_cards_updated": fixed_cards,
    }


def promote_students_still_on_prior_year_grade(
    closed_school_year_id: int,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    """
    If a closed year has grade G for a student (from classes / SSY) and their
    live ``grade_level`` is still G, promote them to G+1 for the new year.

    Skips departed students and those staged to graduate/withdraw/repeat.
    """
    from utils.student_departure import (
        DEPARTURE_STATUSES,
        effective_year_end_intent,
    )

    school_year = SchoolYear.query.get(closed_school_year_id)
    if not school_year or bool(getattr(school_year, "is_active", False)):
        return {"ok": False, "error": "Pass a closed (inactive) school year id."}

    active = SchoolYear.query.filter_by(is_active=True).first()
    if not active:
        return {"ok": False, "error": "No active school year."}

    student_ids = {
        row[0]
        for row in (
            db.session.query(Enrollment.student_id)
            .join(Class, Class.id == Enrollment.class_id)
            .filter(Class.school_year_id == closed_school_year_id)
            .distinct()
            .all()
        )
    }

    promoted = 0
    skipped = 0
    for sid in student_ids:
        student = Student.query.get(sid)
        if not student or getattr(student, "is_deleted", False):
            skipped += 1
            continue
        if not bool(getattr(student, "is_active", True)):
            skipped += 1
            continue
        if getattr(student, "departure_status", None) in DEPARTURE_STATUSES:
            skipped += 1
            continue
        intent = effective_year_end_intent(student)
        if intent in ("graduate", "withdraw", "repeat"):
            skipped += 1
            continue
        if getattr(student, "is_repeating", False):
            skipped += 1
            continue
        closed_grade = grade_level_for_school_year(student, school_year)
        if closed_grade is None or student.grade_level is None:
            skipped += 1
            continue
        if int(student.grade_level) != int(closed_grade):
            skipped += 1
            continue
        if int(closed_grade) >= 12:
            skipped += 1
            continue
        student.grade_level = int(closed_grade) + 1
        student.year_end_intent = None
        upsert_student_school_year(
            sid, active.id, int(student.grade_level), enrolled=True
        )
        promoted += 1

    if commit:
        db.session.commit()

    return {
        "ok": True,
        "closed_school_year_id": closed_school_year_id,
        "active_school_year_id": active.id,
        "promoted": promoted,
        "skipped": skipped,
        "students_considered": len(student_ids),
    }
