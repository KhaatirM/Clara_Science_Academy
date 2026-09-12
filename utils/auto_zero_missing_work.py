"""Auto-zero missing quiz/discussion work after the student's effective due date."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _student_effective_due(assignment, student_id: int) -> datetime | None:
    """Due datetime for auto-zero: extended due if active, else assignment.due_date."""
    from models import AssignmentExtension

    ext = AssignmentExtension.query.filter_by(
        assignment_id=assignment.id,
        student_id=student_id,
        is_active=True,
    ).first()
    raw = None
    if ext and getattr(ext, "extended_due_date", None):
        raw = ext.extended_due_date
    else:
        raw = getattr(assignment, "due_date", None)
    return _as_utc_aware(raw)


def _student_has_live_redo_or_reopen(assignment_id: int, student_id: int, now: datetime) -> bool:
    from models import AssignmentRedo
    from teacher_routes.assignment_utils import get_active_assignment_reopening
    from utils.redo_revoke import student_has_usable_redo_access

    if student_has_usable_redo_access(assignment_id, student_id, now=now):
        return True
    if get_active_assignment_reopening(assignment_id, student_id, now=now):
        return True
    redo = AssignmentRedo.query.filter_by(
        assignment_id=assignment_id,
        student_id=student_id,
        is_used=False,
    ).first()
    if redo and redo.redo_deadline:
        deadline = _as_utc_aware(redo.redo_deadline)
        if deadline is not None and now <= deadline:
            return True
    return False


def _discussion_participated(assignment_id: int, student_id: int) -> bool:
    from models import DiscussionPost, DiscussionThread

    if DiscussionThread.query.filter_by(assignment_id=assignment_id, student_id=student_id).first():
        return True
    thread_ids = [
        t.id for t in DiscussionThread.query.filter_by(assignment_id=assignment_id).all()
    ]
    if not thread_ids:
        return False
    return (
        DiscussionPost.query.filter(
            DiscussionPost.student_id == student_id,
            DiscussionPost.thread_id.in_(thread_ids),
        ).first()
        is not None
    )


def _quiz_has_submission(assignment_id: int, student_id: int) -> bool:
    from models import Submission

    return (
        Submission.query.filter_by(assignment_id=assignment_id, student_id=student_id)
        .filter(Submission.submission_type.in_(("online", "in_person")))
        .first()
        is not None
    )


def _write_auto_zero_grade(*, assignment, student_id: int, now: datetime) -> bool:
    """Insert a final auto-zero grade if none exists. Returns True if written."""
    from models import Grade, db

    existing = (
        Grade.query.filter_by(assignment_id=assignment.id, student_id=student_id)
        .order_by(Grade.graded_at.desc(), Grade.id.desc())
        .first()
    )
    if existing:
        return False

    total_points = float(getattr(assignment, "total_points", None) or 100.0)
    grade_data = {
        "score": 0.0,
        "points_earned": 0.0,
        "total_points": total_points,
        "max_score": total_points,
        "percentage": 0.0,
        "feedback": "",
        "comment": "Auto-zero: no submission by due date",
        "graded_at": now.isoformat(),
        "auto_zero": True,
        "grading_status": "final",
    }
    db.session.add(
        Grade(
            student_id=student_id,
            assignment_id=assignment.id,
            grade_data=json.dumps(grade_data),
            graded_at=now.replace(tzinfo=None) if now.tzinfo else now,
        )
    )
    return True


def apply_quiz_discussion_auto_zeros(*, class_ids: list[int] | None = None) -> dict[str, Any]:
    """
    For quiz and discussion assignments past each student's effective due date:
    if they never submitted/participated and have no live redo/reopen, assign 0.
    """
    from models import Assignment, Enrollment, db

    now = datetime.now(timezone.utc)
    written = 0
    scanned = 0

    q = Assignment.query.filter(
        Assignment.status != "Voided",
        Assignment.assignment_type.in_(("quiz", "discussion")),
    )
    if class_ids:
        q = q.filter(Assignment.class_id.in_(class_ids))

    for assignment in q.all():
        scanned += 1
        atype = (assignment.assignment_type or "").lower()
        enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
        for enr in enrollments:
            sid = enr.student_id
            if not sid:
                continue
            due = _student_effective_due(assignment, sid)
            if due is None or now <= due:
                continue
            if _student_has_live_redo_or_reopen(assignment.id, sid, now):
                continue

            if atype == "quiz":
                if _quiz_has_submission(assignment.id, sid):
                    continue
            elif atype == "discussion":
                if _discussion_participated(assignment.id, sid):
                    continue
            else:
                continue

            # Open-ended quiz with a pending grade should not be auto-zeroed.
            from models import Grade

            existing = Grade.query.filter_by(assignment_id=assignment.id, student_id=sid).first()
            if existing and existing.grade_data:
                try:
                    gd = (
                        json.loads(existing.grade_data)
                        if isinstance(existing.grade_data, str)
                        else existing.grade_data
                    )
                    if isinstance(gd, dict) and (gd.get("grading_status") or "").lower() == "pending":
                        continue
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass

            if _write_auto_zero_grade(assignment=assignment, student_id=sid, now=now):
                written += 1

    if written:
        try:
            db.session.commit()
            try:
                from utils.grade_mutation_hooks import notify_grades_changed

                notify_grades_changed()
            except Exception:
                pass
        except Exception:
            db.session.rollback()
            return {"success": False, "written": 0, "scanned": scanned}

    return {"success": True, "written": written, "scanned": scanned}
