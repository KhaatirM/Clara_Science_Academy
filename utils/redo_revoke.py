"""Shared helpers for revoking granted redo / reopen access."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models import AssignmentRedo, AssignmentReopening, RedoRequest, TeacherStaff, db


def mark_approved_redo_request_revoked(
    *,
    assignment_id: int,
    student_id: int,
    teacher: TeacherStaff | None = None,
    notes: str | None = None,
) -> RedoRequest | None:
    """Flip the latest Approved RedoRequest to Revoked so the student can re-request."""
    req = (
        RedoRequest.query.filter_by(
            assignment_id=assignment_id,
            student_id=student_id,
            status="Approved",
        )
        .order_by(RedoRequest.reviewed_at.desc(), RedoRequest.requested_at.desc())
        .first()
    )
    if not req:
        return None
    req.status = "Revoked"
    req.reviewed_at = datetime.utcnow()
    if teacher is not None:
        req.reviewed_by = teacher.id
    if notes:
        req.review_notes = notes
    return req


def deactivate_student_reopenings(*, assignment_id: int, student_id: int) -> int:
    """Deactivate all active reopenings for this student/assignment pair."""
    rows = AssignmentReopening.query.filter_by(
        assignment_id=assignment_id,
        student_id=student_id,
        is_active=True,
    ).all()
    for row in rows:
        row.is_active = False
    return len(rows)


def revoke_assignment_redo_record(
    *,
    redo: AssignmentRedo,
    teacher: TeacherStaff | None = None,
) -> dict[str, Any]:
    """Revoke an unused AssignmentRedo and mark the matching Approved request Revoked."""
    if redo.is_used:
        raise ValueError("Cannot revoke a redo that has already been used.")

    mark_approved_redo_request_revoked(
        assignment_id=redo.assignment_id,
        student_id=redo.student_id,
        teacher=teacher,
        notes="Redo permission revoked",
    )
    deactivate_student_reopenings(
        assignment_id=redo.assignment_id,
        student_id=redo.student_id,
    )
    title = redo.assignment.title if redo.assignment else "assignment"
    student = redo.student
    db.session.delete(redo)
    return {"title": title, "student": student}


def revoke_assignment_reopening_record(
    *,
    reopening: AssignmentReopening,
    teacher: TeacherStaff | None = None,
) -> dict[str, Any]:
    """Deactivate a reopening grant and mark the matching Approved request Revoked."""
    if not reopening.is_active:
        raise ValueError("This reopening is already inactive.")

    mark_approved_redo_request_revoked(
        assignment_id=reopening.assignment_id,
        student_id=reopening.student_id,
        teacher=teacher,
        notes="Redo / reopen permission revoked",
    )
    reopening.is_active = False
    title = reopening.assignment.title if reopening.assignment else "assignment"
    student = reopening.student
    return {"title": title, "student": student}
