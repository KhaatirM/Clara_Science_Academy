"""Student collaborate hub (peer feedback, journals, conflicts) for the React SPA."""

from __future__ import annotations

import json
from typing import Any

from flask_login import current_user
from sqlalchemy.orm import joinedload

from management_routes.student_assistant_utils import group_assignment_student_visibility_filter
from models import (
    Enrollment,
    Feedback360,
    Feedback360Response,
    GroupAssignment,
    GroupConflict,
    ReflectionJournal,
    SchoolYear,
    Student,
    StudentGroupMember,
    db,
)


def _fmt_dt(value) -> str | None:
    if not value:
        return None
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        pass
    return str(value)


def _student_name(student: Student | None) -> str:
    if not student:
        return "Unknown"
    return f"{student.first_name or ''} {student.last_name or ''}".strip() or "Unknown"


def _parse_feedback_preview(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, dict):
            return None
        comments = data.get("comments") or data.get("comment")
        if comments:
            return str(comments)[:140]
        ratings = []
        for key, val in data.items():
            if key in ("comments", "comment"):
                continue
            if isinstance(val, (int, float)):
                ratings.append(f"{key}: {val}")
        return ", ".join(ratings[:3]) if ratings else None
    except Exception:
        text = str(raw).strip()
        return text[:140] if text else None


