"""Deadline reminder payloads and mutations for the React management SPA."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from flask_login import current_user

from extensions import db
from models import (
    Assignment,
    Class,
    DeadlineReminder,
    Enrollment,
    Grade,
    GroupAssignment,
    Notification,
    ReminderNotification,
    Student,
    Submission,
    User,
)

from management_routes.class_tools_spa_helpers import _enrolled_students, _load_deadline_reminders_for_class


def _creator_staff_id(class_obj: Class) -> int:
    staff_id = getattr(current_user, "teacher_staff_id", None)
    if staff_id:
        return int(staff_id)
    if class_obj.teacher_id:
        return int(class_obj.teacher_id)
    raise ValueError("No teacher staff record available for this action.")


def _assignment_options(class_id: int) -> list[dict[str, Any]]:
    rows = (
        Assignment.query.filter_by(class_id=class_id)
        .order_by(Assignment.title.asc())
        .all()
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "due_date": a.due_date.isoformat() if a.due_date else None,
        }
        for a in rows
    ]


def _group_assignment_options(class_id: int) -> list[dict[str, Any]]:
    rows = (
        GroupAssignment.query.filter_by(class_id=class_id)
        .order_by(GroupAssignment.title.asc())
        .all()
    )
    return [
        {
            "id": ga.id,
            "title": ga.title,
            "due_date": ga.due_date.isoformat() if ga.due_date else None,
        }
        for ga in rows
    ]


def _assignment_title_map(class_id: int) -> dict[int, str]:
    return {a.id: a.title for a in Assignment.query.filter_by(class_id=class_id).all()}


def _group_assignment_title_map(class_id: int) -> dict[int, str]:
    return {ga.id: ga.title for ga in GroupAssignment.query.filter_by(class_id=class_id).all()}


def _serialize_reminder(
    reminder: Any,
    assignment_titles: dict[int, str],
    group_assignment_titles: dict[int, str],
    now: datetime,
    upcoming_cutoff: datetime,
) -> dict[str, Any]:
    send_at = getattr(reminder, "reminder_date", None)
    is_upcoming = bool(send_at and now <= send_at <= upcoming_cutoff)
    reminder_type = getattr(reminder, "reminder_type", "general") or "general"
    assignment_id = getattr(reminder, "assignment_id", None)
    group_assignment_id = getattr(reminder, "group_assignment_id", None)
    assignment_title = None
    if assignment_id:
        assignment_title = assignment_titles.get(assignment_id)
        if not assignment_title and getattr(reminder, "assignment", None):
            assignment_title = reminder.assignment.title
    elif group_assignment_id:
        assignment_title = group_assignment_titles.get(group_assignment_id)
        if not assignment_title and getattr(reminder, "group_assignment", None):
            assignment_title = reminder.group_assignment.title

    last_sent = getattr(reminder, "last_sent", None)
    return {
        "id": reminder.id,
        "title": reminder.reminder_title or f"Reminder #{reminder.id}",
        "message": reminder.reminder_message or "",
        "reminder_type": reminder_type,
        "reminder_frequency": getattr(reminder, "reminder_frequency", "once") or "once",
        "send_at": send_at.isoformat() if send_at else None,
        "status": "active" if getattr(reminder, "is_active", True) else "inactive",
        "is_upcoming": is_upcoming,
        "assignment_id": assignment_id,
        "group_assignment_id": group_assignment_id,
        "assignment_title": assignment_title,
        "last_sent": last_sent.isoformat() if last_sent else None,
        "created_at": (
            reminder.created_at.isoformat()
            if getattr(reminder, "created_at", None)
            else None
        ),
    }


def query_deadline_reminders_hub(class_id: int) -> dict[str, Any]:
    from models import Class

    class_obj = Class.query.get_or_404(class_id)
    reminders = _load_deadline_reminders_for_class(class_id)
    now = datetime.now()
    upcoming_cutoff = now + timedelta(days=7)
    assignment_titles = _assignment_title_map(class_id)
    group_assignment_titles = _group_assignment_title_map(class_id)

    payload_reminders = []
    active_count = 0
    assignment_count = 0
    upcoming: list[dict[str, Any]] = []

    for r in reminders:
        item = _serialize_reminder(r, assignment_titles, group_assignment_titles, now, upcoming_cutoff)
        if item["status"] == "active":
            active_count += 1
        if item["reminder_type"] == "assignment":
            assignment_count += 1
        if item["is_upcoming"]:
            upcoming.append(item)
        payload_reminders.append(item)

    teacher = class_obj.teacher if getattr(class_obj, "teacher", None) else None
    teacher_name = (
        f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() if teacher else "Unknown"
    )

    return {
        "id": class_obj.id,
        "name": class_obj.name,
        "subject": getattr(class_obj, "subject", None),
        "teacher_name": teacher_name,
        "tool": "deadline-reminders",
        "title": "Deadline reminders",
        "stats": {
            "total": len(reminders),
            "active": active_count,
            "upcoming": len(upcoming),
            "assignment": assignment_count,
        },
        "reminders": payload_reminders,
        "upcoming": upcoming,
    }


def query_deadline_reminder_form(class_id: int, reminder_id: int | None = None) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    payload: dict[str, Any] = {
        "class": {"id": class_obj.id, "name": class_obj.name},
        "assignments": _assignment_options(class_id),
        "group_assignments": _group_assignment_options(class_id),
        "students": _enrolled_students(class_id),
        "defaults": {
            "reminder_type": "assignment",
            "reminder_frequency": "once",
            "reminder_date": (datetime.now() + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            ).strftime("%Y-%m-%dT%H:%M"),
        },
    }
    if reminder_id is None:
        return payload

    reminder = DeadlineReminder.query.filter_by(id=reminder_id, class_id=class_id).first_or_404()
    selected_ids: list[int] = []
    raw_selected = getattr(reminder, "selected_student_ids", None)
    if raw_selected:
        try:
            selected_ids = [int(x) for x in json.loads(raw_selected)]
        except (TypeError, ValueError, json.JSONDecodeError):
            selected_ids = []

    send_at = reminder.reminder_date
    payload["reminder"] = {
        "id": reminder.id,
        "reminder_type": reminder.reminder_type,
        "reminder_frequency": reminder.reminder_frequency,
        "reminder_title": reminder.reminder_title,
        "reminder_message": reminder.reminder_message,
        "reminder_date": send_at.strftime("%Y-%m-%dT%H:%M") if send_at else "",
        "assignment_id": reminder.assignment_id,
        "group_assignment_id": reminder.group_assignment_id,
        "selected_student_ids": selected_ids,
        "is_active": bool(reminder.is_active),
        "last_sent": reminder.last_sent.isoformat() if reminder.last_sent else None,
        "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
    }
    return payload


def _parse_reminder_body(body: dict[str, Any]) -> dict[str, Any]:
    reminder_type = (body.get("reminder_type") or "assignment").strip()
    reminder_frequency = (body.get("reminder_frequency") or "once").strip()
    reminder_title = (body.get("reminder_title") or "").strip()
    reminder_message = (body.get("reminder_message") or "").strip()
    reminder_date_str = (body.get("reminder_date") or "").strip()

    if not reminder_title or not reminder_message or not reminder_date_str:
        raise ValueError("Title, message, and reminder date are required.")

    try:
        reminder_date = datetime.strptime(reminder_date_str, "%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise ValueError("Invalid reminder date format.") from exc

    assignment_id = body.get("assignment_id")
    group_assignment_id = body.get("group_assignment_id")
    if assignment_id in ("", None):
        assignment_id = None
    else:
        assignment_id = int(assignment_id)
    if group_assignment_id in ("", None):
        group_assignment_id = None
    else:
        group_assignment_id = int(group_assignment_id)

    if reminder_type == "assignment" and not assignment_id:
        raise ValueError("Select a regular assignment for this reminder type.")
    if reminder_type == "group_assignment" and not group_assignment_id:
        raise ValueError("Select a group assignment for this reminder type.")
    if reminder_type == "assignment":
        group_assignment_id = None
    elif reminder_type == "group_assignment":
        assignment_id = None
    else:
        assignment_id = None
        group_assignment_id = None

    selected_raw = body.get("selected_student_ids")
    selected_student_ids = None
    if isinstance(selected_raw, list) and selected_raw:
        selected_student_ids = json.dumps([int(x) for x in selected_raw])

    return {
        "reminder_type": reminder_type,
        "reminder_frequency": reminder_frequency,
        "reminder_title": reminder_title,
        "reminder_message": reminder_message,
        "reminder_date": reminder_date,
        "assignment_id": assignment_id,
        "group_assignment_id": group_assignment_id,
        "selected_student_ids": selected_student_ids,
    }


def create_deadline_reminder(class_id: int, body: dict[str, Any]) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    fields = _parse_reminder_body(body)
    reminder = DeadlineReminder(
        class_id=class_id,
        created_by=_creator_staff_id(class_obj),
        is_active=True,
        next_send=fields["reminder_date"],
        **fields,
    )
    db.session.add(reminder)
    db.session.commit()
    return {"success": True, "message": "Reminder created.", "id": reminder.id}


def update_deadline_reminder(class_id: int, reminder_id: int, body: dict[str, Any]) -> dict[str, Any]:
    reminder = DeadlineReminder.query.filter_by(id=reminder_id, class_id=class_id).first_or_404()
    fields = _parse_reminder_body(body)
    for key, value in fields.items():
        setattr(reminder, key, value)
    if reminder.next_send is None or reminder.next_send < fields["reminder_date"]:
        reminder.next_send = fields["reminder_date"]
    db.session.commit()
    return {"success": True, "message": "Reminder updated.", "id": reminder.id}


def toggle_deadline_reminder(class_id: int, reminder_id: int) -> dict[str, Any]:
    reminder = DeadlineReminder.query.filter_by(id=reminder_id, class_id=class_id).first_or_404()
    reminder.is_active = not bool(reminder.is_active)
    db.session.commit()
    state = "activated" if reminder.is_active else "deactivated"
    return {"success": True, "message": f"Reminder {state}.", "is_active": reminder.is_active}


def delete_deadline_reminder(class_id: int, reminder_id: int) -> dict[str, Any]:
    reminder = DeadlineReminder.query.filter_by(id=reminder_id, class_id=class_id).first_or_404()
    ReminderNotification.query.filter_by(reminder_id=reminder.id).delete(synchronize_session=False)
    db.session.delete(reminder)
    db.session.commit()
    return {"success": True, "message": "Reminder deleted."}


def _enrolled_student_ids(class_id: int) -> list[int]:
    from utils.student_roster import active_class_roster_students_query

    return [int(s.id) for s in active_class_roster_students_query(class_id).all()]


def _target_student_ids(reminder: DeadlineReminder) -> list[int]:
    raw_selected = getattr(reminder, "selected_student_ids", None)
    if raw_selected:
        try:
            ids = [int(x) for x in json.loads(raw_selected)]
            if ids:
                return ids
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return _enrolled_student_ids(reminder.class_id)


def send_deadline_reminder_now(class_id: int, reminder_id: int) -> dict[str, Any]:
    reminder = DeadlineReminder.query.filter_by(id=reminder_id, class_id=class_id).first_or_404()
    student_ids = _target_student_ids(reminder)
    if not student_ids:
        return {"success": False, "message": "No students to notify."}

    sent = 0
    for student_id in student_ids:
        user = User.query.filter_by(student_id=student_id).first()
        if not user:
            continue
        db.session.add(
            Notification(
                user_id=user.id,
                type="deadline_reminder",
                title=reminder.reminder_title,
                message=reminder.reminder_message,
            )
        )
        db.session.add(
            ReminderNotification(
                reminder_id=reminder.id,
                student_id=student_id,
                notification_type="in_app",
                status="sent",
            )
        )
        sent += 1

    now = datetime.now()
    reminder.last_sent = now
    if reminder.reminder_frequency == "daily":
        reminder.next_send = now + timedelta(days=1)
    elif reminder.reminder_frequency == "weekly":
        reminder.next_send = now + timedelta(weeks=1)
    else:
        reminder.next_send = None

    db.session.commit()
    return {
        "success": True,
        "message": f"Reminder sent to {sent} student(s).",
        "sent_count": sent,
    }


def query_students_needing_reminder(assignment_id: int) -> dict[str, Any]:
    from utils.student_roster import active_class_roster_students_query

    assignment = Assignment.query.get_or_404(assignment_id)
    enrolled_student_ids = [s.id for s in active_class_roster_students_query(assignment.class_id).all()]

    submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    graded_students = Grade.query.filter_by(assignment_id=assignment.id).all()

    voided_student_ids: set[int] = set()
    for grade in graded_students:
        if grade.is_voided:
            voided_student_ids.add(grade.student_id)
        elif grade.grade_data:
            try:
                grade_data = json.loads(grade.grade_data)
                if grade_data.get("is_voided"):
                    voided_student_ids.add(grade.student_id)
            except (TypeError, json.JSONDecodeError):
                pass

    actually_submitted: set[int] = set()
    for sub in submissions:
        if sub.student_id not in voided_student_ids:
            if sub.submission_type and sub.submission_type != "not_submitted":
                actually_submitted.add(sub.student_id)

    students_payload = []
    for student_id in enrolled_student_ids:
        if student_id in voided_student_ids:
            continue
        student = Student.query.get(student_id)
        if not student or getattr(student, "is_deleted", False):
            continue
        if student_id in actually_submitted:
            status = "submitted_not_graded"
            graded = any(
                g.student_id == student_id and not g.is_voided for g in graded_students
            )
            if graded:
                continue
        else:
            status = "not_submitted"
        students_payload.append(
            {
                "id": student.id,
                "display_name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
                "student_id": getattr(student, "student_id", None),
                "status": status,
            }
        )

    return {"success": True, "students": students_payload}
