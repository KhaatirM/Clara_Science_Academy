"""Student home dashboard payload for the React SPA."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from flask_login import current_user
from sqlalchemy.orm import joinedload

from management_routes.student_assistant_utils import (
    active_assistant_classes_for_student,
    assignment_student_visibility_filter,
)
from models import (
    Announcement,
    Assignment,
    Attendance,
    Class,
    ClassSchedule,
    Enrollment,
    Grade,
    GroupAssignment,
    GroupGrade,
    Notification,
    SchoolYear,
    Student,
    StudentGoal,
)


def _display_grade_label(grade_level) -> str:
    if grade_level == 0:
        return "K"
    if grade_level is not None:
        return str(grade_level)
    return "N/A"


def _iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _empty_payload(student: Student, *, has_active_school_year: bool, latest_label: str | None) -> dict[str, Any]:
    return {
        "has_active_school_year": has_active_school_year,
        "latest_school_year_label": latest_label,
        "home_display_date": datetime.now().strftime("%A, %B %d, %Y"),
        "profile": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "display_name": f"{student.first_name} {student.last_name}".strip(),
            "state_id": getattr(student, "state_id", None) or getattr(student, "student_id", None),
            "grade_level": student.grade_level,
            "grade_display": _display_grade_label(student.grade_level),
            "dob": str(student.dob) if student.dob else None,
            "email": student.email,
        },
        "stats": {
            "gpa": 0.0,
            "class_count": 0,
            "upcoming_count": 0,
            "grade_display": _display_grade_label(student.grade_level),
        },
        "attendance_summary": {"Present": 0, "Tardy": 0, "Absent": 0},
        "failing_classes": [],
        "up_next_items": [],
        "announcements": [],
        "goals": [],
        "upcoming_assignments": [],
        "past_due_assignments": [],
        "notifications": [],
        "assistant_classes": [],
        "links": {
            "assignments": "/app/student/assignments",
            "classes": "/student/classes",
            "grades": "/app/student/grades",
            "assistant_console": "/assistant",
        },
    }


def build_student_home_payload(student_id: int | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """Build JSON-serializable student home dashboard payload."""
    from .routes import _get_points_earned, calculate_gpa, get_grade_trends

    try:
        sid = student_id or getattr(current_user, "student_id", None)
        if not sid:
            return None, "No student profile linked to this account"
        student = Student.query.get(sid)
        if not student:
            return None, "Student not found"
    except Exception as exc:
        return None, str(exc)

    latest_year = SchoolYear.query.order_by(SchoolYear.start_date.desc()).first()
    latest_label = latest_year.name if latest_year else None
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not current_school_year:
        return _empty_payload(student, has_active_school_year=False, latest_label=latest_label), None

    enrollments = (
        Enrollment.query.filter_by(student_id=student.id, is_active=True)
        .join(Class)
        .filter(Class.school_year_id == current_school_year.id)
        .all()
    )
    classes = [enrollment.class_info for enrollment in enrollments if enrollment.class_info]
    class_ids = [c.id for c in classes]

    grades_by_name: dict[str, float] = {}
    all_grades: list[float] = []
    for c in classes:
        class_grades = (
            Grade.query.join(Assignment)
            .filter(
                Grade.student_id == student.id,
                Assignment.class_id == c.id,
                Assignment.school_year_id == current_school_year.id,
            )
            .all()
        )
        grade_percentages: list[float] = []
        for g in class_grades:
            if g.is_voided or (g.assignment and g.assignment.status == "Voided"):
                continue
            try:
                grade_data = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
            except (json.JSONDecodeError, TypeError):
                continue
            score = _get_points_earned(grade_data)
            if score is None:
                continue
            total_points = g.assignment.total_points if g.assignment and g.assignment.total_points else 100.0
            if not total_points:
                continue
            try:
                grade_percentages.append(float(score) / float(total_points) * 100)
            except (ValueError, TypeError, ZeroDivisionError):
                continue

        group_grades_home = (
            GroupGrade.query.join(GroupAssignment)
            .filter(
                GroupGrade.student_id == student.id,
                GroupAssignment.class_id == c.id,
                GroupAssignment.school_year_id == current_school_year.id,
            )
            .all()
        )
        for g in group_grades_home:
            if g.is_voided or (g.group_assignment and g.group_assignment.status == "Voided"):
                continue
            try:
                gdata = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
                score = _get_points_earned(gdata)
                if score is None:
                    continue
                total_points = (
                    g.group_assignment.total_points
                    if (g.group_assignment and g.group_assignment.total_points)
                    else 100.0
                )
                if total_points:
                    grade_percentages.append(float(score) / float(total_points) * 100)
            except (ValueError, TypeError, json.JSONDecodeError, AttributeError, ZeroDivisionError):
                continue

        if grade_percentages:
            avg_grade = round(sum(grade_percentages) / len(grade_percentages), 2)
            grades_by_name[c.name] = avg_grade
            all_grades.append(avg_grade)
            # Keep trends available for future SPA use without bloating payload today
            _ = get_grade_trends(student.id, c.id)

    gpa = float(calculate_gpa(all_grades) or 0)

    goals_rows = StudentGoal.query.filter_by(student_id=student.id).all()
    goals_by_class = {goal.class_id: goal for goal in goals_rows}

    today = datetime.now()
    today_weekday = today.weekday()
    today_schedule = []
    for c in classes:
        schedule = ClassSchedule.query.filter_by(class_id=c.id, day_of_week=today_weekday).first()
        if schedule:
            today_schedule.append(
                {
                    "class_id": c.id,
                    "class_name": c.name,
                    "time": f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}",
                    "room": schedule.room or "TBD",
                    "teacher": (
                        f"{c.teacher.first_name} {c.teacher.last_name}" if c.teacher else "TBD"
                    ),
                }
            )

    attendance_records = (
        Attendance.query.filter_by(student_id=student.id)
        .filter(
            Attendance.date >= current_school_year.start_date,
            Attendance.date <= current_school_year.end_date,
        )
        .all()
    )
    attendance_summary = {
        "Present": len([r for r in attendance_records if r.status == "Present"]),
        "Tardy": len([r for r in attendance_records if r.status == "Tardy"]),
        "Absent": len([r for r in attendance_records if r.status == "Absent"]),
    }

    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.timestamp.desc())
        .limit(10)
        .all()
    )

    assignments = []
    if class_ids:
        assignments = Assignment.query.filter(
            Assignment.class_id.in_(class_ids),
            Assignment.school_year_id == current_school_year.id,
            Assignment.status.in_(["Active", "Upcoming"]),
            assignment_student_visibility_filter(),
        ).all()

    past_due_assignments = []
    upcoming_assignments = []
    for assignment in assignments:
        grade = (
            Grade.query.filter_by(student_id=student.id, assignment_id=assignment.id)
            .order_by(Grade.graded_at.desc())
            .first()
        )
        if assignment.due_date and not grade:
            due_date = assignment.due_date.date() if hasattr(assignment.due_date, "date") else assignment.due_date
            today_date = today.date()
            if due_date < today_date:
                past_due_assignments.append(assignment)
            elif due_date <= today_date + timedelta(days=7):
                upcoming_assignments.append(assignment)

    failing_classes = []
    for c in classes:
        avg = grades_by_name.get(c.name)
        if avg is not None and float(avg) < 70:
            failing_classes.append(
                {
                    "class_id": c.id,
                    "class_name": c.name,
                    "average": round(float(avg), 1),
                    "url": f"/app/student/classes/{c.id}",
                }
            )

    today_date = today.date()
    up_next_items = []
    for a in past_due_assignments:
        due_date = a.due_date.date() if hasattr(a.due_date, "date") else a.due_date
        up_next_items.append(
            {
                "assignment_id": a.id,
                "title": a.title,
                "class_id": a.class_id,
                "class_name": a.class_info.name if a.class_info else "N/A",
                "days_offset": (today_date - due_date).days,
                "urgency": "overdue",
                "url": f"/app/student/assignments?class_id={a.class_id}",
            }
        )
    for a in upcoming_assignments:
        due_date = a.due_date.date() if hasattr(a.due_date, "date") else a.due_date
        days_offset = (due_date - today_date).days
        up_next_items.append(
            {
                "assignment_id": a.id,
                "title": a.title,
                "class_id": a.class_id,
                "class_name": a.class_info.name if a.class_info else "N/A",
                "days_offset": days_offset,
                "urgency": "due_today" if days_offset == 0 else "due_soon",
                "url": f"/app/student/assignments?class_id={a.class_id}",
            }
        )
    up_next_items = up_next_items[:5]

    announcements_q = Announcement.query.options(
        joinedload(Announcement.class_info),
        joinedload(Announcement.sender),
    )
    if class_ids:
        announcements_q = announcements_q.filter(
            (Announcement.target_group.in_(["all_students", "all"]))
            | ((Announcement.target_group == "class") & (Announcement.class_id.in_(class_ids)))
        )
    else:
        announcements_q = announcements_q.filter(Announcement.target_group.in_(["all_students", "all"]))
    announcements = announcements_q.order_by(Announcement.timestamp.desc()).limit(100).all()

    assistant_for_classes = active_assistant_classes_for_student(
        student.id, active_school_year=current_school_year
    )

    goals_payload = []
    for c in classes[:5]:
        goal = goals_by_class.get(c.id)
        current_grade = float(grades_by_name.get(c.name, 0) or 0)
        target = float(goal.target_grade) if goal else None
        progress = None
        if target and target > 0:
            progress = round(min((current_grade / target) * 100, 100), 1)
        goals_payload.append(
            {
                "class_id": c.id,
                "class_name": c.name,
                "current_grade": round(current_grade, 1),
                "goal_id": goal.id if goal else None,
                "target_grade": target,
                "progress_pct": progress,
            }
        )

    return (
        {
            "has_active_school_year": True,
            "latest_school_year_label": latest_label,
            "school_year_name": current_school_year.name,
            "home_display_date": datetime.now().strftime("%A, %B %d, %Y"),
            "profile": {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "display_name": f"{student.first_name} {student.last_name}".strip(),
                "state_id": getattr(student, "state_id", None) or getattr(student, "student_id", None),
                "grade_level": student.grade_level,
                "grade_display": _display_grade_label(student.grade_level),
                "dob": str(student.dob) if student.dob else None,
                "email": student.email,
            },
            "stats": {
                "gpa": round(gpa, 2),
                "class_count": len(classes),
                "upcoming_count": len(upcoming_assignments),
                "grade_display": _display_grade_label(student.grade_level),
            },
            "attendance_summary": attendance_summary,
            "today_schedule": today_schedule,
            "failing_classes": failing_classes,
            "up_next_items": up_next_items,
            "announcements": [
                {
                    "id": a.id,
                    "title": a.title,
                    "message": a.message or "",
                    "preview": ((a.message or "")[:120] + ("…" if a.message and len(a.message) > 120 else "")),
                    "is_important": bool(a.is_important),
                    "is_schoolwide": a.target_group in ("all_students", "all"),
                    "audience_label": (
                        "Entire student assembly"
                        if a.target_group in ("all_students", "all")
                        else (a.class_info.name if a.class_info else "Class")
                    ),
                    "class_id": a.class_id,
                    "timestamp": _iso(a.timestamp),
                    "timestamp_display": (
                        a.timestamp.strftime("%b %d, %I:%M %p") if a.timestamp else ""
                    ),
                    "timestamp_full": (
                        a.timestamp.strftime("%B %d, %Y at %I:%M %p") if a.timestamp else ""
                    ),
                }
                for a in announcements
            ],
            "goals": goals_payload,
            "upcoming_assignments": [
                {
                    "id": a.id,
                    "title": a.title,
                    "class_id": a.class_id,
                    "class_name": a.class_info.name if a.class_info else "N/A",
                    "due_date": _iso(a.due_date),
                    "due_display": a.due_date.strftime("%m/%d") if a.due_date else "N/A",
                    "url": f"/app/student/assignments?class_id={a.class_id}",
                }
                for a in upcoming_assignments[:5]
            ],
            "past_due_assignments": [
                {
                    "id": a.id,
                    "title": a.title,
                    "class_id": a.class_id,
                    "class_name": a.class_info.name if a.class_info else "N/A",
                    "due_date": _iso(a.due_date),
                    "due_display": a.due_date.strftime("%b %d, %Y") if a.due_date else "N/A",
                    "url": f"/app/student/assignments?class_id={a.class_id}",
                }
                for a in past_due_assignments[:5]
            ],
            "notifications": [
                {
                    "id": n.id,
                    "type": n.type,
                    "title": n.title,
                    "message": n.message or "",
                    "preview": (
                        ((n.message or "")[:120] + ("…" if n.message and len(n.message) > 120 else ""))
                    ),
                    "is_long": bool(n.message and len(n.message) > 120),
                    "timestamp": _iso(n.timestamp),
                    "timestamp_display": (
                        n.timestamp.strftime("%b %d, %I:%M %p") if n.timestamp else "Recently"
                    ),
                }
                for n in notifications[:5]
            ],
            "assistant_classes": [
                {
                    "id": c.id,
                    "name": c.name,
                    "url": f"/assistant/class/{c.id}",
                }
                for c in assistant_for_classes
            ],
            "links": {
                "assignments": "/app/student/assignments",
                "classes": "/student/classes",
                "grades": "/app/student/grades",
                "assistant_console": "/assistant",
            },
        },
        None,
    )


def set_student_goal(student_id: int, class_id: int, target_grade: float) -> dict[str, Any]:
    from extensions import db

    existing = StudentGoal.query.filter_by(student_id=student_id, class_id=class_id).first()
    if existing:
        existing.target_grade = target_grade
        existing.updated_at = datetime.utcnow()
        db.session.commit()
        return {"success": True, "message": "Goal updated successfully!", "goal_id": existing.id}
    goal = StudentGoal(student_id=student_id, class_id=class_id, target_grade=target_grade)
    db.session.add(goal)
    db.session.commit()
    return {"success": True, "message": "Goal set successfully!", "goal_id": goal.id}


def delete_student_goal(student_id: int, goal_id: int) -> dict[str, Any]:
    from extensions import db

    goal = StudentGoal.query.get(goal_id)
    if not goal:
        return {"success": False, "message": "Goal not found"}
    if goal.student_id != student_id:
        return {"success": False, "message": "Forbidden"}
    db.session.delete(goal)
    db.session.commit()
    return {"success": True, "message": "Goal removed"}
