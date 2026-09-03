"""Extensions & redo dashboard payloads for the React management SPA."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from flask_login import current_user
from sqlalchemy.orm import joinedload

from models import (
    Assignment,
    AssignmentRedo,
    AssignmentReopening,
    ExtensionRequest,
    Grade,
    RedoRequest,
    TeacherStaff,
)
from teacher_routes.assignment_utils import _as_utc_aware
from utils.school_year_filters import (
    assignment_redos_query,
    assignment_reopenings_query,
    classes_for_active_school_year,
    extension_requests_query,
    get_active_school_year,
    redo_requests_query,
    teacher_class_ids_active_school_year,
)


def _iso(dt: Any) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _student_name(student) -> str:
    if not student:
        return "Unknown"
    return f"{student.first_name or ''} {student.last_name or ''}".strip() or "Unknown"


def _serialize_extension_request(req: ExtensionRequest) -> dict[str, Any]:
    assignment = req.assignment
    student = req.student
    class_info = assignment.class_info if assignment else None
    search_parts = [
        _student_name(student),
        assignment.title if assignment else "",
        class_info.name if class_info else "",
    ]
    return {
        "id": req.id,
        "status": req.status,
        "reason": req.reason or "",
        "review_notes": req.review_notes or "",
        "requested_at": _iso(req.requested_at),
        "reviewed_at": _iso(req.reviewed_at),
        "requested_due_date": _iso(req.requested_due_date),
        "current_due_date": _iso(assignment.due_date) if assignment else None,
        "student": {
            "id": student.id if student else None,
            "display_name": _student_name(student),
        },
        "assignment": {
            "id": assignment.id if assignment else None,
            "title": assignment.title if assignment else "Unknown",
        },
        "class": {
            "id": class_info.id if class_info else None,
            "name": class_info.name if class_info else "Unknown",
        },
        "search_text": " ".join(p for p in search_parts if p).lower(),
    }


def query_teacher_extensions_hub() -> dict[str, Any]:
    """Extension requests visible to the current teacher (or all for school admins)."""
    from teacher_routes.utils import get_teacher_or_admin, is_admin
    from utils.school_year_filters import teacher_class_ids_active_school_year

    active = get_active_school_year()
    teacher = get_teacher_or_admin()
    if is_admin():
        rows = (
            extension_requests_query()
            .options(
                joinedload(ExtensionRequest.assignment).joinedload(Assignment.class_info),
                joinedload(ExtensionRequest.student),
            )
            .order_by(ExtensionRequest.requested_at.desc())
            .all()
        )
    elif teacher is None:
        rows = []
    else:
        class_ids = teacher_class_ids_active_school_year(teacher.id)
        rows = (
            extension_requests_query(class_ids=class_ids)
            .options(
                joinedload(ExtensionRequest.assignment).joinedload(Assignment.class_info),
                joinedload(ExtensionRequest.student),
            )
            .order_by(ExtensionRequest.requested_at.desc())
            .all()
        )
    items = [_serialize_extension_request(r) for r in rows if r.assignment and r.student]
    pending = [i for i in items if i["status"] == "Pending"]
    approved = [i for i in items if i["status"] == "Approved"]
    rejected = [i for i in items if i["status"] == "Rejected"]
    return {
        "items": items,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "stats": {
            "total": len(items),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
        },
        "meta": {
            "active_school_year_id": active.id if active else None,
            "active_school_year_name": active.name if active else None,
            "has_active_school_year": active is not None,
            "scope": "teacher",
        },
    }


def query_extensions_hub() -> dict[str, Any]:
    """All extension requests for the active school year, grouped by status."""
    active = get_active_school_year()
    rows = (
        extension_requests_query()
        .options(
            joinedload(ExtensionRequest.assignment).joinedload(Assignment.class_info),
            joinedload(ExtensionRequest.student),
        )
        .order_by(ExtensionRequest.requested_at.desc())
        .all()
    )
    items = [_serialize_extension_request(r) for r in rows if r.assignment and r.student]
    pending = [i for i in items if i["status"] == "Pending"]
    approved = [i for i in items if i["status"] == "Approved"]
    rejected = [i for i in items if i["status"] == "Rejected"]
    return {
        "items": items,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "stats": {
            "total": len(items),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
        },
        "meta": {
            "active_school_year_id": active.id if active else None,
            "active_school_year_name": active.name if active else None,
            "has_active_school_year": active is not None,
        },
    }


def _redo_visibility() -> tuple[bool, TeacherStaff | None, list[int], list]:
    """Return (is_teacher_scoped, teacher, class_ids, classes)."""
    is_school_admin = current_user.role in ("Director", "School Administrator")
    is_teacher_user = (not is_school_admin) and bool(getattr(current_user, "teacher_staff_id", None))

    teacher = None
    if is_teacher_user:
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        if not teacher:
            return True, None, [], []
        class_ids = teacher_class_ids_active_school_year(teacher.id)
        classes = classes_for_active_school_year(class_ids=class_ids)
        return True, teacher, class_ids, classes

    classes = classes_for_active_school_year()
    class_ids = [c.id for c in classes]
    return False, None, class_ids, classes


def _serialize_redo_request(rr: RedoRequest) -> dict[str, Any]:
    assignment = rr.assignment
    student = rr.student
    class_info = assignment.class_info if assignment else None
    return {
        "id": rr.id,
        "assignment_id": rr.assignment_id,
        "reason": rr.reason or "",
        "requested_at": _iso(rr.requested_at),
        "student": {
            "id": student.id if student else None,
            "display_name": _student_name(student),
        },
        "assignment": {
            "id": assignment.id if assignment else None,
            "title": assignment.title if assignment else "Unknown",
        },
        "class": {
            "id": class_info.id if class_info else None,
            "name": class_info.name if class_info else "Unknown",
        },
        "search_text": " ".join(
            filter(
                None,
                [
                    _student_name(student),
                    assignment.title if assignment else "",
                    class_info.name if class_info else "",
                ],
            )
        ).lower(),
    }


def _serialize_reopening(r: AssignmentReopening) -> dict[str, Any]:
    assignment = r.assignment
    student = r.student
    class_info = assignment.class_info if assignment else None
    return {
        "id": r.id,
        "reopened_at": _iso(r.reopened_at),
        "additional_attempts": r.additional_attempts or 0,
        "student": {
            "id": student.id if student else None,
            "display_name": _student_name(student),
        },
        "assignment": {
            "id": assignment.id if assignment else None,
            "title": assignment.title if assignment else "Unknown",
        },
        "class": {
            "id": class_info.id if class_info else None,
            "name": class_info.name if class_info else "Unknown",
        },
        "status": "reopened",
        "search_text": " ".join(
            filter(
                None,
                [
                    _student_name(student),
                    assignment.title if assignment else "",
                    class_info.name if class_info else "",
                ],
            )
        ).lower(),
    }


def _recorded_grade_scores(redos: list[AssignmentRedo]) -> dict[tuple[int, int], float]:
    """Actual graded scores keyed by (assignment_id, student_id).

    Redos granted before grading closed them out have ``final_grade = NULL``;
    reading the real Grade row keeps those from being reported as pending.
    """
    if not redos:
        return {}
    pairs = {(r.assignment_id, r.student_id) for r in redos}
    assignment_ids = {a for a, _ in pairs}
    student_ids = {s for _, s in pairs}
    scores: dict[tuple[int, int], float] = {}
    rows = (
        Grade.query.filter(
            Grade.assignment_id.in_(assignment_ids), Grade.student_id.in_(student_ids)
        )
        .order_by(Grade.graded_at.asc())
        .all()
    )
    for row in rows:
        key = (row.assignment_id, row.student_id)
        if key not in pairs or getattr(row, "is_voided", False):
            continue
        try:
            data = json.loads(row.grade_data) if isinstance(row.grade_data, str) else row.grade_data
        except (TypeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        value = data.get("score")
        if value is None:
            value = data.get("points_earned")
        if value is None:
            continue
        try:
            scores[key] = float(value)
        except (TypeError, ValueError):
            continue
    return scores


def _assignment_total_points(assignment) -> float:
    try:
        total = float(getattr(assignment, "total_points", None) or 0)
    except (TypeError, ValueError):
        total = 0.0
    return total if total > 0 else 100.0


def _points_to_percent(points: float | None, total_points: float) -> float | None:
    if points is None:
        return None
    try:
        pts = float(points)
        total = float(total_points) if total_points and float(total_points) > 0 else 100.0
        return round(pts / total * 100.0, 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _serialize_redo(
    redo: AssignmentRedo,
    *,
    now: datetime,
    recorded_scores: dict[tuple[int, int], float] | None = None,
) -> dict[str, Any]:
    assignment = redo.assignment
    student = redo.student
    class_info = assignment.class_info if assignment else None
    total_points = _assignment_total_points(assignment)

    final_grade = redo.final_grade
    if final_grade is None and recorded_scores is not None:
        final_grade = recorded_scores.get((redo.assignment_id, redo.student_id))
    has_final = final_grade is not None
    redo_grade = redo.redo_grade if redo.redo_grade is not None else final_grade

    is_overdue = bool(
        (not redo.is_used)
        and (not has_final)
        and redo.redo_deadline
        and (_as_utc_aware(redo.redo_deadline) < now)
    )
    if has_final:
        status = "graded"
    elif redo.is_used:
        status = "submitted"
    elif is_overdue:
        status = "overdue"
    else:
        status = "pending"
    return {
        "id": redo.id,
        "assignment_id": redo.assignment_id,
        "reason": redo.reason or "",
        # Scores are stored as points earned (not percent). Expose both.
        "total_points": total_points,
        "original_grade": redo.original_grade,
        "original_percent": _points_to_percent(redo.original_grade, total_points),
        "redo_grade": redo_grade,
        "redo_percent": _points_to_percent(redo_grade, total_points),
        "final_grade": final_grade,
        "final_percent": _points_to_percent(final_grade, total_points),
        "was_redo_late": bool(redo.was_redo_late),
        "is_used": bool(redo.is_used),
        "is_overdue": is_overdue,
        "redo_deadline": _iso(redo.redo_deadline),
        "granted_at": _iso(redo.granted_at),
        "status": status,
        "student": {
            "id": student.id if student else None,
            "display_name": _student_name(student),
            "grade_level": getattr(student, "grade_level", None),
        },
        "assignment": {
            "id": assignment.id if assignment else None,
            "title": assignment.title if assignment else "Unknown",
            "total_points": total_points,
        },
        "class": {
            "id": class_info.id if class_info else None,
            "name": class_info.name if class_info else "Unknown",
        },
        "grade_url": f"/management/grade/assignment/{redo.assignment_id}" if assignment else None,
        "search_text": " ".join(
            filter(
                None,
                [
                    _student_name(student),
                    assignment.title if assignment else "",
                    class_info.name if class_info else "",
                ],
            )
        ).lower(),
    }


def query_redo_dashboard() -> dict[str, Any]:
    """Redo dashboard payload mirroring legacy redo_dashboard()."""
    active = get_active_school_year()
    now = datetime.now(timezone.utc)
    if not active:
        return {
            "redo_requests": [],
            "reopenings": [],
            "redos": [],
            "classes": [],
            "stats": {
                "active_redos": 0,
                "completed_redos": 0,
                "active_reopenings": 0,
                "improvement_rate": 0,
                "overdue_redos": 0,
            },
            "meta": {
                "active_school_year_id": None,
                "active_school_year_name": None,
                "has_active_school_year": False,
            },
        }

    is_teacher_scoped, teacher, class_ids, classes = _redo_visibility()
    if is_teacher_scoped and teacher is None:
        return {
            "redo_requests": [],
            "reopenings": [],
            "redos": [],
            "classes": [],
            "stats": {
                "active_redos": 0,
                "completed_redos": 0,
                "active_reopenings": 0,
                "improvement_rate": 0,
                "overdue_redos": 0,
            },
            "meta": {
                "active_school_year_id": active.id,
                "active_school_year_name": active.name,
                "has_active_school_year": True,
                "teacher_not_found": True,
            },
        }

    if is_teacher_scoped:
        redos_q = assignment_redos_query(class_ids=class_ids)
        reopenings_q = assignment_reopenings_query(class_ids=class_ids)
        requests_q = redo_requests_query(class_ids=class_ids, status="Pending")
    else:
        redos_q = assignment_redos_query()
        reopenings_q = assignment_reopenings_query()
        requests_q = redo_requests_query(status="Pending")

    redos = (
        redos_q.options(
            joinedload(AssignmentRedo.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentRedo.student),
        )
        .order_by(AssignmentRedo.redo_deadline.asc())
        .all()
    )
    reopenings = (
        reopenings_q.options(
            joinedload(AssignmentReopening.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentReopening.student),
        )
        .order_by(AssignmentReopening.reopened_at.desc())
        .all()
    )
    redo_requests = (
        requests_q.options(
            joinedload(RedoRequest.assignment).joinedload(Assignment.class_info),
            joinedload(RedoRequest.student),
        )
        .order_by(RedoRequest.requested_at.desc())
        .all()
    )

    redos = [r for r in redos if r.assignment and r.student]
    reopenings = [r for r in reopenings if r.assignment and r.student]
    redo_requests = [r for r in redo_requests if r.assignment and r.student]

    recorded_scores = _recorded_grade_scores(redos)
    serialized_redos = [
        _serialize_redo(r, now=now, recorded_scores=recorded_scores) for r in redos
    ]
    active_redos = len([r for r in serialized_redos if r["status"] in ("pending", "submitted")])
    completed_redos = len([r for r in serialized_redos if r["status"] == "graded"])
    overdue_redos = len([r for r in serialized_redos if r["is_overdue"]])
    active_reopenings = len(reopenings)

    improvements: list[float] = []
    for row in serialized_redos:
        original_pct = row.get("original_percent")
        final_pct = row.get("final_percent")
        if original_pct is not None and final_pct is not None:
            improvement = float(final_pct) - float(original_pct)
            if improvement > 0:
                improvements.append(improvement)
    improvement_rate = round(sum(improvements) / len(improvements), 1) if improvements else 0

    return {
        "redo_requests": [_serialize_redo_request(r) for r in redo_requests],
        "reopenings": [_serialize_reopening(r) for r in reopenings],
        "redos": serialized_redos,
        "classes": [{"id": c.id, "name": c.name} for c in classes],
        "stats": {
            "active_redos": active_redos,
            "completed_redos": completed_redos,
            "active_reopenings": active_reopenings,
            "improvement_rate": improvement_rate,
            "overdue_redos": overdue_redos,
        },
        "meta": {
            "active_school_year_id": active.id,
            "active_school_year_name": active.name,
            "has_active_school_year": True,
        },
    }
