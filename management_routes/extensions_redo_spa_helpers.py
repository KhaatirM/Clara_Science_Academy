"""Extensions & redo dashboard payloads for the React management SPA."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask_login import current_user
from sqlalchemy.orm import joinedload

from models import (
    Assignment,
    AssignmentRedo,
    AssignmentReopening,
    ExtensionRequest,
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


def _serialize_redo(redo: AssignmentRedo, *, now: datetime) -> dict[str, Any]:
    assignment = redo.assignment
    student = redo.student
    class_info = assignment.class_info if assignment else None
    is_overdue = bool(
        (not redo.is_used)
        and (not redo.final_grade)
        and redo.redo_deadline
        and (_as_utc_aware(redo.redo_deadline) < now)
    )
    if redo.final_grade:
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
        "original_grade": redo.original_grade,
        "redo_grade": redo.redo_grade,
        "final_grade": redo.final_grade,
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

    serialized_redos = [_serialize_redo(r, now=now) for r in redos]
    active_redos = len([r for r in redos if not r.is_used and not r.final_grade])
    completed_redos = len([r for r in redos if r.final_grade])
    overdue_redos = len([r for r in serialized_redos if r["is_overdue"]])
    active_reopenings = len(reopenings)

    improvements: list[float] = []
    for redo in redos:
        if redo.original_grade and redo.final_grade:
            improvement = redo.final_grade - redo.original_grade
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
