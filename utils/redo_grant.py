"""Shared logic for granting redo / reopen access from a student redo request."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from models import (
    Assignment,
    AssignmentRedo,
    AssignmentReopening,
    Grade,
    Submission,
    TeacherStaff,
    db,
)


def normalize_assignment_type(assignment_type: str | None) -> str:
    return (assignment_type or "").lower().replace("/", "_").replace(" ", "_")


def is_pdf_paper_type(assignment_type: str | None) -> bool:
    atype = normalize_assignment_type(assignment_type)
    return atype in ("", "pdf", "paper", "pdf_paper")


def parse_redo_deadline_end_of_day(date_str: str) -> datetime:
    """Parse YYYY-MM-DD as inclusive end-of-day (23:59:59)."""
    deadline = datetime.strptime((date_str or "").strip(), "%Y-%m-%d")
    return deadline.replace(hour=23, minute=59, second=59)


def _original_grade_points(student_id: int, assignment_id: int) -> float | None:
    grade = (
        Grade.query.filter_by(student_id=student_id, assignment_id=assignment_id)
        .order_by(Grade.graded_at.desc())
        .first()
    )
    if not grade or not grade.grade_data:
        return None
    try:
        gd = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
        if isinstance(gd, dict):
            value = gd.get("score")
            if value is None:
                value = gd.get("points_earned")
            return float(value) if value is not None else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return None


def _upsert_reopening(
    *,
    assignment: Assignment,
    student_id: int,
    teacher: TeacherStaff | None,
    redo_deadline: datetime,
    reason: str | None,
    additional_attempts: int,
) -> AssignmentReopening:
    reopened_by_id = teacher.id if teacher else None
    if reopened_by_id is None and assignment.class_info and assignment.class_info.teacher_id:
        reopened_by_id = assignment.class_info.teacher_id

    existing = (
        AssignmentReopening.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_active=True,
        ).first()
    )
    if existing:
        existing.expires_at = redo_deadline
        existing.reason = reason or existing.reason
        existing.reopened_at = datetime.utcnow()
        if reopened_by_id:
            existing.reopened_by = reopened_by_id
        if additional_attempts > 0:
            # Bring a 0-attempt (broken) reopen up to the grant; don't stack on re-approve.
            existing.additional_attempts = max(int(existing.additional_attempts or 0), additional_attempts)
        return existing

    reopening = AssignmentReopening(
        assignment_id=assignment.id,
        student_id=student_id,
        reopened_by=reopened_by_id,
        is_active=True,
        additional_attempts=additional_attempts,
        expires_at=redo_deadline,
        reason=reason,
    )
    db.session.add(reopening)
    return reopening


def grant_redo_access_for_request(
    *,
    assignment: Assignment,
    student_id: int,
    teacher: TeacherStaff | None,
    redo_deadline: datetime,
    reason: str | None = None,
) -> dict[str, Any]:
    """
    Grant student access until redo_deadline.

    - Quiz: always AssignmentReopening with +1 attempt and expires_at.
    - Discussion / never-submitted PDF: AssignmentReopening with expires_at.
    - Submitted PDF/paper: AssignmentRedo with redo_deadline.
    """
    submission = Submission.query.filter_by(
        student_id=student_id,
        assignment_id=assignment.id,
    ).first()
    has_submitted = submission is not None and submission.submission_type != "not_submitted"
    atype = normalize_assignment_type(getattr(assignment, "assignment_type", None))
    is_quiz = atype == "quiz"
    is_discussion = atype == "discussion"
    reason_text = reason or "Granted from redo request"

    # Quizzes need attempt math via AssignmentReopening, not AssignmentRedo.
    if is_quiz:
        _upsert_reopening(
            assignment=assignment,
            student_id=student_id,
            teacher=teacher,
            redo_deadline=redo_deadline,
            reason=reason_text,
            additional_attempts=1,
        )
        return {"mode": "reopening", "kind": "quiz", "already": False}

    if is_discussion or not has_submitted:
        existing = AssignmentReopening.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_active=True,
        ).first()
        already = existing is not None
        _upsert_reopening(
            assignment=assignment,
            student_id=student_id,
            teacher=teacher,
            redo_deadline=redo_deadline,
            reason=reason_text,
            additional_attempts=0,
        )
        return {
            "mode": "reopening",
            "kind": "discussion" if is_discussion else "access",
            "already": already,
        }

    # Submitted PDF / paper (or unknown types treated as file work)
    existing_redo = AssignmentRedo.query.filter_by(
        assignment_id=assignment.id,
        student_id=student_id,
    ).first()
    if existing_redo:
        existing_redo.redo_deadline = redo_deadline
        existing_redo.reason = reason_text
        existing_redo.granted_at = datetime.utcnow()
        if teacher:
            existing_redo.granted_by = teacher.id
        if existing_redo.is_used and not existing_redo.final_grade:
            # Keep used flag; teacher can still grade. Access window refreshed only if unused.
            pass
        # Re-open unused redos that were past deadline by refreshing deadline above.
        return {"mode": "redo", "kind": "pdf", "already": True}

    redo_rec = AssignmentRedo(
        assignment_id=assignment.id,
        student_id=student_id,
        granted_by=teacher.id if teacher else None,
        redo_deadline=redo_deadline,
        reason=reason_text,
        original_grade=_original_grade_points(student_id, assignment.id),
    )
    db.session.add(redo_rec)
    return {"mode": "redo", "kind": "pdf", "already": False}
