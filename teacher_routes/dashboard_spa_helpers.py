"""Teacher home dashboard payload for the React SPA."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from flask import url_for
from flask_login import current_user

from extensions import db
from models import (
    Assignment,
    Class,
    Enrollment,
    Grade,
    Notification,
    SchoolYear,
    Student,
    Submission,
)

from utils.school_timezone import get_school_now, get_school_today
from management_routes.utils import update_assignment_statuses
from teacher_routes.utils import get_teacher_or_admin, is_admin


def _serialize_feed_timestamp(value) -> str | None:
    from management_routes.dashboard import _serialize_feed_timestamp as serialize

    return serialize(value)


def _home_display_date() -> str:
    return get_school_now().strftime("%A, %B %d, %Y")


def build_teacher_home_payload() -> tuple[dict[str, Any] | None, str | None]:
    try:
        update_assignment_statuses()
        teacher = get_teacher_or_admin()
    except Exception as exc:
        return None, str(exc)

    active_school_year = SchoolYear.query.filter_by(is_active=True).first()
    latest_year = SchoolYear.query.order_by(SchoolYear.start_date.desc()).first()
    latest_label = latest_year.name if latest_year else None

    if not active_school_year:
        return (
            _empty_payload(teacher, has_active_school_year=False, latest_school_year_label=latest_label),
            None,
        )

    if is_admin():
        classes = Class.query.filter_by(school_year_id=active_school_year.id).all()
        class_ids = [c.id for c in classes]
        recent_assignments = (
            Assignment.query.filter(Assignment.school_year_id == active_school_year.id)
            .order_by(Assignment.due_date.desc())
            .limit(5)
            .all()
        )
        assignments = Assignment.query.filter_by(school_year_id=active_school_year.id).all()
    elif teacher is None:
        classes = []
        class_ids = []
        recent_assignments = []
        assignments = []
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id, school_year_id=active_school_year.id).all()
        class_ids = [c.id for c in classes]
        recent_assignments = (
            Assignment.query.filter(
                Assignment.class_id.in_(class_ids),
                Assignment.school_year_id == active_school_year.id,
            )
            .order_by(Assignment.due_date.desc())
            .limit(5)
            .all()
            if class_ids
            else []
        )
        assignments = (
            Assignment.query.filter(
                Assignment.class_id.in_(class_ids),
                Assignment.school_year_id == active_school_year.id,
            ).all()
            if class_ids
            else []
        )

    recent_activity: list[dict[str, Any]] = []

    if class_ids:
        recent_submissions = (
            Submission.query.join(Assignment)
            .filter(Assignment.class_id.in_(class_ids))
            .order_by(Submission.submitted_at.desc())
            .limit(5)
            .all()
        )
    else:
        recent_submissions = []

    for submission in recent_submissions:
        try:
            if not submission.assignment or not submission.student:
                continue
            recent_activity.append(
                {
                    "type": "submission",
                    "title": f"New submission for {submission.assignment.title}",
                    "description": (
                        f"{submission.student.first_name} {submission.student.last_name} submitted work"
                    ),
                    "timestamp": submission.submitted_at or datetime.utcnow(),
                    "link": url_for(
                        "teacher.grading.grade_assignment",
                        assignment_id=submission.assignment_id,
                    ),
                }
            )
        except (AttributeError, TypeError):
            continue

    if class_ids:
        recent_grades_entered = (
            Grade.query.join(Assignment)
            .filter(Assignment.class_id.in_(class_ids))
            .order_by(Grade.graded_at.desc())
            .limit(5)
            .all()
        )
    else:
        recent_grades_entered = []

    for grade in recent_grades_entered:
        try:
            if not grade.assignment or not grade.student:
                continue
            grade_data = (
                json.loads(grade.grade_data)
                if isinstance(grade.grade_data, str)
                else grade.grade_data
            )
            score = grade_data.get("score", "N/A") if isinstance(grade_data, dict) else "N/A"
            recent_activity.append(
                {
                    "type": "grade",
                    "title": f"Grade entered for {grade.assignment.title}",
                    "description": (
                        f"Graded {grade.student.first_name} {grade.student.last_name} — Score: {score}"
                    ),
                    "timestamp": grade.graded_at or datetime.utcnow(),
                    "link": url_for(
                        "teacher.grading.grade_assignment",
                        assignment_id=grade.assignment_id,
                    ),
                }
            )
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    for assignment in recent_assignments:
        try:
            if not assignment.class_info:
                continue
            due_date_str = (
                assignment.due_date.strftime("%b %d, %Y") if assignment.due_date else "No due date"
            )
            recent_activity.append(
                {
                    "type": "assignment",
                    "title": f"New assignment: {assignment.title}",
                    "description": f"Created for {assignment.class_info.name} — Due: {due_date_str}",
                    "timestamp": assignment.created_at or datetime.utcnow(),
                    "link": url_for("teacher.dashboard.view_class", class_id=assignment.class_id),
                }
            )
        except (AttributeError, TypeError):
            continue

    recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
    recent_activity = recent_activity[:10]

    notification_rows = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.timestamp.desc())
        .limit(10)
        .all()
    )

    if class_ids:
        from utils.student_roster import active_roster_student_filters

        enrollments = (
            Enrollment.query.join(Student, Student.id == Enrollment.student_id)
            .filter(
                Enrollment.class_id.in_(class_ids),
                Enrollment.is_active.is_(True),
                active_roster_student_filters(),
            )
            .all()
        )
        total_students = len({e.student_id for e in enrollments})
        active_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).count()
        total_assignments = active_assignments
    else:
        total_students = 0
        active_assignments = 0
        total_assignments = 0

    now = get_school_now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    if class_ids:
        due_assignments = Assignment.query.filter(
            Assignment.class_id.in_(class_ids),
            Assignment.due_date.isnot(None),
            Assignment.due_date >= week_start,
            Assignment.due_date < week_end,
        ).count()
        grades_this_month = (
            Grade.query.join(Assignment)
            .filter(Assignment.class_id.in_(class_ids), Grade.graded_at >= month_start)
            .count()
        )
    else:
        due_assignments = 0
        grades_this_month = 0

    if teacher:
        display_name = f"{teacher.first_name or ''} {teacher.last_name or ''}".strip()
        initials = f"{(teacher.first_name or '?')[0]}{(teacher.last_name or '?')[0]}".upper()
        profile = {
            "display_name": display_name or current_user.username,
            "role": current_user.role,
            "email": teacher.email,
            "phone": teacher.phone,
            "initials": initials,
            "class_count": len(classes),
        }
    else:
        profile = {
            "display_name": current_user.username,
            "role": current_user.role,
            "email": getattr(current_user, "email", None),
            "phone": None,
            "initials": (current_user.username or "?")[0].upper(),
            "class_count": len(classes),
        }

    return (
        {
            "home_display_date": _home_display_date(),
            "has_active_school_year": True,
            "latest_school_year_label": latest_label,
            "is_admin": is_admin(),
            "profile": profile,
            "stats": {
                "classes": len(classes),
                "students": total_students,
                "active_assignments": active_assignments,
                "total_assignments": total_assignments,
                "notifications": len(notification_rows),
            },
            "monthly_stats": {"grades_entered": grades_this_month},
            "weekly_stats": {"due_assignments": due_assignments},
            "notifications": [
                {
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "timestamp": _serialize_feed_timestamp(n.timestamp),
                    "link": n.link,
                    "is_read": bool(n.is_read),
                }
                for n in notification_rows
            ],
            "recent_activity": [
                {
                    **item,
                    "timestamp": _serialize_feed_timestamp(item.get("timestamp")),
                }
                for item in recent_activity
            ],
        },
        None,
    )


def _empty_payload(
    teacher,
    *,
    has_active_school_year: bool,
    latest_school_year_label: str | None,
) -> dict[str, Any]:
    if teacher:
        display_name = f"{teacher.first_name or ''} {teacher.last_name or ''}".strip()
        initials = f"{(teacher.first_name or '?')[0]}{(teacher.last_name or '?')[0]}".upper()
        profile = {
            "display_name": display_name or current_user.username,
            "role": current_user.role,
            "email": teacher.email,
            "phone": teacher.phone,
            "initials": initials,
            "class_count": 0,
        }
    else:
        profile = {
            "display_name": current_user.username,
            "role": current_user.role,
            "email": getattr(current_user, "email", None),
            "phone": None,
            "initials": (current_user.username or "?")[0].upper(),
            "class_count": 0,
        }

    return {
        "home_display_date": _home_display_date(),
        "has_active_school_year": has_active_school_year,
        "latest_school_year_label": latest_school_year_label,
        "is_admin": is_admin(),
        "profile": profile,
        "stats": {
            "classes": 0,
            "students": 0,
            "active_assignments": 0,
            "total_assignments": 0,
            "notifications": 0,
        },
        "monthly_stats": {"grades_entered": 0},
        "weekly_stats": {"due_assignments": 0},
        "notifications": [],
        "recent_activity": [],
    }
