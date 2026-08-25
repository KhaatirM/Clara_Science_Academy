"""Device repair ticket payloads for the Tech SPA."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from models import DeviceRepairTicket, Student, StudentDevice, User, db

REPAIR_CATEGORIES = ("hardware", "software")
REPAIR_SEVERITIES = ("low", "medium", "high", "critical")
REPAIR_STATUSES = ("open", "in_progress", "repaired", "closed")
RESOLVED_STATUSES = frozenset({"repaired", "closed"})

CATEGORY_LABELS = {
    "hardware": "Hardware Issues",
    "software": "Software Issues",
}


def _fmt(value) -> str | None:
    if not value:
        return None
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        pass
    return str(value)


def _student_brief(student: Student | None) -> dict[str, Any] | None:
    if not student:
        return None
    return {
        "id": student.id,
        "name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
        "student_id": student.student_id,
        "grade_level": student.grade_level,
    }


def _device_brief(device: StudentDevice | None) -> dict[str, Any] | None:
    if not device:
        return None
    from tech_routes.spa_helpers import DEVICE_COLOR_LABELS

    color = getattr(device, "color", None)
    return {
        "id": device.id,
        "device_type": device.device_type,
        "asset_name": device.asset_name,
        "device_name": device.device_name,
        "color": color,
        "color_label": DEVICE_COLOR_LABELS.get(color or "") if color else None,
        "student": _student_brief(device.student),
    }


def _user_brief(user: User | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {"id": user.id, "username": user.username}


def _normalize_category(raw) -> str:
    value = (raw or "").strip().lower()
    if value in REPAIR_CATEGORIES:
        return value
    return "hardware"


def _serialize_ticket(ticket: DeviceRepairTicket) -> dict[str, Any]:
    category = _normalize_category(getattr(ticket, "category", None))
    return {
        "id": ticket.id,
        "device_id": ticket.device_id,
        "title": ticket.title,
        "description": ticket.description,
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Hardware Issues"),
        "severity": ticket.severity,
        "status": ticket.status,
        "resolution_notes": ticket.resolution_notes,
        "created_display": _fmt(ticket.created_at),
        "updated_display": _fmt(ticket.updated_at),
        "resolved_display": _fmt(ticket.resolved_at),
        "device": _device_brief(ticket.device),
        "creator": _user_brief(ticket.creator),
        "resolver": _user_brief(ticket.resolver),
    }


def build_repair_tickets_list_payload(
    *,
    status: str = "",
    category: str = "",
    search: str = "",
    device_id: int | None = None,
) -> dict[str, Any]:
    status = (status or "").strip().lower()
    category = (category or "").strip().lower()
    search = (search or "").strip()

    q = DeviceRepairTicket.query.options(
        joinedload(DeviceRepairTicket.device).joinedload(StudentDevice.student),
        joinedload(DeviceRepairTicket.creator),
        joinedload(DeviceRepairTicket.resolver),
    )
    if status in REPAIR_STATUSES:
        q = q.filter(DeviceRepairTicket.status == status)
    if category in REPAIR_CATEGORIES:
        q = q.filter(DeviceRepairTicket.category == category)
    if device_id is not None:
        q = q.filter(DeviceRepairTicket.device_id == int(device_id))
    if search:
        like = f"%{search}%"
        q = (
            q.join(StudentDevice, DeviceRepairTicket.device_id == StudentDevice.id)
            .outerjoin(Student, StudentDevice.student_id == Student.id)
            .filter(
                or_(
                    DeviceRepairTicket.title.ilike(like),
                    DeviceRepairTicket.description.ilike(like),
                    StudentDevice.asset_name.ilike(like),
                    StudentDevice.device_name.ilike(like),
                    Student.first_name.ilike(like),
                    Student.last_name.ilike(like),
                    Student.student_id.ilike(like),
                )
            )
        )

    tickets = q.order_by(DeviceRepairTicket.created_at.desc()).all()
    open_count = sum(1 for t in tickets if t.status == "open")
    in_progress_count = sum(1 for t in tickets if t.status == "in_progress")
    repaired_count = sum(1 for t in tickets if t.status == "repaired")
    closed_count = sum(1 for t in tickets if t.status == "closed")
    hardware_count = sum(1 for t in tickets if _normalize_category(t.category) == "hardware")
    software_count = sum(1 for t in tickets if _normalize_category(t.category) == "software")

    devices = (
        StudentDevice.query.options(joinedload(StudentDevice.student))
        .order_by(StudentDevice.asset_name)
        .all()
    )

    return {
        "tickets": [_serialize_ticket(t) for t in tickets],
        "counts": {
            "total": len(tickets),
            "open": open_count,
            "in_progress": in_progress_count,
            "repaired": repaired_count,
            "closed": closed_count,
            "hardware": hardware_count,
            "software": software_count,
        },
        "devices": [_device_brief(d) for d in devices],
        "categories": [
            {"value": key, "label": CATEGORY_LABELS[key]} for key in REPAIR_CATEGORIES
        ],
        "severities": list(REPAIR_SEVERITIES),
        "statuses": list(REPAIR_STATUSES),
    }


def create_repair_ticket(body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    try:
        device_id = int(body.get("device_id"))
    except (TypeError, ValueError):
        return None, "Select a device for this repair ticket.", 400

    device = StudentDevice.query.get(device_id)
    if not device:
        return None, "Device not found.", 404

    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    severity = (body.get("severity") or "medium").strip().lower()
    category = _normalize_category(body.get("category"))
    if not title:
        return None, "Please provide a title.", 400
    if not description:
        return None, "Please describe the repair needed.", 400
    if severity not in REPAIR_SEVERITIES:
        severity = "medium"

    ticket = DeviceRepairTicket(
        device_id=device.id,
        title=title[:200],
        description=description,
        category=category,
        severity=severity,
        status="open",
        created_by=current_user.id,
    )
    db.session.add(ticket)
    db.session.commit()
    ticket = (
        DeviceRepairTicket.query.options(
            joinedload(DeviceRepairTicket.device).joinedload(StudentDevice.student),
            joinedload(DeviceRepairTicket.creator),
        )
        .filter_by(id=ticket.id)
        .first()
    )
    return {
        "success": True,
        "message": "Repair ticket created.",
        "ticket": _serialize_ticket(ticket),
    }, None, 200


def update_repair_ticket_status(
    ticket_id: int, body: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None, int]:
    ticket = DeviceRepairTicket.query.get(ticket_id)
    if not ticket:
        return None, "Ticket not found.", 404

    new_status = (body.get("status") or "").strip().lower()
    if new_status not in REPAIR_STATUSES:
        return None, "Invalid status.", 400

    notes = (body.get("resolution_notes") or "").strip()
    ticket.status = new_status
    if notes:
        ticket.resolution_notes = notes

    if new_status in RESOLVED_STATUSES:
        ticket.resolved_at = datetime.utcnow()
        ticket.resolved_by = current_user.id
        if notes:
            ticket.resolution_notes = notes
    elif new_status in ("open", "in_progress"):
        ticket.resolved_at = None
        ticket.resolved_by = None

    db.session.commit()
    ticket = (
        DeviceRepairTicket.query.options(
            joinedload(DeviceRepairTicket.device).joinedload(StudentDevice.student),
            joinedload(DeviceRepairTicket.creator),
            joinedload(DeviceRepairTicket.resolver),
        )
        .filter_by(id=ticket_id)
        .first()
    )
    return {
        "success": True,
        "message": "Ticket status updated.",
        "ticket": _serialize_ticket(ticket),
        "status": new_status,
    }, None, 200
