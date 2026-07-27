"""Student grades payload for the React SPA."""

from __future__ import annotations

import json
from typing import Any

from flask_login import current_user

from management_routes.student_assistant_utils import (
    assignment_student_visibility_filter,
    group_assignment_student_visibility_filter,
)
from models import (
    AcademicPeriod,
    Assignment,
    Class,
    Enrollment,
    Grade,
    GroupAssignment,
    GroupGrade,
    SchoolYear,
    Student,
)
from utils.gpa_period_visibility import period_gpa_visibility_state


def _standing(gpa: float) -> dict[str, str]:
    if gpa >= 3.5:
        return {"key": "honor", "label": "Honor Roll", "icon": "bi-award"}
    if gpa >= 3.0:
        return {"key": "good", "label": "Good Standing", "icon": "bi-check-circle"}
    if gpa >= 2.0:
        return {"key": "improve", "label": "Needs Improvement", "icon": "bi-exclamation-triangle"}
    return {"key": "warning", "label": "Academic Warning", "icon": "bi-x-circle"}


def _band(pct: float | None) -> str | None:
    if pct is None:
        return None
    if pct >= 90:
        return "a"
    if pct >= 80:
        return "b"
    if pct >= 70:
        return "c"
    return "d"


def _quarter_matches(assign_quarter, period_name) -> bool:
    if assign_quarter is None or assign_quarter == "":
        return False
    a = str(assign_quarter).strip().upper().replace("Q", "")
    b = str(period_name or "").strip().upper().replace("Q", "")
    return bool(a and b and a == b)


def _pct_from_grade(grade_data, total_points) -> float | None:
    from studentroutes import _get_points_earned

    if not isinstance(grade_data, dict):
        return None
    points_earned = _get_points_earned(grade_data)
    if points_earned is not None:
        try:
            total_pts = float(total_points) if total_points and float(total_points) > 0 else 100.0
            return (float(points_earned) / total_pts * 100) if total_pts > 0 else 0.0
        except (ValueError, TypeError, ZeroDivisionError):
            return None
    if grade_data.get("percentage") is not None:
        try:
            return float(grade_data["percentage"])
        except (ValueError, TypeError):
            return None
    return None


def _period_payload(
    *,
    name: str,
    status: str,
    end_date,
    average: float | None = None,
    letter: str | None = None,
    gpa: float | None = None,
    assignments: int = 0,
) -> dict[str, Any]:
    end_display = None
    try:
        if end_date and hasattr(end_date, "strftime"):
            end_display = end_date.strftime("%m/%d/%Y")
    except Exception:
        end_display = str(end_date) if end_date else None
    return {
        "name": name,
        "status": status,
        "average": average,
        "letter": letter,
        "gpa": round(float(gpa), 2) if gpa is not None else None,
        "assignments": assignments,
        "end_date": end_date.isoformat() if end_date and hasattr(end_date, "isoformat") else None,
        "end_display": end_display,
        "band": _band(average),
    }


def _aggregate_period_summaries(
    grades_by_class: list[dict[str, Any]],
    periods: list,
    visibility: dict[str, str],
) -> list[dict[str, Any]]:
    from studentroutes import calculate_gpa

    out: list[dict[str, Any]] = []
    for period in periods:
        name = period.name
        status = visibility.get(name) or "released"
        end_date = period.end_date
        if status == "in_progress":
            out.append(
                _period_payload(
                    name=name,
                    status="in_progress",
                    end_date=end_date,
                    letter="In Progress",
                )
            )
            continue
        if status == "calculating":
            out.append(
                _period_payload(
                    name=name,
                    status="calculating",
                    end_date=end_date,
                )
            )
            continue

        averages: list[float] = []
        for cls in grades_by_class:
            period_map = cls.get("periods") or {}
            row = period_map.get(name)
            if row and row.get("average") is not None:
                averages.append(float(row["average"]))

        if averages:
            avg = round(sum(averages) / len(averages), 1)
            out.append(
                _period_payload(
                    name=name,
                    status="released",
                    end_date=end_date,
                    average=avg,
                    letter=None,
                    gpa=calculate_gpa(averages),
                    assignments=len(averages),
                )
            )
        else:
            out.append(
                _period_payload(
                    name=name,
                    status="released",
                    end_date=end_date,
                    letter="No Grades",
                )
            )
    return out


