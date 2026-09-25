"""Teacher review of lockdown test sessions: monitoring data, unlock, delete recordings."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from flask_login import current_user
from sqlalchemy import func

from models import (
    AssignmentReopening,
    Submission,
    TeacherStaff,
    TestMonitorEvent,
    TestMonitorSnapshot,
    TestSession,
    db,
)
from student_routes.test_lockdown_helpers import lock_reason_label


def _iso(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def test_sessions_by_student(assignment_id: int) -> dict[int, list[dict[str, Any]]]:
    sessions = TestSession.query.filter_by(assignment_id=assignment_id).order_by(TestSession.id.asc()).all()
    if not sessions:
        return {}
    ids = [s.id for s in sessions]
    snap_counts = dict(
        db.session.query(TestMonitorSnapshot.session_id, func.count(TestMonitorSnapshot.id))
        .filter(TestMonitorSnapshot.session_id.in_(ids))
        .group_by(TestMonitorSnapshot.session_id)
        .all()
    )
    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for s in sessions:
        out[s.student_id].append(
            {
                "id": s.id,
                "status": s.status,
                "lock_reason": s.lock_reason,
                "lock_reason_label": lock_reason_label(s.lock_reason) if s.lock_reason else None,
                "started_at": _iso(s.started_at),
                "ended_at": _iso(s.ended_at),
                "locked_at": _iso(s.locked_at),
                "unlocked_at": _iso(s.unlocked_at),
                "submission_id": s.submission_id,
                "snapshot_count": int(snap_counts.get(s.id, 0)),
            }
        )
    return dict(out)


def _session_for(assignment_id: int, session_id: int) -> TestSession | None:
    session = TestSession.query.get(session_id)
    if not session or session.assignment_id != assignment_id:
        return None
    return session


def query_test_session_monitor(assignment_id: int, session_id: int) -> tuple[dict[str, Any] | None, int]:
    session = _session_for(assignment_id, session_id)
    if not session:
        return None, 404
    snaps = (
        TestMonitorSnapshot.query.with_entities(
            TestMonitorSnapshot.id, TestMonitorSnapshot.kind, TestMonitorSnapshot.captured_at
        )
        .filter_by(session_id=session.id)
        .order_by(TestMonitorSnapshot.captured_at.asc(), TestMonitorSnapshot.id.asc())
        .all()
    )
    events: list[dict[str, Any]] = []
    for row in TestMonitorEvent.query.filter_by(session_id=session.id).order_by(TestMonitorEvent.id.asc()).all():
        try:
            batch = json.loads(row.events_json)
        except Exception:
            continue
        if isinstance(batch, list):
            events.extend(e for e in batch if isinstance(e, dict))
    events.sort(key=lambda e: e.get("t") or 0)
    student = session.student
    return {
        "session": {
            "id": session.id,
            "status": session.status,
            "lock_reason": session.lock_reason,
            "lock_reason_label": lock_reason_label(session.lock_reason) if session.lock_reason else None,
            "started_at": _iso(session.started_at),
            "ended_at": _iso(session.ended_at),
            "locked_at": _iso(session.locked_at),
            "unlocked_at": _iso(session.unlocked_at),
            "submission_id": session.submission_id,
        },
        "student": {
            "id": student.id if student else None,
            "name": f"{student.first_name} {student.last_name}".strip() if student else "Student",
        },
        "snapshots": [
            {"id": s.id, "kind": s.kind, "captured_at": _iso(s.captured_at)} for s in snaps
        ],
        "events": events,
    }, 200


def test_snapshot_bytes(assignment_id: int, session_id: int, snapshot_id: int) -> bytes | None:
    session = _session_for(assignment_id, session_id)
    if not session:
        return None
    snap = TestMonitorSnapshot.query.get(snapshot_id)
    if not snap or snap.session_id != session.id:
        return None
    return snap.image


def _current_teacher_staff_id() -> int | None:
    staff_id = getattr(current_user, "teacher_staff_id", None)
    if staff_id and TeacherStaff.query.get(staff_id):
        return staff_id
    fallback = TeacherStaff.query.first()
    return fallback.id if fallback else None


def unlock_test_session(assignment_id: int, session_id: int) -> tuple[dict[str, Any], int]:
    session = _session_for(assignment_id, session_id)
    if not session:
        return {"success": False, "message": "Test session not found."}, 404
    if session.status != "locked":
        return {"success": False, "message": "This test attempt is not locked."}, 400
    assignment = session.assignment
    staff_id = _current_teacher_staff_id()
    if not staff_id:
        return {"success": False, "message": "No teacher record found to grant the retake."}, 400

    used = Submission.query.filter_by(assignment_id=assignment_id, student_id=session.student_id).count()
    base = int(assignment.max_attempts or 0)
    needed_extra = max(0, used + 1 - base) if base else 0

    existing = AssignmentReopening.query.filter_by(
        assignment_id=assignment_id, student_id=session.student_id, is_active=True
    ).all()
    for r in existing:
        needed_extra = max(needed_extra, int(r.additional_attempts or 0))
        r.is_active = False
    db.session.add(
        AssignmentReopening(
            assignment_id=assignment_id,
            student_id=session.student_id,
            reopened_by=staff_id,
            reason="Lockdown test unlocked by teacher",
            additional_attempts=needed_extra,
            is_active=True,
        )
    )
    session.status = "unlocked"
    session.unlocked_at = datetime.utcnow()
    session.unlocked_by = current_user.id
    db.session.commit()
    return {"success": True, "message": "Test unlocked. The student can take it one more time."}, 200


def delete_test_session_recordings(assignment_id: int, session_id: int) -> tuple[dict[str, Any], int]:
    session = _session_for(assignment_id, session_id)
    if not session:
        return {"success": False, "message": "Test session not found."}, 404
    TestMonitorSnapshot.query.filter_by(session_id=session.id).delete(synchronize_session=False)
    TestMonitorEvent.query.filter_by(session_id=session.id).delete(synchronize_session=False)
    db.session.commit()
    return {"success": True, "message": "Recordings deleted."}, 200
