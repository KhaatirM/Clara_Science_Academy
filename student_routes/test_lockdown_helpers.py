"""Lockdown ('test' mode) quiz sessions: start, monitoring uploads, violations."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from models import (
    Assignment,
    Submission,
    TestMonitorEvent,
    TestMonitorSnapshot,
    TestSession,
    db,
)

MAX_SNAPSHOT_BYTES = 150 * 1024
MAX_SNAPSHOTS_PER_SESSION = 1500
MAX_EVENTS_BATCH_CHARS = 200_000
MAX_ANSWERS_CHARS = 500_000
SNAPSHOT_RETENTION_DAYS = 60

LOCK_REASON_LABELS = {
    "tab_hidden": "Left the test tab",
    "window_blur": "Clicked outside the test window",
    "page_closed": "Closed or reloaded the test page",
    "reload": "Reopened the test after leaving",
    "screen_share_ended": "Stopped sharing their screen",
    "camera_ended": "Turned off their camera",
    "fullscreen_exit": "Exited full screen",
}


def lock_reason_label(reason: str | None) -> str:
    if not reason:
        return "Locked"
    return LOCK_REASON_LABELS.get(reason, reason.replace("_", " ").capitalize())


def is_test_mode(assignment: Assignment | None) -> bool:
    return bool(
        assignment
        and assignment.assignment_type == "quiz"
        and (getattr(assignment, "quiz_mode", None) or "quiz") == "test"
        and not assignment.google_form_linked
    )


def active_test_session(assignment_id: int, student_id: int) -> TestSession | None:
    return (
        TestSession.query.filter_by(assignment_id=assignment_id, student_id=student_id, status="active")
        .order_by(TestSession.id.desc())
        .first()
    )


def latest_test_session(assignment_id: int, student_id: int) -> TestSession | None:
    return (
        TestSession.query.filter_by(assignment_id=assignment_id, student_id=student_id)
        .order_by(TestSession.id.desc())
        .first()
    )


def session_brief(session: TestSession | None) -> dict[str, Any] | None:
    if not session:
        return None
    return {
        "id": session.id,
        "status": session.status,
        "lock_reason": session.lock_reason,
        "lock_reason_label": lock_reason_label(session.lock_reason) if session.lock_reason else None,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "locked_at": session.locked_at.isoformat() if session.locked_at else None,
        "submission_id": session.submission_id,
    }


def _session_answers(session: TestSession) -> dict[str, Any]:
    if not session.last_answers_json:
        return {}
    try:
        data = json.loads(session.last_answers_json)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def lock_test_session(
    session: TestSession, reason: str, answers: dict[str, Any] | None = None
) -> tuple[dict[str, Any] | None, str | None, int]:
    """Auto-submit the attempt with the best answers we have, then mark the session locked."""
    from .quiz_spa_helpers import submit_student_quiz

    if session.status != "active":
        return {"success": True, "already": True, "status": session.status}, None, 200
    use_answers = answers if isinstance(answers, dict) and answers else _session_answers(session)
    payload, error, status = submit_student_quiz(
        session.assignment_id, answers=use_answers, lockdown_reason=reason or "tab_hidden"
    )
    if error:
        # Could not grade (e.g. quiz closed); still lock so the student can't continue.
        session.status = "locked"
        session.lock_reason = reason or "tab_hidden"
        session.locked_at = datetime.utcnow()
        session.ended_at = session.locked_at
        db.session.commit()
        return {"success": True, "locked": True, "graded": False, "message": error}, None, 200
    return payload, None, status


def start_test_session(assignment: Assignment, student_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    from teacher_routes.assignment_utils import (
        get_active_assignment_reopening,
        is_assignment_open_for_student,
    )

    if not is_test_mode(assignment):
        return None, "This assignment is not a lockdown test.", 400

    existing = active_test_session(assignment.id, student_id)
    if existing:
        lock_test_session(existing, "reload")
        return None, "This test was locked because it was reopened after leaving. Ask your teacher to unlock it.", 409

    latest = latest_test_session(assignment.id, student_id)
    if latest and latest.status == "locked":
        return None, "This test is locked. Ask your teacher to unlock it.", 403

    reopening = get_active_assignment_reopening(assignment.id, student_id)
    if not is_assignment_open_for_student(assignment, student_id) and not reopening:
        return None, "This test is not currently open.", 403

    max_attempts = assignment.max_attempts
    if reopening and reopening.additional_attempts > 0:
        max_attempts = (assignment.max_attempts or 0) + reopening.additional_attempts
    used = Submission.query.filter_by(student_id=student_id, assignment_id=assignment.id).count()
    if max_attempts and used >= max_attempts:
        return None, f"You have used all {max_attempts} attempt(s) for this test.", 403

    now = datetime.utcnow()
    session = TestSession(
        assignment_id=assignment.id,
        student_id=student_id,
        started_at=now,
        consent_at=now,
        status="active",
    )
    db.session.add(session)
    db.session.commit()
    return {
        "success": True,
        "session": session_brief(session),
        "time_limit_seconds": assignment.time_limit_minutes * 60 if assignment.time_limit_minutes else None,
        "snapshot_interval_seconds": 10,
    }, None, 200


def _owned_session(session_id: int, student_id: int) -> TestSession | None:
    session = TestSession.query.get(session_id)
    if not session or session.student_id != student_id:
        return None
    return session


def save_snapshot(session_id: int, student_id: int, kind: str, data: bytes) -> tuple[dict[str, Any] | None, str | None, int]:
    session = _owned_session(session_id, student_id)
    if not session:
        return None, "Test session not found.", 404
    if session.status != "active":
        return {"success": False, "status": session.status}, None, 200
    if kind not in ("screen", "camera"):
        return None, "Invalid snapshot kind.", 400
    if not data or len(data) > MAX_SNAPSHOT_BYTES:
        return None, "Snapshot is empty or too large.", 413
    if not data.startswith(b"\xff\xd8"):
        return None, "Snapshot must be a JPEG image.", 400
    if TestMonitorSnapshot.query.filter_by(session_id=session.id).count() >= MAX_SNAPSHOTS_PER_SESSION:
        return {"success": False, "message": "Snapshot limit reached."}, None, 200
    db.session.add(
        TestMonitorSnapshot(session_id=session.id, kind=kind, image=data, size_bytes=len(data))
    )
    db.session.commit()
    return {"success": True}, None, 200


def save_events(
    session_id: int, student_id: int, events: Any, answers: Any
) -> tuple[dict[str, Any] | None, str | None, int]:
    session = _owned_session(session_id, student_id)
    if not session:
        return None, "Test session not found.", 404
    if session.status != "active":
        return {"success": False, "status": session.status}, None, 200
    if isinstance(events, list) and events:
        raw = json.dumps(events[:5000])
        if len(raw) <= MAX_EVENTS_BATCH_CHARS:
            db.session.add(TestMonitorEvent(session_id=session.id, events_json=raw))
    if isinstance(answers, dict):
        raw_answers = json.dumps(answers)
        if len(raw_answers) <= MAX_ANSWERS_CHARS:
            session.last_answers_json = raw_answers
    db.session.commit()
    return {"success": True, "status": session.status}, None, 200


def report_violation(
    session_id: int, student_id: int, reason: str, answers: Any
) -> tuple[dict[str, Any] | None, str | None, int]:
    session = _owned_session(session_id, student_id)
    if not session:
        return None, "Test session not found.", 404
    reason = (reason or "tab_hidden").strip()[:50]
    db.session.add(
        TestMonitorEvent(
            session_id=session.id,
            events_json=json.dumps([{"t": int(datetime.utcnow().timestamp() * 1000), "type": "violation", "reason": reason}]),
        )
    )
    db.session.commit()
    return lock_test_session(session, reason, answers if isinstance(answers, dict) else None)


def lock_stale_session_on_load(assignment: Assignment, student_id: int) -> None:
    """Opening the test page while a session is still active means the student left and came back."""
    if not is_test_mode(assignment):
        return
    session = active_test_session(assignment.id, student_id)
    if session:
        lock_test_session(session, "reload")


def cleanup_old_test_snapshots(days: int = SNAPSHOT_RETENTION_DAYS) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    old_ids = [
        row.id for row in TestSession.query.with_entities(TestSession.id).filter(TestSession.started_at < cutoff).all()
    ]
    if not old_ids:
        return 0
    deleted = TestMonitorSnapshot.query.filter(TestMonitorSnapshot.session_id.in_(old_ids)).delete(
        synchronize_session=False
    )
    TestMonitorEvent.query.filter(TestMonitorEvent.session_id.in_(old_ids)).delete(synchronize_session=False)
    db.session.commit()
    return int(deleted or 0)