def build_student_collaborate_payload() -> tuple[dict[str, Any] | None, str | None]:
    sid = getattr(current_user, "student_id", None)
    if not sid:
        return None, "Student profile required"
    student = Student.query.get(sid)
    if not student:
        return None, "Student not found"

    school_year = SchoolYear.query.filter_by(is_active=True).first()

    feedback_rows = (
        Feedback360Response.query.filter_by(respondent_id=student.id)
        .options(joinedload(Feedback360Response.feedback360).joinedload(Feedback360.target_student))
        .order_by(Feedback360Response.submitted_at.desc())
        .all()
    )
    feedback_history = []
    for row in feedback_rows[:25]:
        session = row.feedback360
        feedback_history.append(
            {
                "id": row.id,
                "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
                "submitted_display": _fmt_dt(row.submitted_at),
                "session_title": session.title if session else "Feedback session",
                "target_name": _student_name(session.target_student) if session else "—",
                "class_name": session.class_info.name if session and session.class_info else None,
                "is_anonymous": bool(row.is_anonymous),
                "preview": _parse_feedback_preview(row.feedback_data),
            }
        )

    journal_rows = (
        ReflectionJournal.query.filter_by(student_id=student.id)
        .options(
            joinedload(ReflectionJournal.group),
            joinedload(ReflectionJournal.group_assignment),
        )
        .order_by(ReflectionJournal.submitted_at.desc())
        .all()
    )
    journal_history = []
    for row in journal_rows[:25]:
        journal_history.append(
            {
                "id": row.id,
                "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
                "submitted_display": _fmt_dt(row.submitted_at),
                "group_name": row.group.name if row.group else "—",
                "assignment_title": row.group_assignment.title if row.group_assignment else "—",
                "collaboration_rating": row.collaboration_rating,
                "learning_rating": row.learning_rating,
                "reflection_preview": (row.reflection_text or "")[:160],
            }
        )

    conflict_rows = (
        GroupConflict.query.filter_by(reported_by=student.id)
        .options(
            joinedload(GroupConflict.group),
            joinedload(GroupConflict.group_assignment),
        )
        .order_by(GroupConflict.reported_at.desc())
        .all()
    )
    conflict_history = []
    for row in conflict_rows[:25]:
        conflict_history.append(
            {
                "id": row.id,
                "reported_at": row.reported_at.isoformat() if row.reported_at else None,
                "reported_display": _fmt_dt(row.reported_at),
                "group_name": row.group.name if row.group else "—",
                "assignment_title": row.group_assignment.title if row.group_assignment else "—",
                "conflict_type": row.conflict_type,
                "conflict_type_label": (row.conflict_type or "other").replace("_", " ").title(),
                "severity_level": row.severity_level,
                "status": row.status,
                "status_label": (row.status or "reported").replace("_", " ").title(),
                "description_preview": (row.conflict_description or "")[:160],
            }
        )

    already_responded = {
        r.feedback360_id for r in Feedback360Response.query.filter_by(respondent_id=student.id).all()
    }

    available_sessions: list[dict[str, Any]] = []
    if school_year:
        enrollments = Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
        class_ids = [e.class_id for e in enrollments]
        if class_ids:
            sessions = (
                Feedback360.query.filter(
                    Feedback360.class_id.in_(class_ids),
                    Feedback360.is_active == True,  # noqa: E712
                )
                .options(
                    joinedload(Feedback360.target_student),
                    joinedload(Feedback360.class_info),
                    joinedload(Feedback360.criteria),
                )
                .order_by(Feedback360.created_at.desc())
                .all()
            )
            for session in sessions:
                if session.id in already_responded:
                    continue
                if session.target_student_id == student.id and session.feedback_type == "peer_only":
                    continue
                criteria = sorted(session.criteria or [], key=lambda c: c.order_index or 0)
                criteria_out = [
                    {
                        "id": c.id,
                        "name": c.criteria_name,
                        "description": c.criteria_description,
                        "type": c.criteria_type or "rating",
                        "scale_min": c.scale_min or 1,
                        "scale_max": c.scale_max or 5,
                        "required": bool(c.is_required),
                    }
                    for c in criteria
                ]
                if not criteria_out:
                    criteria_out = [
                        {
                            "id": None,
                            "name": "communication",
                            "description": "Communication with the group",
                            "type": "rating",
                            "scale_min": 1,
                            "scale_max": 5,
                            "required": True,
                        },
                        {
                            "id": None,
                            "name": "teamwork",
                            "description": "Teamwork and collaboration",
                            "type": "rating",
                            "scale_min": 1,
                            "scale_max": 5,
                            "required": True,
                        },
                        {
                            "id": None,
                            "name": "leadership",
                            "description": "Leadership and initiative",
                            "type": "rating",
                            "scale_min": 1,
                            "scale_max": 5,
                            "required": True,
                        },
                        {
                            "id": None,
                            "name": "comments",
                            "description": "Additional comments",
                            "type": "text",
                            "scale_min": 1,
                            "scale_max": 5,
                            "required": False,
                        },
                    ]
                available_sessions.append(
                    {
                        "id": session.id,
                        "title": session.title,
                        "description": session.description,
                        "class_name": session.class_info.name if session.class_info else "Class",
                        "target_name": _student_name(session.target_student),
                        "due_display": _fmt_dt(session.due_date),
                        "criteria": criteria_out,
                    }
                )

    group_assignments: list[dict[str, Any]] = []
    seen_keys: set[tuple[int, int]] = set()
    memberships = (
        StudentGroupMember.query.filter_by(student_id=student.id)
        .options(joinedload(StudentGroupMember.group))
        .all()
    )
    for membership in memberships:
        group = membership.group
        if not group or not group.class_id or not getattr(group, "is_active", True):
            continue
        assignments = GroupAssignment.query.filter(
            GroupAssignment.class_id == group.class_id,
            group_assignment_student_visibility_filter(),
        ).all()
        for assignment in assignments:
            key = (assignment.id, group.id)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            group_assignments.append(
                {
                    "id": assignment.id,
                    "title": assignment.title,
                    "class_name": group.class_info.name if group.class_info else "Class",
                    "group_id": group.id,
                    "group_name": group.name,
                    "label": f"{assignment.title} · {group.class_info.name if group.class_info else 'Class'} ({group.name})",
                }
            )
    group_assignments.sort(key=lambda x: (x["class_name"] or "", x["title"] or ""))

    return {
        "school_year_name": school_year.name if school_year else None,
        "stats": {
            "feedback": len(feedback_rows),
            "journals": len(journal_rows),
            "conflicts": len(conflict_rows),
            "open_feedback": len(available_sessions),
        },
        "available_feedback_sessions": available_sessions,
        "group_assignments": group_assignments,
        "feedback_history": feedback_history,
        "journal_history": journal_history,
        "conflict_history": conflict_history,
        "conflict_types": [
            {"value": "communication", "label": "Communication issues"},
            {"value": "workload", "label": "Unequal workload"},
            {"value": "personality", "label": "Personality conflicts"},
            {"value": "participation", "label": "Lack of participation"},
            {"value": "other", "label": "Other"},
        ],
        "severity_levels": [
            {"value": "low", "label": "Low — minor issue"},
            {"value": "medium", "label": "Medium — affecting work"},
            {"value": "high", "label": "High — significant impact"},
            {"value": "critical", "label": "Critical — urgent help needed"},
        ],
    }, None