def build_student_grades_payload() -> tuple[dict[str, Any] | None, str | None]:
    from studentroutes import _get_points_earned, calculate_gpa, get_letter_grade

    sid = getattr(current_user, "student_id", None)
    if not sid:
        return None, "Student profile required"
    student = Student.query.get(sid)
    if not student:
        return None, "Student not found"

    school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not school_year:
        return {
            "has_active_school_year": False,
            "school_year_name": None,
            "gpa": 0.0,
            "standing": _standing(0.0),
            "quarters": [],
            "semesters": [],
            "classes": [],
            "class_count": 0,
            "graded_class_count": 0,
        }, None

    academic_periods = (
        AcademicPeriod.query.filter_by(school_year_id=school_year.id, is_active=True)
        .order_by(AcademicPeriod.start_date)
        .all()
    )
    quarters = [p for p in academic_periods if p.period_type == "quarter"]
    semesters = [p for p in academic_periods if p.period_type == "semester"]
    gpa_quarter_visibility = {q.name: period_gpa_visibility_state(q.end_date) for q in quarters}
    gpa_semester_visibility = {s.name: period_gpa_visibility_state(s.end_date) for s in semesters}

    enrollments = (
        Enrollment.query.filter_by(student_id=student.id, is_active=True)
        .join(Class)
        .filter(Class.school_year_id == school_year.id)
        .all()
    )

    classes_out: list[dict[str, Any]] = []
    all_class_averages: list[float] = []

    for enrollment in enrollments:
        class_info = enrollment.class_info
        if not class_info:
            continue

        assignments = Assignment.query.filter(
            Assignment.class_id == class_info.id,
            Assignment.school_year_id == school_year.id,
            assignment_student_visibility_filter(),
        ).all()
        group_assignments = GroupAssignment.query.filter(
            GroupAssignment.class_id == class_info.id,
            GroupAssignment.school_year_id == school_year.id,
            group_assignment_student_visibility_filter(),
        ).all()
        if not assignments and not group_assignments:
            continue

        grades = (
            Grade.query.join(Assignment)
            .filter(
                Grade.student_id == student.id,
                Assignment.class_id == class_info.id,
                Assignment.school_year_id == school_year.id,
            )
            .order_by(Grade.graded_at.desc())
            .all()
        )
        group_grades = (
            GroupGrade.query.join(GroupAssignment)
            .filter(
                GroupGrade.student_id == student.id,
                GroupAssignment.class_id == class_info.id,
                GroupAssignment.school_year_id == school_year.id,
            )
            .order_by(GroupGrade.graded_at.desc())
            .all()
        )
        if not grades and not group_grades:
            continue

        assignment_details: list[dict[str, Any]] = []
        total_score = 0.0
        valid_grades = 0

        for grade in grades:
            if grade.is_voided or (grade.assignment and grade.assignment.status == "Voided"):
                continue
            try:
                grade_data = (
                    json.loads(grade.grade_data)
                    if isinstance(grade.grade_data, str)
                    else grade.grade_data
                )
            except (json.JSONDecodeError, TypeError):
                continue
            total_points = (
                grade.assignment.total_points
                if grade.assignment and grade.assignment.total_points
                else 100.0
            )
            percentage = _pct_from_grade(grade_data, total_points)
            if percentage is None:
                continue
            percentage = round(float(percentage), 1)
            total_score += percentage
            valid_grades += 1
            assignment_details.append(
                {
                    "title": grade.assignment.title if grade.assignment else "Assignment",
                    "percentage": percentage,
                    "display": f"{percentage}%",
                    "letter": get_letter_grade(percentage),
                    "band": _band(percentage),
                    "is_group": False,
                    "graded_at": grade.graded_at.isoformat() if grade.graded_at else None,
                }
            )

        for group_grade in group_grades:
            if group_grade.is_voided or (
                group_grade.group_assignment and group_grade.group_assignment.status == "Voided"
            ):
                continue
            try:
                grade_data = (
                    json.loads(group_grade.grade_data)
                    if isinstance(group_grade.grade_data, str)
                    else group_grade.grade_data
                )
            except (json.JSONDecodeError, TypeError):
                continue
            total_points = (
                group_grade.group_assignment.total_points
                if group_grade.group_assignment and group_grade.group_assignment.total_points
                else 100.0
            )
            percentage = _pct_from_grade(grade_data, total_points)
            if percentage is None:
                continue
            percentage = round(float(percentage), 1)
            total_score += percentage
            valid_grades += 1
            title = (
                f"{group_grade.group_assignment.title} (Group)"
                if group_grade.group_assignment
                else "Group assignment"
            )
            assignment_details.append(
                {
                    "title": title,
                    "percentage": percentage,
                    "display": f"{percentage}%",
                    "letter": get_letter_grade(percentage),
                    "band": _band(percentage),
                    "is_group": True,
                    "graded_at": group_grade.graded_at.isoformat() if group_grade.graded_at else None,
                }
            )

        if valid_grades <= 0:
            continue

        class_average = round(total_score / valid_grades, 2)
        all_class_averages.append(class_average)
        letter_grade = get_letter_grade(class_average)
        class_gpa = calculate_gpa([class_average])

        recent_raw: list[dict[str, Any]] = []
        for grade in grades:
            if grade.is_voided or (grade.assignment and grade.assignment.status == "Voided"):
                continue
            try:
                grade_data = (
                    json.loads(grade.grade_data)
                    if isinstance(grade.grade_data, str)
                    else grade.grade_data
                )
            except (json.JSONDecodeError, TypeError):
                continue
            score = _get_points_earned(grade_data)
            if score is None:
                continue
            total_points = (
                grade.assignment.total_points
                if grade.assignment and grade.assignment.total_points
                else 100.0
            )
            try:
                percentage = float(score) / float(total_points) * 100 if total_points else 0
            except (ValueError, TypeError, ZeroDivisionError):
                continue
            recent_raw.append(
                {
                    "title": grade.assignment.title if grade.assignment else "Assignment",
                    "score": round(percentage, 1),
                    "letter": get_letter_grade(percentage),
                    "band": _band(percentage),
                    "graded_at": grade.graded_at,
                    "graded_display": grade.graded_at.strftime("%b %d, %Y") if grade.graded_at else None,
                }
            )

        for group_grade in group_grades:
            if group_grade.is_voided or (
                group_grade.group_assignment and group_grade.group_assignment.status == "Voided"
            ):
                continue
            try:
                grade_data = (
                    json.loads(group_grade.grade_data)
                    if isinstance(group_grade.grade_data, str)
                    else group_grade.grade_data
                )
            except (json.JSONDecodeError, TypeError):
                continue
            total_points = (
                group_grade.group_assignment.total_points
                if group_grade.group_assignment and group_grade.group_assignment.total_points
                else 100.0
            )
            percentage = _pct_from_grade(grade_data, total_points)
            if percentage is None:
                continue
            recent_raw.append(
                {
                    "title": (
                        f"{group_grade.group_assignment.title} (Group)"
                        if group_grade.group_assignment
                        else "Group assignment"
                    ),
                    "score": round(float(percentage), 1),
                    "letter": get_letter_grade(percentage),
                    "band": _band(percentage),
                    "graded_at": group_grade.graded_at,
                    "graded_display": (
                        group_grade.graded_at.strftime("%b %d, %Y") if group_grade.graded_at else None
                    ),
                }
            )

        recent_raw.sort(
            key=lambda x: x["graded_at"].isoformat() if x["graded_at"] else "",
            reverse=True,
        )
        recent_assignments = [
            {
                "title": r["title"],
                "score": r["score"],
                "letter": r["letter"],
                "band": r["band"],
                "graded_display": r["graded_display"],
            }
            for r in recent_raw[:3]
        ]

        periods_map: dict[str, dict[str, Any]] = {}

        for quarter in quarters:
            q_vis = period_gpa_visibility_state(quarter.end_date)
            if q_vis == "in_progress":
                periods_map[quarter.name] = _period_payload(
                    name=quarter.name,
                    status="in_progress",
                    end_date=quarter.end_date,
                    letter="In Progress",
                )
                continue
            if q_vis == "calculating":
                periods_map[quarter.name] = _period_payload(
                    name=quarter.name,
                    status="calculating",
                    end_date=quarter.end_date,
                )
                continue

            quarter_grades_list: list[float] = []
            for assignment in assignments:
                if assignment.status == "Voided" or not _quarter_matches(assignment.quarter, quarter.name):
                    continue
                grade = next((g for g in grades if g.assignment_id == assignment.id), None)
                if not grade or grade.is_voided:
                    continue
                try:
                    grade_data = (
                        json.loads(grade.grade_data)
                        if isinstance(grade.grade_data, str)
                        else grade.grade_data
                    )
                except (json.JSONDecodeError, TypeError):
                    continue
                pct = _pct_from_grade(grade_data, assignment.total_points)
                if pct is not None:
                    quarter_grades_list.append(float(pct))

            for group_assignment in group_assignments:
                if group_assignment.status == "Voided" or not _quarter_matches(
                    group_assignment.quarter, quarter.name
                ):
                    continue
                group_grade = next(
                    (g for g in group_grades if g.group_assignment_id == group_assignment.id),
                    None,
                )
                if not group_grade or group_grade.is_voided:
                    continue
                try:
                    grade_data = (
                        json.loads(group_grade.grade_data)
                        if isinstance(group_grade.grade_data, str)
                        else group_grade.grade_data
                    )
                except (json.JSONDecodeError, TypeError):
                    continue
                pct = _pct_from_grade(grade_data, group_assignment.total_points)
                if pct is not None:
                    quarter_grades_list.append(float(pct))

            if quarter_grades_list:
                quarter_avg = round(sum(quarter_grades_list) / len(quarter_grades_list), 2)
                periods_map[quarter.name] = _period_payload(
                    name=quarter.name,
                    status="released",
                    end_date=quarter.end_date,
                    average=quarter_avg,
                    letter=get_letter_grade(quarter_avg),
                    gpa=calculate_gpa([quarter_avg]),
                    assignments=len(quarter_grades_list),
                )
            else:
                periods_map[quarter.name] = _period_payload(
                    name=quarter.name,
                    status="released",
                    end_date=quarter.end_date,
                    letter="No Grades",
                )

        for semester in semesters:
            s_vis = period_gpa_visibility_state(semester.end_date)
            if s_vis == "in_progress":
                periods_map[semester.name] = _period_payload(
                    name=semester.name,
                    status="in_progress",
                    end_date=semester.end_date,
                    letter="In Progress",
                )
                continue
            if s_vis == "calculating":
                periods_map[semester.name] = _period_payload(
                    name=semester.name,
                    status="calculating",
                    end_date=semester.end_date,
                )
                continue

            semester_assignments = []
            semester_group_assignments = []
            for assignment in assignments:
                if not assignment.due_date:
                    continue
                due = assignment.due_date.date() if hasattr(assignment.due_date, "date") else assignment.due_date
                if semester.name == "S1" and due <= semester.end_date:
                    semester_assignments.append(assignment)
                elif semester.name == "S2" and due > semester.start_date:
                    semester_assignments.append(assignment)

            for group_assignment in group_assignments:
                if not group_assignment.due_date:
                    continue
                due = (
                    group_assignment.due_date.date()
                    if hasattr(group_assignment.due_date, "date")
                    else group_assignment.due_date
                )
                if semester.name == "S1" and due <= semester.end_date:
                    semester_group_assignments.append(group_assignment)
                elif semester.name == "S2" and due > semester.start_date:
                    semester_group_assignments.append(group_assignment)

            semester_grades_list: list[float] = []
            for assignment in semester_assignments:
                if assignment.status == "Voided":
                    continue
                grade = next((g for g in grades if g.assignment_id == assignment.id), None)
                if not grade or grade.is_voided:
                    continue
                try:
                    grade_data = (
                        json.loads(grade.grade_data)
                        if isinstance(grade.grade_data, str)
                        else grade.grade_data
                    )
                except (json.JSONDecodeError, TypeError):
                    continue
                pct = _pct_from_grade(grade_data, assignment.total_points)
                if pct is not None:
                    semester_grades_list.append(float(pct))

            for group_assignment in semester_group_assignments:
                if group_assignment.status == "Voided":
                    continue
                group_grade = next(
                    (g for g in group_grades if g.group_assignment_id == group_assignment.id),
                    None,
                )
                if not group_grade or group_grade.is_voided:
                    continue
                try:
                    grade_data = (
                        json.loads(group_grade.grade_data)
                        if isinstance(group_grade.grade_data, str)
                        else group_grade.grade_data
                    )
                except (json.JSONDecodeError, TypeError):
                    continue
                pct = _pct_from_grade(grade_data, group_assignment.total_points)
                if pct is not None:
                    semester_grades_list.append(float(pct))

            if semester_grades_list:
                semester_avg = round(sum(semester_grades_list) / len(semester_grades_list), 2)
                periods_map[semester.name] = _period_payload(
                    name=semester.name,
                    status="released",
                    end_date=semester.end_date,
                    average=semester_avg,
                    letter=get_letter_grade(semester_avg),
                    gpa=calculate_gpa([semester_avg]),
                    assignments=len(semester_grades_list),
                )
            else:
                periods_map[semester.name] = _period_payload(
                    name=semester.name,
                    status="released",
                    end_date=semester.end_date,
                    letter="No Grades",
                )

        teacher = getattr(class_info, "teacher", None)
        teacher_name = "No teacher assigned"
        if teacher:
            teacher_name = (
                f"{getattr(teacher, 'first_name', '') or ''} {getattr(teacher, 'last_name', '') or ''}".strip()
                or "No teacher assigned"
            )

        quarter_names = {q.name for q in quarters}
        semester_names = {s.name for s in semesters}

        classes_out.append(
            {
                "id": class_info.id,
                "name": class_info.name,
                "subject": class_info.subject or "General",
                "teacher_name": teacher_name,
                "final_grade": {
                    "letter": letter_grade,
                    "percentage": class_average,
                    "band": _band(class_average),
                },
                "class_gpa": round(float(class_gpa or 0), 2),
                "graded_count": valid_grades,
                "recent_assignments": recent_assignments,
                "assignment_details": sorted(
                    assignment_details,
                    key=lambda x: x.get("title") or "",
                ),
                "quarter_grades": [periods_map[n] for n in sorted(quarter_names) if n in periods_map],
                "semester_grades": [periods_map[n] for n in sorted(semester_names) if n in periods_map],
                "periods": periods_map,
                "links": {
                    "open_class": f"/app/student/classes/{class_info.id}",
                    "assignments": f"/app/student/assignments?class_id={class_info.id}",
                },
            }
        )

    gpa = float(calculate_gpa(all_class_averages) or 0) if all_class_averages else 0.0

    quarter_summaries = _aggregate_period_summaries(classes_out, quarters, gpa_quarter_visibility)
    semester_summaries = _aggregate_period_summaries(classes_out, semesters, gpa_semester_visibility)

    for cls in classes_out:
        cls.pop("periods", None)

    return {
        "has_active_school_year": True,
        "school_year_name": school_year.name,
        "gpa": round(gpa, 2),
        "standing": _standing(gpa),
        "quarters": quarter_summaries,
        "semesters": semester_summaries,
        "classes": classes_out,
        "class_count": len(enrollments),
        "graded_class_count": len(classes_out),
    }, None
