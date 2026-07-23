"""Student classes list payload for the React SPA."""

from __future__ import annotations

import json
from typing import Any

from flask_login import current_user
from sqlalchemy.orm import joinedload

from models import (
    Assignment,
    Class,
    Enrollment,
    Grade,
    GroupAssignment,
    GroupGrade,
    SchoolYear,
    Student,
    StudentAssistant,
)


def _teacher_name(class_obj: Class) -> str:
    teacher = getattr(class_obj, "teacher", None)
    if not teacher:
        return "No teacher assigned"
    name = f"{getattr(teacher, 'first_name', '') or ''} {getattr(teacher, 'last_name', '') or ''}".strip()
    return name or "No teacher assigned"


def _avg_for_class(student_id: int, class_obj: Class, school_year_id: int) -> float | None:
    from studentroutes import _get_points_earned

    grade_percentages: list[float] = []

    class_grades = (
        Grade.query.join(Assignment)
        .filter(
            Grade.student_id == student_id,
            Assignment.class_id == class_obj.id,
            Assignment.school_year_id == school_year_id,
        )
        .all()
    )
    for g in class_grades:
        if g.is_voided or (g.assignment and g.assignment.status == "Voided"):
            continue
        try:
            grade_data = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
            points_earned = _get_points_earned(grade_data)
            if points_earned is None:
                continue
            points_earned = float(points_earned)
            total_points = (
                g.assignment.total_points if (g.assignment and g.assignment.total_points) else 100.0
            )
            if total_points and total_points > 0:
                grade_percentages.append(points_earned / total_points * 100)
        except (ValueError, TypeError, json.JSONDecodeError, AttributeError):
            continue

    group_grades = (
        GroupGrade.query.join(GroupAssignment)
        .filter(
            GroupGrade.student_id == student_id,
            GroupAssignment.class_id == class_obj.id,
            GroupAssignment.school_year_id == school_year_id,
        )
        .all()
    )
    for g in group_grades:
        if g.is_voided or (g.group_assignment and g.group_assignment.status == "Voided"):
            continue
        try:
            grade_data = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
            points_earned = _get_points_earned(grade_data)
            if points_earned is None:
                continue
            points_earned = float(points_earned)
            total_points = (
                g.group_assignment.total_points
                if (g.group_assignment and g.group_assignment.total_points)
                else 100.0
            )
            if total_points and total_points > 0:
                grade_percentages.append(points_earned / total_points * 100)
        except (ValueError, TypeError, json.JSONDecodeError, AttributeError):
            continue

    if not grade_percentages:
        return None
    return round(sum(grade_percentages) / len(grade_percentages), 1)


def _serialize_class(
    class_obj: Class,
    *,
    average: float | None,
    group_name: str | None,
    is_assistant: bool,
    archived: bool = False,
) -> dict[str, Any]:
    grade_display = None
    try:
        grade_display = class_obj.get_grade_levels_display() or "All Grades"
    except Exception:
        grade_display = "All Grades"

    letter_band = None
    if average is not None:
        if average >= 90:
            letter_band = "a"
        elif average >= 80:
            letter_band = "b"
        elif average >= 70:
            letter_band = "c"
        else:
            letter_band = "d"

    return {
        "id": class_obj.id,
        "name": class_obj.name,
        "subject": class_obj.subject or "General",
        "grade_levels_display": grade_display,
        "teacher_name": _teacher_name(class_obj),
        "average": average,
        "average_band": letter_band,
        "group_name": group_name,
        "is_assistant": is_assistant,
        "archived": archived,
        "links": {
            "open_class": f"/app/student/classes/{class_obj.id}",
            "assignments": f"/app/student/assignments?class_id={class_obj.id}",
            "assistant": f"/assistant/class/{class_obj.id}" if is_assistant else None,
        },
    }


def build_student_classes_payload() -> tuple[dict[str, Any] | None, str | None]:
    from studentroutes import get_student_class_groups_by_class_id

    if not getattr(current_user, "student_id", None):
        return None, "Student profile required"

    student = Student.query.get(current_user.student_id)
    if not student:
        return None, "Student not found"

    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not current_school_year:
        return {
            "has_active_school_year": False,
            "school_year_name": None,
            "classes": [],
            "archived_classes": [],
            "assistant_classes": [],
            "closure_phase_label": None,
            "assistant_console_url": "/assistant",
        }, None

    enrollments = (
        Enrollment.query.filter_by(student_id=student.id, is_active=True)
        .join(Class)
        .filter(Class.school_year_id == current_school_year.id)
        .options(joinedload(Enrollment.class_info).joinedload(Class.teacher))
        .all()
    )
    classes = [e.class_info for e in enrollments if e.class_info]

    closure_archived_classes: list[Class] = []
    closure_phase_label = None
    try:
        from services.school_year_closure import (
            ACCESS_HIDDEN,
            get_latest_closure_for_year,
            get_student_access_status,
        )

        status = get_student_access_status(current_user, current_school_year)
        active_closure = get_latest_closure_for_year(current_school_year.id)
        if active_closure:
            closure_phase_label = active_closure.phase
        if status == ACCESS_HIDDEN:
            closure_archived_classes = list(classes)
            classes = []
    except Exception:
        pass

    assistant_objs = [
        sa.class_info
        for sa in StudentAssistant.query.filter_by(student_id=student.id).all()
        if sa.class_info
    ]
    assistant_ids = {c.id for c in assistant_objs}

    class_groups = get_student_class_groups_by_class_id(student.id, [c.id for c in classes])

    def pack(class_list: list[Class], *, archived: bool) -> list[dict[str, Any]]:
        rows = []
        for c in class_list:
            group = class_groups.get(c.id) if not archived else None
            avg = None if archived else _avg_for_class(student.id, c, current_school_year.id)
            rows.append(
                _serialize_class(
                    c,
                    average=avg,
                    group_name=getattr(group, "name", None) if group else None,
                    is_assistant=c.id in assistant_ids,
                    archived=archived,
                )
            )
        rows.sort(key=lambda r: (r["name"] or "").lower())
        return rows

    return {
        "has_active_school_year": True,
        "school_year_name": current_school_year.name,
        "classes": pack(classes, archived=False),
        "archived_classes": pack(closure_archived_classes, archived=True),
        "assistant_classes": [
            {"id": c.id, "name": c.name, "hub_url": f"/assistant/class/{c.id}"}
            for c in assistant_objs
        ],
        "closure_phase_label": closure_phase_label,
        "assistant_console_url": "/assistant",
    }, None
