"""Teacher class view (roster overview) payload for the React SPA."""

from __future__ import annotations

import json
from typing import Any

from flask import url_for

from extensions import db
from management_routes.class_spa_helpers import _standards_flags, serialize_student_brief
from management_routes.classes import serialize_class_list_item
from models import (
    Announcement,
    Assignment,
    Class,
    Enrollment,
    GroupAssignment,
    Student,
    StudentAssistant,
    StudentAssistantActionLog,
    User,
)
from services.class_google_group import class_needs_google_integration
from teacher_routes.utils import is_authorized_for_class


def _assignment_count(class_id: int) -> int:
    regular = Assignment.query.filter_by(class_id=class_id).count()
    try:
        group = GroupAssignment.query.filter_by(class_id=class_id).count()
    except Exception:
        group = 0
    return regular + group


def _teacher_class_view_links(class_id: int, features: dict[str, bool]) -> dict[str, str]:
    links: dict[str, str] = {
        "back_to_classes": "/app/teacher/classes",
        "add_assignment": f"/app/teacher/assignments/create?class_id={class_id}",
        "take_attendance": f"/app/teacher/attendance/take/{class_id}",
        "manage_groups": f"/app/teacher/classes/{class_id}/groups",
        "class_notes": f"/app/teacher/classes/{class_id}/notes",
        "assignments_and_grades": f"/app/teacher/assignments-and-grades/{class_id}",
        "group_assignments": f"/app/teacher/assignments-and-grades/{class_id}?view=group",
        "deadline_reminders": "spa:deadline_reminders",
        "analytics": "spa:analytics",
        "feedback_360": "spa:360-feedback",
        "reflection_journals": "spa:reflection-journals",
        "conflicts": "spa:conflicts",
        "assistant_approvals": f"/app/teacher/classes/{class_id}/assistant-approvals",
        "announcements_legacy": "#announcements",
    }
    if features.get("syllabus"):
        links["syllabus"] = "modal:syllabus"
    if features.get("grade1_standards"):
        links["grade1_standards"] = f"/app/teacher/classes/{class_id}/standards/grade1"
    if features.get("grade3_standards"):
        links["grade3_standards"] = f"/app/teacher/classes/{class_id}/standards/grade3"
    return links


def _serialize_announcement(ann: Announcement) -> dict[str, Any]:
    ts = ann.timestamp
    return {
        "id": ann.id,
        "title": ann.title or "",
        "message": ann.message or "",
        "message_preview": ((ann.message or "")[:100] + ("..." if len(ann.message or "") > 100 else "")),
        "timestamp": ts.isoformat() if ts else None,
        "timestamp_display": ts.strftime("%b %d, %Y %I:%M %p") if ts else "",
    }


def _assistant_log_summary(log: StudentAssistantActionLog) -> str:
    if not log.details:
        return "—"
    try:
        details = json.loads(log.details) if isinstance(log.details, str) else log.details
    except (json.JSONDecodeError, TypeError):
        return "—"
    if not isinstance(details, dict):
        return "—"
    if log.assignment_id and details.get("assignment_title"):
        text = str(details.get("assignment_title", ""))
        changes = details.get("changes")
        if isinstance(changes, list) and changes:
            text += f" ({len(changes)} change(s))"
        return text or "—"
    if details.get("date"):
        text = f"Date: {details.get('date')}"
        changes = details.get("changes")
        if isinstance(changes, list) and changes:
            text += f" ({len(changes)} change(s))"
        return text
    return "—"


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


def _serialize_teacher_class_roster_student(student: Student) -> dict[str, Any]:
    import re

    photo = getattr(student, "photo_filename", None)
    safe_photo = photo if photo and re.match(r"^[a-zA-Z0-9._-]+$", str(photo)) else None
    user = User.query.filter_by(student_id=student.id).first()
    school_email = (user.google_workspace_email or "").strip() if user else None
    return {
        **serialize_student_brief(student),
        "grade_label": _grade_label(student.grade_level),
        "email": student.email or None,
        "school_email": school_email or None,
        "date_of_birth_display": student.dob or None,
        "parent1_name": (
            f"{student.parent1_first_name or ''} {student.parent1_last_name or ''}".strip() or None
        ),
        "parent1_email": student.parent1_email or None,
        "parent1_phone": student.parent1_phone or None,
        "photo_url": f"/static/uploads/{safe_photo}" if safe_photo else "/static/img/default_avatar.png",
        "links": {
            "grades": f"/app/teacher/students/{student.id}/grades",
            "attendance": f"/app/teacher/students/{student.id}/attendance",
        },
    }


