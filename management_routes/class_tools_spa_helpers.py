"""Class admin tool payloads for the React management SPA."""

from __future__ import annotations

from typing import Any

from extensions import db
from models import (
    Class,
    DeadlineReminder,
    Feedback360,
    GroupAssignment,
    GroupConflict,
    ReflectionJournal,
    StudentGroup,
    StudentGroupMember,
)
from utils.student_roster import active_class_roster_students_query, student_is_archived


def _load_deadline_reminders_for_class(class_id: int) -> list:
    """Load reminders; raw SQL fallback when selected_student_ids column is missing."""
    from sqlalchemy import text

    try:
        return (
            DeadlineReminder.query.filter_by(class_id=class_id)
            .order_by(DeadlineReminder.reminder_date.asc())
            .all()
        )
    except Exception as exc:
        error_str = str(exc).lower()
        if "selected_student_ids" not in error_str and "no such column" not in error_str:
            raise
        result = db.session.execute(
            text(
                """
                SELECT id, assignment_id, group_assignment_id, class_id, reminder_type,
                       reminder_title, reminder_message, reminder_date, reminder_frequency,
                       is_active, created_by, created_at, last_sent, next_send
                FROM deadline_reminder
                WHERE class_id = :class_id
                ORDER BY reminder_date ASC
                """
            ),
            {"class_id": class_id},
        )

        class _ReminderRow:
            pass

        reminders = []
        for row in result:
            item = _ReminderRow()
            for key, value in dict(row._mapping).items():
                setattr(item, key, value)
            reminders.append(item)
        return reminders


def _class_header(class_obj: Class) -> dict[str, Any]:
    teacher = class_obj.teacher if getattr(class_obj, "teacher", None) else None
    teacher_name = (
        f"{teacher.first_name or ''} {teacher.last_name or ''}".strip()
        if teacher
        else "Unknown"
    )
    return {
        "id": class_obj.id,
        "name": class_obj.name,
        "subject": getattr(class_obj, "subject", None),
        "teacher_name": teacher_name,
        "back_url": f"/app/management/classes/{class_obj.id}",
    }


def _enrolled_students(class_id: int) -> list[dict[str, Any]]:
    rows = active_class_roster_students_query(class_id).all()
    return [
        {
            "id": s.id,
            "display_name": f"{s.first_name or ''} {s.last_name or ''}".strip(),
            "grade_level": getattr(s, "grade_level", None),
            "view_url": f"/app/management/students?edit={s.id}",
        }
        for s in rows
    ]


def query_class_tool(class_id: int, tool: str) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    header = _class_header(class_obj)
    students = _enrolled_students(class_id)

    if tool == "analytics":
        groups = StudentGroup.query.filter_by(class_id=class_id).all()
        group_assignments = GroupAssignment.query.filter_by(class_id=class_id).all()

        def _active_member_count(group: StudentGroup) -> int:
            return sum(
                1
                for m in (group.members or [])
                if getattr(m, "student", None) and not student_is_archived(m.student)
            )

        return {
            **header,
            "tool": tool,
            "title": "Class analytics",
            "summary": {
                "groups": len(groups),
                "group_assignments": len(group_assignments),
                "students": len(students),
            },
            "groups": [
                {"id": g.id, "name": g.name, "member_count": _active_member_count(g)}
                for g in groups
            ],
            "group_assignments": [
                {"id": ga.id, "title": ga.title, "status": ga.status, "due_date": ga.due_date.isoformat() if ga.due_date else None}
                for ga in group_assignments
            ],
        }

    if tool == "groups":
        groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
        payload_groups = []
        for group in groups:
            members = StudentGroupMember.query.filter_by(group_id=group.id).all()
            member_rows = [
                {
                    "student_id": m.student_id,
                    "display_name": (
                        f"{m.student.first_name} {m.student.last_name}".strip()
                        if m.student
                        else "Unknown"
                    ),
                    "is_leader": bool(m.is_leader),
                }
                for m in members
                if m.student and not student_is_archived(m.student)
            ]
            payload_groups.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "member_count": len(member_rows),
                    "members": member_rows,
                }
            )
        return {
            **header,
            "tool": tool,
            "title": "Student groups",
            "groups": payload_groups,
            "students": students,
        }

    if tool == "360-feedback":
        sessions = Feedback360.query.filter_by(class_id=class_id).order_by(Feedback360.created_at.desc()).all()
        return {
            **header,
            "tool": tool,
            "title": "360° feedback",
            "stats": {
                "total": len(sessions),
                "active": sum(1 for s in sessions if s.is_active),
            },
            "sessions": [
                {
                    "id": s.id,
                    "title": s.title or f"Session #{s.id}",
                    "status": "active" if s.is_active else "inactive",
                    "feedback_type": getattr(s, "feedback_type", None),
                    "due_date": s.due_date.isoformat() if getattr(s, "due_date", None) else None,
                    "created_at": s.created_at.isoformat() if getattr(s, "created_at", None) else None,
                }
                for s in sessions
            ],
        }

    if tool == "reflection-journals":
        group_ids = [g.id for g in StudentGroup.query.filter_by(class_id=class_id).all()]
        journals = (
            ReflectionJournal.query.filter(ReflectionJournal.group_id.in_(group_ids))
            .order_by(ReflectionJournal.submitted_at.desc())
            .all()
            if group_ids
            else []
        )
        return {
            **header,
            "tool": tool,
            "title": "Reflection journals",
            "stats": {"total": len(journals)},
            "journals": [
                {
                    "id": j.id,
                    "title": (
                        f"{j.student.first_name} {j.student.last_name}".strip()
                        if getattr(j, "student", None)
                        else f"Journal #{j.id}"
                    ),
                    "assignment_title": (
                        j.group_assignment.title
                        if getattr(j, "group_assignment", None)
                        else None
                    ),
                    "submitted_at": j.submitted_at.isoformat() if getattr(j, "submitted_at", None) else None,
                    "status": "submitted",
                    "collaboration_rating": getattr(j, "collaboration_rating", None),
                    "learning_rating": getattr(j, "learning_rating", None),
                }
                for j in journals
            ],
        }

    if tool == "conflicts":
        group_ids = [g.id for g in StudentGroup.query.filter_by(class_id=class_id).all()]
        conflicts = (
            GroupConflict.query.filter(GroupConflict.group_id.in_(group_ids))
            .order_by(GroupConflict.reported_at.desc())
            .all()
            if group_ids
            else []
        )
        return {
            **header,
            "tool": tool,
            "title": "Conflict resolution",
            "stats": {
                "total": len(conflicts),
                "open": sum(1 for c in conflicts if c.status not in ("resolved",)),
            },
            "conflicts": [
                {
                    "id": c.id,
                    "title": c.conflict_type or f"Conflict #{c.id}",
                    "status": c.status,
                    "severity": getattr(c, "severity_level", None),
                    "description": (c.conflict_description or "")[:160],
                    "created_at": c.reported_at.isoformat() if getattr(c, "reported_at", None) else None,
                }
                for c in conflicts
            ],
        }

    if tool == "deadline-reminders":
        from management_routes.deadline_reminders_spa_helpers import query_deadline_reminders_hub

        return query_deadline_reminders_hub(class_id)

    raise ValueError(f"Unknown class tool: {tool}")


CLASS_TOOL_SLUGS = frozenset(
    {
        "analytics",
        "groups",
        "360-feedback",
        "reflection-journals",
        "conflicts",
        "deadline-reminders",
    }
)
