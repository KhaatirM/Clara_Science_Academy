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


def quiz_additional_attempts_needed(
    assignment: Assignment,
    student_id: int,
    requested_attempts: int,
) -> int:
    """
    Compute AssignmentReopening.additional_attempts so the student has
    ``requested_attempts`` tries remaining right now.
    """
    requested = max(1, int(requested_attempts or 1))
    submissions_count = Submission.query.filter_by(
        student_id=student_id,
        assignment_id=assignment.id,
    ).count()
    base = int(assignment.max_attempts or 0)
    if base <= 0:
        # Store total allowed submissions so remaining == requested after prior attempts.
        return submissions_count + requested
    target_effective_max = submissions_count + requested
    return max(requested, target_effective_max - base)


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
    allow_review_previous_attempts: bool | None = None,
) -> AssignmentReopening:
    reopened_by_id = teacher.id if teacher else None
    if reopened_by_id is None and assignment.class_info and assignment.class_info.teacher_id:
        reopened_by_id = assignment.class_info.teacher_id

    # Include inactive rows so a premature close can be revived on re-grant.
    existing = (
        AssignmentReopening.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
        )
        .order_by(AssignmentReopening.reopened_at.desc())
        .first()
    )
    if existing:
        existing.is_active = True
        existing.expires_at = redo_deadline
        existing.reason = reason or existing.reason
        # Refresh grant time so "used after reopen" checks use this grant.
        existing.reopened_at = datetime.utcnow()
        if reopened_by_id:
            existing.reopened_by = reopened_by_id
        if additional_attempts > 0:
            # SET (not max-only) so a new grant always restores the requested remaining tries.
            existing.additional_attempts = int(additional_attempts)
        if allow_review_previous_attempts is not None:
            existing.allow_review_previous_attempts = bool(allow_review_previous_attempts)
        return existing

    reopening = AssignmentReopening(
        assignment_id=assignment.id,
        student_id=student_id,
        reopened_by=reopened_by_id,
        is_active=True,
        additional_attempts=additional_attempts,
        expires_at=redo_deadline,
        reason=reason,
        allow_review_previous_attempts=(
            True if allow_review_previous_attempts is None else bool(allow_review_previous_attempts)
        ),
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
    additional_attempts: int | None = None,
    allow_review_previous_attempts: bool | None = None,
) -> dict[str, Any]:
    """
    Grant student access until redo_deadline.

    - Quiz: AssignmentReopening with enough additional attempts for the requested
      remaining tries, plus expires_at.
    - Discussion / never-submitted PDF: AssignmentReopening with expires_at.
    - Submitted PDF/paper: AssignmentRedo with redo_deadline (reopens closed work).
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

    if is_quiz:
        requested = max(1, int(additional_attempts or 1))
        needed = quiz_additional_attempts_needed(assignment, student_id, requested)
        allow_review = (
            True if allow_review_previous_attempts is None else bool(allow_review_previous_attempts)
        )
        _upsert_reopening(
            assignment=assignment,
            student_id=student_id,
            teacher=teacher,
            redo_deadline=redo_deadline,
            reason=reason_text,
            additional_attempts=needed,
            allow_review_previous_attempts=allow_review,
        )
        return {
            "mode": "reopening",
            "kind": "quiz",
            "already": False,
            "additional_attempts": needed,
            "attempts_granted": requested,
            "allow_review_previous_attempts": allow_review,
        }

    if is_discussion or not has_submitted:
        existing = AssignmentReopening.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
        ).first()
        already = existing is not None and bool(existing.is_active)
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
        if existing_redo.is_used:
            existing_redo.is_used = False
            existing_redo.redo_grade = None
            existing_redo.final_grade = None
            existing_redo.was_redo_late = False
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
