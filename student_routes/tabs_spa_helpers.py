"""Student schedule, calendar, jobs, and settings payloads for the React SPA."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from flask_login import current_user

from management_routes.bug_reports_spa_helpers import query_bug_reports
from management_routes.calendar_spa_helpers import build_calendar_month
from management_routes.settings_spa_helpers import THEME_OPTIONS
from management_routes.student_jobs_spa_helpers import query_student_jobs_hub
from models import Assignment, Class, Enrollment, Grade, SchoolYear, Student, User
from utils.schedule_helpers import build_weekly_schedule, finalize_schedule_view
from utils.school_year_filters import get_active_school_year, student_classes_for_school_year
from utils.user_theme import get_effective_theme, get_site_theme_override
from utils.school_timezone import get_school_now, get_school_today


def _serialize_schedule_block(class_obj: Class, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "class_id": class_obj.id,
        "class_name": class_obj.name or "",
        "subject": (class_obj.subject or "").strip() or "General",
        "time_str": item.get("time_str") or "",
        "room": item.get("room") or "TBD",
        "teacher_name": item.get("teacher_name") or "TBD",
        "is_now": bool(item.get("is_now")),
        "is_upcoming": bool(item.get("is_upcoming")),
        "links": {
            "view_class": f"/app/student/classes/{class_obj.id}",
        },
    }


def build_student_schedule_payload() -> tuple[dict[str, Any] | None, str | None]:
    try:
        sid = getattr(current_user, "student_id", None)
        if not sid:
            return None, "Student profile required"
        active_year = get_active_school_year()
        classes = student_classes_for_school_year(sid, active_year) if active_year else []
        weekly_schedule = build_weekly_schedule(classes, role="student")
        weekly_schedule, today_weekday, insights, schedule_grid = finalize_schedule_view(weekly_schedule)

        days: list[dict[str, Any]] = []
        for day_num in range(7):
            day_data = weekly_schedule.get(day_num) or {"day_name": "", "schedules": []}
            blocks = []
            for item in day_data.get("schedules") or []:
                class_obj = item.get("class")
                if class_obj:
                    blocks.append(_serialize_schedule_block(class_obj, item))
            days.append(
                {
                    "day_index": day_num,
                    "day_name": day_data.get("day_name") or "",
                    "is_today": day_num == today_weekday,
                    "blocks": blocks,
                }
            )

        grid_rows: list[dict[str, Any]] = []
        for row in schedule_grid:
            cells: list[list[dict[str, Any]]] = []
            for day_num in range(7):
                cell_items = []
                for item in (row.get("cells") or {}).get(day_num) or []:
                    class_obj = item.get("class")
                    if class_obj:
                        cell_items.append(_serialize_schedule_block(class_obj, item))
                cells.append(cell_items)
            grid_rows.append({"time_label": row.get("time_label") or "", "cells": cells})

        return {
            "days": days,
            "grid_rows": grid_rows,
            "today_weekday": today_weekday,
            "today_display": get_school_now().strftime("%A, %B %d, %Y"),
            "stats": {
                "today_blocks": insights.get("today_blocks", 0),
                "total_blocks": insights.get("total_blocks", 0),
                "active_days": insights.get("active_days", 0),
                "unique_classes": insights.get("unique_classes", 0),
            },
            "links": {"calendar": "/app/student/calendar"},
        }, None
    except Exception as exc:
        return None, str(exc)


def build_student_calendar_payload(
    *, month: int | None, year: int | None
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        today = get_school_today()
        month = month or today.month
        year = year or today.year
        grid = build_calendar_month(year, month)
        active_school_year = SchoolYear.query.filter_by(is_active=True).first()
        return {
            **grid,
            "active_school_year": (
                {"id": active_school_year.id, "name": active_school_year.name}
                if active_school_year
                else None
            ),
            "read_only": True,
        }, None
    except Exception as exc:
        return None, str(exc)


def build_student_jobs_payload() -> tuple[dict[str, Any] | None, str | None]:
    try:
        hub = query_student_jobs_hub(user=current_user)
        hub["can_manage"] = False
        hub["urls"] = {"home": "/app/student"}
        return hub, None
    except Exception as exc:
        return None, str(exc)


def _student_gpa(student: Student, school_year: SchoolYear | None) -> float:
    from .routes import _get_points_earned, calculate_gpa

    if not school_year:
        return 0.0
    enrollments = (
        Enrollment.query.filter_by(student_id=student.id, is_active=True)
        .join(Class)
        .filter(Class.school_year_id == school_year.id)
        .all()
    )
    all_percentages: list[float] = []
    for enrollment in enrollments:
        class_grades = (
            Grade.query.join(Assignment)
            .filter(
                Grade.student_id == student.id,
                Assignment.class_id == enrollment.class_id,
                Assignment.school_year_id == school_year.id,
            )
            .all()
        )
        class_pcts: list[float] = []
        for g in class_grades:
            if g.is_voided or (g.assignment and g.assignment.status == "Voided"):
                continue
            try:
                grade_data = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
            except (json.JSONDecodeError, TypeError):
                continue
            points = _get_points_earned(grade_data)
            if points is None:
                continue
            total = (
                g.assignment.total_points
                if g.assignment and g.assignment.total_points
                else 100.0
            )
            try:
                class_pcts.append(float(points) / float(total) * 100 if total else 0)
            except (ValueError, TypeError, ZeroDivisionError):
                continue
        if class_pcts:
            all_percentages.append(sum(class_pcts) / len(class_pcts))
    return float(calculate_gpa(all_percentages) or 0) if all_percentages else 0.0


def build_student_settings_payload(*, user) -> dict[str, Any]:
    sid = getattr(user, "student_id", None)
    student = Student.query.get(sid) if sid else None
    db_user = User.query.get(user.id) if getattr(user, "id", None) else None
    school_year = SchoolYear.query.filter_by(is_active=True).first()
    enrollment_count = 0
    if student and school_year:
        enrollment_count = (
            Enrollment.query.filter_by(student_id=student.id, is_active=True)
            .join(Class)
            .filter(Class.school_year_id == school_year.id)
            .count()
        )

    threshold = getattr(db_user or user, "low_grade_threshold", None)
    if threshold is None:
        threshold = 70

    site_override = get_site_theme_override()
    saved_theme = (db_user.theme_preference if db_user else None) or "default"

    return {
        "account": {
            "username": getattr(user, "username", None),
            "email": getattr(user, "email", None),
            "role": getattr(user, "role", None),
            "student": (
                {
                    "id": student.id,
                    "state_id": getattr(student, "student_id", None),
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "full_name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
                    "grade_level": student.grade_level,
                }
                if student
                else None
            ),
        },
        "preferences": {
            "theme": get_effective_theme(db_user or user),
            "saved_theme": saved_theme,
            "theme_locked": bool(site_override),
            "site_theme_override": site_override,
            "theme_options": THEME_OPTIONS,
            "low_grade_threshold": int(threshold),
            "notifications_coming_soon": True,
            "language_coming_soon": True,
        },
        "academic": {
            "school_year": (
                {"id": school_year.id, "name": school_year.name} if school_year else None
            ),
            "enrollment_count": enrollment_count,
            "gpa": round(_student_gpa(student, school_year), 2) if student else 0.0,
        },
        "urls": {
            "home": "/app/student",
            "change_password": "/change-password",
            "bug_reports_tab": "/app/student/settings/bug-reports",
        },
    }


def build_student_bug_reports_payload(*, user) -> dict[str, Any]:
    return query_bug_reports(user=user)