def submit_student_feedback360(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    sid = getattr(current_user, "student_id", None)
    if not sid:
        return None, "Student profile required", 403

    feedback360_id = payload.get("feedback360_id")
    answers = payload.get("answers") or {}
    is_anonymous = bool(payload.get("is_anonymous"))
    if not feedback360_id:
        return None, "Select a feedback session", 400

    session = Feedback360.query.get(int(feedback360_id))
    if not session or not session.is_active:
        return None, "Feedback session not available", 404

    existing = Feedback360Response.query.filter_by(
        feedback360_id=session.id, respondent_id=sid
    ).first()
    if existing:
        return None, "You already submitted feedback for this session", 400

    # Normalize answers into JSON
    if isinstance(answers, str):
        feedback_data = answers
    else:
        cleaned: dict[str, Any] = {}
        for key, val in (answers or {}).items():
            if val is None or val == "":
                continue
            cleaned[str(key)] = val
        if not cleaned:
            return None, "Provide at least one rating or comment", 400
        feedback_data = json.dumps(cleaned)

    row = Feedback360Response(
        feedback360_id=session.id,
        respondent_id=sid,
        respondent_type="self" if session.target_student_id == sid else "peer",
        feedback_data=feedback_data,
        is_anonymous=is_anonymous,
    )
    db.session.add(row)
    db.session.commit()
    return {"success": True, "message": "360° feedback submitted"}, None, 200


def submit_student_journal(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    sid = getattr(current_user, "student_id", None)
    if not sid:
        return None, "Student profile required", 403

    try:
        group_assignment_id = int(payload.get("group_assignment_id"))
        group_id = int(payload.get("group_id"))
        collaboration_rating = int(payload.get("collaboration_rating"))
        learning_rating = int(payload.get("learning_rating"))
    except (TypeError, ValueError):
        return None, "Invalid journal form values", 400

    reflection_text = (payload.get("reflection_text") or "").strip()
    if not reflection_text:
        return None, "Reflection text is required", 400
    if collaboration_rating < 1 or collaboration_rating > 5 or learning_rating < 1 or learning_rating > 5:
        return None, "Ratings must be between 1 and 5", 400

    membership = StudentGroupMember.query.filter_by(student_id=sid, group_id=group_id).first()
    if not membership:
        return None, "You are not a member of that group", 403

    row = ReflectionJournal(
        student_id=sid,
        group_id=group_id,
        group_assignment_id=group_assignment_id,
        reflection_text=reflection_text,
        collaboration_rating=collaboration_rating,
        learning_rating=learning_rating,
        challenges_faced=(payload.get("challenges_faced") or "").strip() or None,
        lessons_learned=(payload.get("lessons_learned") or "").strip() or None,
    )
    db.session.add(row)
    db.session.commit()
    return {"success": True, "message": "Reflection journal submitted"}, None, 200


def submit_student_conflict(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    sid = getattr(current_user, "student_id", None)
    if not sid:
        return None, "Student profile required", 403

    try:
        group_assignment_id = int(payload.get("group_assignment_id"))
        group_id = int(payload.get("group_id"))
    except (TypeError, ValueError):
        return None, "Invalid conflict form values", 400

    conflict_type = (payload.get("conflict_type") or "").strip()
    severity_level = (payload.get("severity_level") or "").strip()
    description = (payload.get("conflict_description") or "").strip()
    if not conflict_type or not severity_level or not description:
        return None, "Type, severity, and description are required", 400

    membership = StudentGroupMember.query.filter_by(student_id=sid, group_id=group_id).first()
    if not membership:
        return None, "You are not a member of that group", 403

    row = GroupConflict(
        group_id=group_id,
        group_assignment_id=group_assignment_id,
        reported_by=sid,
        conflict_type=conflict_type,
        conflict_description=description,
        severity_level=severity_level,
        status="reported",
    )
    db.session.add(row)
    db.session.commit()
    return {
        "success": True,
        "message": "Conflict report submitted. Your teacher will review it.",
    }, None, 200