def _serialize_assistant_log(log: StudentAssistantActionLog) -> dict[str, Any]:
    action = log.action_type or "other"
    badge = {
        "attendance": ("Attendance", "primary"),
        "past_attendance": ("Past attendance", "warn"),
        "grade_entry": ("Grade entry", "info"),
        "grade_change": ("Grade change", "danger"),
    }.get(action, (action.replace("_", " ").title(), "muted"))
    created = log.created_at
    return {
        "id": log.id,
        "action_type": action,
        "action_label": badge[0],
        "action_tone": badge[1],
        "summary": _assistant_log_summary(log),
        "alert_sent": bool(log.alert_sent),
        "created_at": created.isoformat() if created else None,
        "created_at_display": created.strftime("%Y-%m-%d %H:%M") if created else "",
    }


def build_teacher_class_view_payload(class_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    try:
        class_obj = Class.query.get(class_id)
        if not class_obj:
            return None, "Class not found", 404
        if not is_authorized_for_class(class_obj):
            return None, "You are not authorized to view this class.", 403

        from services.class_google_group import try_provision_class_google_group

        if class_needs_google_integration(class_obj):
            try_provision_class_google_group(class_id)
            db.session.refresh(class_obj)

        enrolled = (
            db.session.query(Student)
            .join(Enrollment)
            .filter(
                Enrollment.class_id == class_id,
                Enrollment.is_active.is_(True),
                Student.is_deleted.is_(False),
            )
            .order_by(Student.last_name, Student.first_name)
            .all()
        )
        assignment_count = _assignment_count(class_id)
        announcements = (
            Announcement.query.filter_by(class_id=class_id)
            .order_by(Announcement.timestamp.desc())
            .limit(5)
            .all()
        )
        student_assistants = [
            sa.student
            for sa in StudentAssistant.query.filter_by(class_id=class_id).all()
            if sa.student
        ]
        assistant_logs = (
            StudentAssistantActionLog.query.filter_by(class_id=class_id)
            .order_by(StudentAssistantActionLog.created_at.desc())
            .limit(50)
            .all()
        )

        from management_routes.student_assistant_utils import count_pending_assistant_proposals_for_class

        pending_assistant_count = count_pending_assistant_proposals_for_class(class_id)
        has_student_assistants = len(student_assistants) > 0
        features = _standards_flags(class_obj)
        show_google = class_needs_google_integration(class_obj)
        school_year = class_obj.school_year
        item = serialize_class_list_item(
            class_obj,
            enrollment_count=len(enrolled),
            assignment_count=assignment_count,
        )

        return (
            {
                "class": {
                    **item,
                    "school_year_name": school_year.name if school_year else None,
                    "room_display": class_obj.room_number or "N/A",
                    "schedule_display": class_obj.schedule or "TBD",
                    "google_group_email": (class_obj.google_group_email or None)
                    if show_google
                    else None,
                    "show_google_integration": show_google,
                },
                "enrolled_students": [_serialize_teacher_class_roster_student(s) for s in enrolled],
                "announcements": [_serialize_announcement(a) for a in announcements],
                "student_assistants": [
                    {
                        "id": s.id,
                        "display_name": f"{s.first_name or ''} {s.last_name or ''}".strip(),
                    }
                    for s in student_assistants
                ],
                "assistant_action_logs": [_serialize_assistant_log(log) for log in assistant_logs],
                "stats": {
                    "students": len(enrolled),
                    "assignments": assignment_count,
                    "announcements": len(announcements),
                },
                "pending_assistant_count": pending_assistant_count,
                "has_student_assistants": has_student_assistants,
                "features": features,
                "links": _teacher_class_view_links(class_id, features),
            },
            None,
            200,
        )
    except Exception as exc:
        return None, str(exc), 500
