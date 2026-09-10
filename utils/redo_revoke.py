"""Shared helpers for revoking granted redo / reopen access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models import AssignmentRedo, AssignmentReopening, RedoRequest, TeacherStaff, db


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def student_has_usable_redo_access(
    assignment_id: int,
    student_id: int,
    *,
    now: datetime | None = None,
) -> bool:
    """True when the student still has a live redo / reopen window."""
    from teacher_routes.assignment_utils import get_active_assignment_reopening

    if now is None:
        now = datetime.now(timezone.utc)

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


def repair_orphaned_approved_redo_request(
    req: RedoRequest,
    *,
    now: datetime | None = None,
) -> RedoRequest:
    """
    If a request is Approved but the student has no live access left (common for
    legacy quiz grants / revokes that never flipped the request status), mark it
    Revoked so the student can request again.
    """
    if not req or req.status != "Approved":
        return req
    if student_has_usable_redo_access(req.assignment_id, req.student_id, now=now):
        return req
    req.status = "Revoked"
    req.reviewed_at = datetime.utcnow()
    note = "Auto-repaired: approved without active redo/reopen access"
    if req.review_notes:
        if note not in req.review_notes:
            req.review_notes = f"{req.review_notes} | {note}"
    else:
        req.review_notes = note
    return req


def repair_orphaned_approved_redo_requests_for_student(student_id: int) -> int:
    """Repair all orphaned Approved redo requests for one student. Returns count."""
    rows = RedoRequest.query.filter_by(student_id=student_id, status="Approved").all()
    repaired = 0
    now = datetime.now(timezone.utc)
    for req in rows:
        before = req.status
        repair_orphaned_approved_redo_request(req, now=now)
        if req.status == "Revoked" and before == "Approved":
            repaired += 1
    if repaired:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return 0
    return repaired


def deactivate_student_reopenings(*, assignment_id: int, student_id: int) -> int:
    """Deactivate all active reopenings for this student/assignment pair."""
    rows = AssignmentReopening.query.filter_by(
        assignment_id=assignment_id,
        student_id=student_id,
        is_active=True,
    ).all()
    now = datetime.utcnow()
    for row in rows:
        row.is_active = False
        # Prevent get_active_assignment_reopening from auto-reviving this grant.
        row.expires_at = now
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
    reopening.expires_at = datetime.utcnow()
    title = reopening.assignment.title if reopening.assignment else "assignment"
    student = reopening.student
    return {"title": title, "student": student}
