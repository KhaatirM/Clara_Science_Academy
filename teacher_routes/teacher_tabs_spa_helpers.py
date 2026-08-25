"""Teacher SPA payloads for students, assignments, attendance, schedule, calendar, and settings."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from flask import url_for
from flask_login import current_user
from sqlalchemy import func

from decorators import has_permission
from extensions import db
from management_routes.calendar_spa_helpers import build_calendar_month
from management_routes.classes import serialize_class_list_item
from management_routes.settings_spa_helpers import THEME_OPTIONS, query_settings_hub
from models import Assignment, Attendance, Class, Enrollment, GroupAssignment, SchoolYear, Student
from teacher_routes.classes_spa_helpers import (
    _teacher_accessible_classes,
    _teacher_classes_for_active_school_year,
)
from utils.school_timezone import get_school_now, get_school_today
from teacher_routes.utils import get_teacher_or_admin, is_admin
from utils.schedule_helpers import build_weekly_schedule, finalize_schedule_view
from utils.school_year_filters import (
    count_pending_extension_requests,
    count_pending_redo_requests,
    get_active_school_year,
)
from utils.student_roster import active_roster_student_filters, student_is_archived
from utils.user_roles import canonical_role_label
from utils.user_theme import get_effective_theme, get_site_theme_override


def _teacher_can_select_school_year() -> bool:
    """Teachers with assignments admin may browse closed years; others are active-year only."""
    if is_admin():
        return True
    return has_permission(current_user, "assignments_grades:manage")


def _grade_label(level: int | None) -> str:
    if level is None:
        return "N/A"
    if level == 0:
        return "K"
    suffix = "th"
    if level % 10 == 1 and level != 11:
        suffix = "st"
    elif level % 10 == 2 and level != 12:
        suffix = "nd"
    elif level % 10 == 3 and level != 13:
        suffix = "rd"
    return f"{level}{suffix}"


def _teacher_student_class_names(class_ids: list[int]) -> dict[int, list[str]]:
    if not class_ids:
        return {}
    rows = (
        db.session.query(Enrollment.student_id, Class.name)
        .join(Class, Enrollment.class_id == Class.id)
        .join(Student, Student.id == Enrollment.student_id)
        .filter(
            Enrollment.class_id.in_(class_ids),
            Enrollment.is_active.is_(True),
            active_roster_student_filters(),
        )
        .order_by(Class.name)
        .all()
    )
    names_by_student: dict[int, list[str]] = {}
    for student_id, class_name in rows:
        if not student_id:
            continue
        bucket = names_by_student.setdefault(int(student_id), [])
        label = (class_name or "").strip()
        if label and label not in bucket:
            bucket.append(label)
    return names_by_student


def _teacher_students() -> list[Student]:
    teacher = get_teacher_or_admin()
    classes = _teacher_classes_for_active_school_year(teacher)
    class_ids = [c.id for c in classes]
    if not class_ids:
        return []

    class_names_by_student = _teacher_student_class_names(class_ids)
    student_ids = list(class_names_by_student.keys())
    if not student_ids:
        return []

    students = (
        Student.query.filter(
            Student.id.in_(student_ids),
            active_roster_student_filters(),
        )
        .all()
    )
    students.sort(key=lambda s: ((s.last_name or "").lower(), (s.first_name or "").lower()))
    return students


def _serialize_teacher_student(student: Student, class_names: list[str] | None = None) -> dict[str, Any]:
    photo = (
        f"/static/uploads/{student.photo_filename}"
        if student.photo_filename
        else "/static/img/default_avatar.png"
    )
    dob_display = student.dob or None
    student_number = student.student_id or None
    return {
        "id": student.id,
        "first_name": student.first_name or "",
        "last_name": student.last_name or "",
        "full_name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
        "grade_level": student.grade_level,
        "grade_label": _grade_label(student.grade_level),
        "email": student.email or None,
        "student_id": student_number,
        "state_id": student_number,
        "address": student.address or None,
        "date_of_birth": dob_display,
        "date_of_birth_display": dob_display,
        "class_names": class_names or [],
        "photo_url": photo,
        "links": {
            "grades": f"/app/teacher/students/{student.id}/grades",
            "attendance": f"/app/teacher/students/{student.id}/attendance",
        },
    }


def build_teacher_students_payload() -> tuple[dict[str, Any] | None, str | None]:
    try:
        teacher = get_teacher_or_admin()
        classes = _teacher_classes_for_active_school_year(teacher)
        class_ids = [c.id for c in classes]
        class_names_by_student = _teacher_student_class_names(class_ids)
        students = _teacher_students()
        items = [
            _serialize_teacher_student(s, class_names_by_student.get(s.id, []))
            for s in students
        ]
        grade_levels = {s.grade_level for s in students if s.grade_level is not None}
        with_email = sum(1 for s in students if s.email)
        with_id = sum(1 for s in students if s.student_id)
        active_school_year = get_active_school_year()
        return (
            {
                "items": items,
                "stats": {
                    "total_students": len(items),
                    "grade_levels": len(grade_levels),
                    "with_email": with_email,
                    "with_id": with_id,
                    "total_classes": len(classes),
                },
                "meta": {
                    "active_school_year_id": active_school_year.id if active_school_year else None,
                    "active_school_year_name": active_school_year.name if active_school_year else None,
                    "has_active_school_year": active_school_year is not None,
                },
            },
            None,
        )
    except Exception as exc:
        return None, str(exc)


def build_teacher_assignments_hub_payload() -> tuple[dict[str, Any] | None, str | None]:
    try:
        can_select_school_year = _teacher_can_select_school_year()
        active_school_year = get_active_school_year()
        if can_select_school_year:
            classes = _teacher_accessible_classes(get_teacher_or_admin())
        else:
            classes = _teacher_classes_for_active_school_year(get_teacher_or_admin())
        class_ids = [c.id for c in classes]
        enrollment_counts = (
            dict(
                db.session.query(Enrollment.class_id, func.count(Enrollment.id))
                .join(Student, Student.id == Enrollment.student_id)
                .filter(
                    Enrollment.is_active.is_(True),
                    Enrollment.class_id.in_(class_ids),
                    active_roster_student_filters(),
                )
                .group_by(Enrollment.class_id)
                .all()
            )
            if class_ids
            else {}
        )
        assignment_counts = (
            dict(
                db.session.query(Assignment.class_id, func.count(Assignment.id))
                .filter(Assignment.class_id.in_(class_ids))
                .group_by(Assignment.class_id)
                .all()
            )
            if class_ids
            else {}
        )
        group_counts = (
            dict(
                db.session.query(GroupAssignment.class_id, func.count(GroupAssignment.id))
                .filter(GroupAssignment.class_id.in_(class_ids))
                .group_by(GroupAssignment.class_id)
                .all()
            )
            if class_ids
            else {}
        )

        items: list[dict[str, Any]] = []
        unique_students: set[int] = set()
        for cls in classes:
            base = serialize_class_list_item(
                cls,
                enrollment_count=enrollment_counts.get(cls.id, 0),
                assignment_count=assignment_counts.get(cls.id, 0) + group_counts.get(cls.id, 0),
            )
            enrollments = Enrollment.query.filter_by(class_id=cls.id, is_active=True).all()
            for e in enrollments:
                if e.student_id and e.student and not student_is_archived(e.student):
                    unique_students.add(e.student_id)
            items.append(
                {
                    **base,
                    "links": {
                        "open": f"/app/teacher/assignments-and-grades/{cls.id}",
                        "create_assignment": f"/app/teacher/assignments/create?class_id={cls.id}",
                    },
                }
            )

        all_school_years = SchoolYear.query.order_by(SchoolYear.start_date.desc()).all()
        if can_select_school_year:
            school_years = [
                {
                    "id": sy.id,
                    "name": sy.name,
                    "is_active": bool(sy.is_active),
                }
                for sy in all_school_years
            ]
        elif active_school_year:
            school_years = [
                {
                    "id": active_school_year.id,
                    "name": active_school_year.name,
                    "is_active": True,
                }
            ]
        else:
            school_years = []

        default_school_year_id = (
            active_school_year.id
            if active_school_year
            else (school_years[0]["id"] if school_years else None)
        )

        return (
            {
                "items": items,
                "school_years": school_years,
                "meta": {
                    "default_school_year_id": default_school_year_id,
                    "active_school_year_id": active_school_year.id if active_school_year else None,
                    "active_school_year_name": active_school_year.name if active_school_year else None,
                    "has_active_school_year": active_school_year is not None,
                    "can_select_school_year": can_select_school_year,
                },
                "hub": {
                    "extension_request_count": count_pending_extension_requests(),
                    "redo_request_count": count_pending_redo_requests(),
                },
                "stats": {
                    "total_classes": len(items),
                    "total_assignments": sum(i["assignment_count"] for i in items),
                    "total_students": len(unique_students),
                    "extension_requests": count_pending_extension_requests(),
                    "redo_requests": count_pending_redo_requests(),
                },
            },
            None,
        )
    except Exception as exc:
        return None, str(exc)


def build_teacher_assignments_class_payload(
    class_id: int,
    *,
    view_mode: str = "grades",
    sort_by: str = "due_date",
    sort_order: str = "desc",
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        from management_routes.assignments_spa_helpers import query_assignments_class
        from teacher_routes.utils import is_authorized_for_class

        class_obj = Class.query.get(class_id)
        if not class_obj:
            return None, "Class not found"
        if not is_admin() and not is_authorized_for_class(class_obj):
            return None, "Forbidden"

        return (
            query_assignments_class(
                class_id,
                view_mode,
                sort_by,
                sort_order,
                scope="teacher",
            ),
            None,
        )
    except Exception as exc:
        return None, str(exc)


def build_teacher_attendance_payload() -> tuple[dict[str, Any] | None, str | None]:
    try:
        classes = _teacher_classes_for_active_school_year(get_teacher_or_admin())
        today = get_school_today()
        items: list[dict[str, Any]] = []
        completed = 0
        for cls in classes:
            taken = (
                Attendance.query.filter_by(class_id=cls.id, date=today).first() is not None
            )
            if taken:
                completed += 1
            from utils.student_roster import active_class_roster_students_query

            enrollment_count = active_class_roster_students_query(cls.id).count()
            items.append(
                {
                    "id": cls.id,
                    "name": cls.name or "",
                    "subject": (cls.subject or "").strip() or "General",
                    "grade_levels_display": cls.get_grade_levels_display() or "N/A",
                    "enrollment_count": enrollment_count,
                    "attendance_taken_today": taken,
                    "links": {
                        "take": f"/app/teacher/attendance/take/{cls.id}",
                        "records": f"/app/teacher/attendance/records/{cls.id}",
                    },
                }
            )

        pending = len(items) - completed
        return (
            {
                "items": items,
                "stats": {
                    "total_classes": len(items),
                    "completed_today": completed,
                    "pending_today": pending,
                },
                "today_display": today.strftime("%A, %B %d, %Y"),
            },
            None,
        )
    except Exception as exc:
        return None, str(exc)


def _serialize_schedule_block(class_obj: Class, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "class_id": class_obj.id,
        "class_name": class_obj.name or "",
        "subject": (class_obj.subject or "").strip() or "General",
        "time_str": item.get("time_str") or "",
        "room": item.get("room") or "TBD",
        "student_count": item.get("student_count"),
        "is_now": bool(item.get("is_now")),
        "is_upcoming": bool(item.get("is_upcoming")),
        "links": {
            "view_class": f"/app/teacher/classes/{class_obj.id}",
        },
    }


def build_teacher_schedule_payload() -> tuple[dict[str, Any] | None, str | None]:
    try:
        classes = _teacher_classes_for_active_school_year(get_teacher_or_admin())
        weekly_schedule = build_weekly_schedule(classes, role="teacher")
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
            grid_rows.append(
                {
                    "time_label": row.get("time_label") or "",
                    "cells": cells,
                }
            )

        return (
            {
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
            },
            None,
        )
    except Exception as exc:
        return None, str(exc)


def build_teacher_calendar_payload(*, month: int | None, year: int | None) -> tuple[dict[str, Any] | None, str | None]:
    try:
        today = get_school_today()
        month = month or today.month
        year = year or today.year
        grid = build_calendar_month(year, month)
        active_school_year = SchoolYear.query.filter_by(is_active=True).first()
        return (
            {
                **grid,
                "active_school_year": (
                    {"id": active_school_year.id, "name": active_school_year.name}
                    if active_school_year
                    else None
                ),
                "read_only": True,
            },
            None,
        )
    except Exception as exc:
        return None, str(exc)


def build_teacher_settings_payload(*, user) -> dict[str, Any]:
    from models import User

    hub = query_settings_hub(user=user)
    db_user = User.query.get(user.id) if getattr(user, "id", None) else None
    role = canonical_role_label(getattr(user, "role", None))
    saved_theme = (db_user.theme_preference if db_user else None) or "default"
    site_override = get_site_theme_override()
    google_connected = bool(db_user and db_user.google_refresh_token)

    return {
        **hub,
        "role_canonical": role,
        "is_director": False,
        "account": {
            "username": user.username,
            "email": getattr(user, "email", None),
            "role": getattr(user, "role", None),
        },
        "preferences": {
            "theme": get_effective_theme(db_user or user),
            "saved_theme": saved_theme,
            "theme_locked": bool(site_override),
            "site_theme_override": site_override,
            "theme_options": THEME_OPTIONS,
            "notifications_coming_soon": True,
            "timezone_coming_soon": True,
        },
        "google": {
            "connected": google_connected,
            "connect_url": url_for("teacher.google_connect_account"),
            "disconnect_url": url_for("teacher.google_disconnect_account"),
        },
        "urls": {
            "home": "/app/teacher",
            "change_password": "/change-password",
            "bug_reports_tab": "/app/teacher/settings/bug-reports",
        },
    }
