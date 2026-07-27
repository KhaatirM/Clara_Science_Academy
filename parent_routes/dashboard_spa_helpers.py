"""Parent / Family Portal SPA payloads."""

from __future__ import annotations

from typing import Any

from flask import session
from flask_login import current_user

from models import Student, TeacherStaff
from management_routes.settings_spa_helpers import THEME_OPTIONS
from utils.parent_portal import (
    build_child_academic_summary,
    get_active_school_year,
    get_linked_students,
    parent_display_name,
    parent_has_access,
)
from utils.report_card_portal import get_parent_visible_report_cards
from utils.user_theme import get_effective_theme, get_site_theme_override


def resolve_active_child_id() -> int | None:
    children = get_linked_students(current_user.id)
    if not children:
        return None
    raw = session.get("parent_active_student_id")
    if raw is not None:
        try:
            sid = int(raw)
            if parent_has_access(current_user.id, sid):
                return sid
        except (TypeError, ValueError):
            pass
    session["parent_active_student_id"] = children[0].id
    return children[0].id


def _serialize_child(student: Student) -> dict[str, Any]:
    return {
        "id": student.id,
        "first_name": student.first_name or "",
        "last_name": student.last_name or "",
        "display_name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
        "student_id": student.student_id or None,
        "grade_level": student.grade_level,
        "initial": ((student.first_name or student.last_name or "S")[0] or "S").upper(),
    }


def _teacher_name(class_obj) -> str:
    teacher = None
    if getattr(class_obj, "teacher_id", None):
        teacher = TeacherStaff.query.get(class_obj.teacher_id)
    if not teacher:
        return "Not assigned"
    return f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() or "Not assigned"


def _serialize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    student = summary.get("student")
    school_year = summary.get("school_year")
    classes = summary.get("classes") or []
    class_grades = summary.get("class_grades") or {}
    recent = summary.get("recent_grades") or []
    attendance_summary = summary.get("attendance_summary") or {}

    class_rows = []
    for c in classes:
        class_rows.append(
            {
                "id": c.id,
                "name": c.name,
                "subject": c.subject or "",
                "teacher_name": _teacher_name(c),
                "room": c.room_number or None,
                "schedule": c.schedule or None,
                "average": class_grades.get(c.name),
            }
        )

    recent_out = []
    for row in recent:
        graded_at = row.get("graded_at")
        recent_out.append(
            {
                "assignment_title": row.get("assignment_title") or "Assignment",
                "class_name": row.get("class_name") or "",
                "percentage": row.get("percentage"),
                "graded_at": graded_at.isoformat() if graded_at else None,
                "graded_at_display": graded_at.strftime("%b %d, %Y") if graded_at else None,
            }
        )

    return {
        "student": _serialize_child(student) if student else None,
        "school_year": (
            {"id": school_year.id, "name": school_year.name}
            if school_year
            else None
        ),
        "gpa": float(summary.get("gpa") or 0),
        "attendance_summary": {
            "Present": int(attendance_summary.get("Present") or 0),
            "Tardy": int(attendance_summary.get("Tardy") or 0),
            "Absent": int(attendance_summary.get("Absent") or 0),
        },
        "attendance_rate": summary.get("attendance_rate"),
        "classes": class_rows,
        "recent_grades": recent_out,
    }


def build_parent_bootstrap_payload() -> dict[str, Any]:
    children = get_linked_students(current_user.id)
    active_id = resolve_active_child_id()
    active = next((c for c in children if c.id == active_id), None)
    school_year = get_active_school_year()
    return {
        "parent_display_name": parent_display_name(current_user),
        "children": [_serialize_child(c) for c in children],
        "active_child_id": active_id,
        "active_child": _serialize_child(active) if active else None,
        "school_year": (
            {"id": school_year.id, "name": school_year.name}
            if school_year
            else None
        ),
        "has_active_school_year": school_year is not None,
        "links": {
            "home": "/app/parent",
            "grades": "/app/parent/grades",
            "attendance": "/app/parent/attendance",
            "classes": "/app/parent/classes",
            "report_cards": "/app/parent/report-cards",
            "settings": "/app/parent/settings",
        },
    }


def select_active_child(student_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    if not parent_has_access(current_user.id, student_id):
        return None, "Access denied", 403
    session["parent_active_student_id"] = student_id
    return build_parent_bootstrap_payload(), None, 200


def build_parent_home_payload() -> tuple[dict[str, Any] | None, str | None, int]:
    bootstrap = build_parent_bootstrap_payload()
    children = get_linked_students(current_user.id)
    if not children:
        return {
            **bootstrap,
            "summary": None,
            "report_card_count": 0,
        }, None, 200

    active_id = bootstrap.get("active_child_id")
    if not active_id:
        return {**bootstrap, "summary": None, "report_card_count": 0}, None, 200

    summary = _serialize_summary(build_child_academic_summary(active_id))
    report_card_count = len(get_parent_visible_report_cards(active_id))
    return {
        **bootstrap,
        "summary": summary,
        "report_card_count": report_card_count,
    }, None, 200


def build_parent_tab_payload(tab: str) -> tuple[dict[str, Any] | None, str | None, int]:
    bootstrap = build_parent_bootstrap_payload()
    active_id = bootstrap.get("active_child_id")
    if not active_id:
        return {**bootstrap, "summary": None, "report_cards": []}, None, 200

    if tab == "report-cards":
        cards = get_parent_visible_report_cards(active_id)
        report_cards = []
        for rc in cards:
            report_cards.append(
                {
                    "id": rc.id,
                    "quarter": rc.quarter,
                    "school_year_id": rc.school_year_id,
                    "generated_at": rc.generated_at.isoformat() if rc.generated_at else None,
                    "generated_at_display": (
                        rc.generated_at.strftime("%b %d, %Y") if rc.generated_at else None
                    ),
                    "approved_at": rc.approved_at.isoformat() if rc.approved_at else None,
                    "download_url": f"/api/spa/parent/report-cards/{rc.id}/pdf",
                }
            )
        return {**bootstrap, "report_cards": report_cards}, None, 200

    summary = _serialize_summary(build_child_academic_summary(active_id))
    return {**bootstrap, "summary": summary}, None, 200


def build_parent_settings_payload() -> dict[str, Any]:
    site_override = get_site_theme_override()
    saved_theme = getattr(current_user, "theme_preference", None) or "default"
    return {
        "account": {
            "username": current_user.username,
            "email": getattr(current_user, "email", None),
            "display_name": parent_display_name(current_user),
            "role": "Parent",
        },
        "preferences": {
            "saved_theme": saved_theme,
            "theme": get_effective_theme(current_user),
            "theme_locked": bool(site_override),
            "theme_options": THEME_OPTIONS,
        },
        "children": [_serialize_child(c) for c in get_linked_students(current_user.id)],
    }
