"""Tech portal payloads and mutations for the React SPA."""

from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import current_app, request, session
from flask_login import current_user, login_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from models import (
    ActivityLog,
    AdminAuditLog,
    BugReport,
    MaintenanceMode,
    Student,
    StudentDevice,
    SystemConfig,
    TeacherStaff,
    User,
    db,
)
from utils.tech_user_management import (
    build_tech_user_management_lists,
    user_portal_status_label,
)

DEVICE_TYPES = ("laptop", "tablet")


def _fmt(value) -> str | None:
    if not value:
        return None
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        pass
    return str(value)


def _iso(value) -> str | None:
    if not value:
        return None
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _maintenance_payload(maintenance: MaintenanceMode | None) -> dict[str, Any] | None:
    if not maintenance:
        return None
    return {
        "is_active": bool(maintenance.is_active),
        "reason": maintenance.reason,
        "maintenance_message": maintenance.maintenance_message,
        "allow_tech_access": bool(getattr(maintenance, "allow_tech_access", True)),
        "duration_minutes": maintenance.duration_minutes,
        "start_time": _iso(maintenance.start_time),
        "end_time": _iso(maintenance.end_time),
        "end_display": _fmt(maintenance.end_time),
    }


def build_tech_dashboard_payload() -> dict[str, Any]:
    from utils.maintenance_mode import get_active_maintenance

    maintenance = get_active_maintenance()
    return {
        "username": current_user.username,
        "role": current_user.role,
        "maintenance": _maintenance_payload(maintenance),
        "cards": [
            {"id": "devices", "title": "Devices", "blurb": "Student laptop and tablet inventory", "url": "/app/tech/devices", "icon": "bi-laptop"},
            {"id": "logs", "title": "Logs", "blurb": "User activity and HTTP audit trail", "url": "/app/tech/logs", "icon": "bi-list-check"},
            {"id": "bugs", "title": "Bugs", "blurb": "Error log and user-submitted reports", "url": "/app/tech/bugs", "icon": "bi-bug-fill"},
            {"id": "system", "title": "System", "blurb": "Status, configuration, maintenance", "url": "/app/tech/system", "icon": "bi-hdd-stack-fill"},
            {"id": "users", "title": "User Management", "blurb": "Accounts, resets, impersonation", "url": "/app/tech/users", "icon": "bi-people-fill"},
            {"id": "settings", "title": "Settings", "blurb": "Password and theme preferences", "url": "/app/tech/settings", "icon": "bi-gear-fill"},
        ],
        "quick_actions": [
            {"id": "backup", "label": "Backup database", "action": "backup"},
            {"id": "integrity", "label": "Check integrity", "action": "integrity"},
            {"id": "clear_cache", "label": "Clear cache", "action": "clear_cache"},
        ],
    }


def build_tech_settings_payload() -> dict[str, Any]:
    from management_routes.settings_spa_helpers import query_settings_hub

    hub = query_settings_hub(user=current_user)
    hub["urls"] = {
        **(hub.get("urls") or {}),
        "home": "/app/tech",
        "change_password": "/change-password",
    }
    hub["google"] = {"connected": False, "show_section": False}
    return hub


# --- Devices -----------------------------------------------------------------


def _normalize_device_type(raw) -> str | None:
    t = (raw or "").strip().lower()
    return t if t in DEVICE_TYPES else None


def _device_type_fits_grade(device_type, grade_level) -> bool:
    if grade_level is None:
        return True
    try:
        g = int(grade_level)
    except (TypeError, ValueError):
        return True
    if g >= 3:
        return device_type == "laptop"
    return device_type == "tablet"


def _expected_device_label(grade_level) -> str | None:
    if grade_level is None:
        return None
    try:
        g = int(grade_level)
    except (TypeError, ValueError):
        return None
    return "laptop" if g >= 3 else "tablet"


def _students_selectable_for_device(exclude_device_id=None):
    assigned_ids = {
        d.student_id
        for d in StudentDevice.query.all()
        if d.student_id is not None
        and (exclude_device_id is None or d.id != exclude_device_id)
    }
    from utils.student_roster import active_roster_student_filters

    q = Student.query.filter(active_roster_student_filters())
    if assigned_ids:
        q = q.filter(~Student.id.in_(assigned_ids))
    return q.order_by(Student.last_name, Student.first_name).all()


def _serialize_student_option(s: Student) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": f"{s.first_name or ''} {s.last_name or ''}".strip(),
        "student_id": s.student_id,
        "grade_level": s.grade_level,
        "expected_device_type": _expected_device_label(s.grade_level),
    }


def _serialize_device(d: StudentDevice) -> dict[str, Any]:
    stu = d.student
    return {
        "id": d.id,
        "device_type": d.device_type,
        "asset_name": d.asset_name,
        "device_name": d.device_name,
        "cord_number": d.cord_number,
        "operating_system": d.operating_system,
        "student_id": d.student_id,
        "assigned": d.student_id is not None,
        "created_display": _fmt(d.created_at),
        "updated_display": _fmt(d.updated_at),
        "student": _serialize_student_option(stu) if stu else None,
    }


def build_devices_list_payload(
    *,
    device_type: str = "",
    search: str = "",
    assignment: str = "",
) -> dict[str, Any]:
    from sqlalchemy import or_

    device_type = (device_type or "").strip().lower()
    search = (search or "").strip()
    assignment = (assignment or "").strip().lower()
    q = StudentDevice.query.outerjoin(Student, StudentDevice.student_id == Student.id)
    if device_type in DEVICE_TYPES:
        q = q.filter(StudentDevice.device_type == device_type)
    if assignment == "unassigned":
        q = q.filter(StudentDevice.student_id.is_(None))
    elif assignment == "assigned":
        q = q.filter(StudentDevice.student_id.isnot(None))
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                Student.first_name.ilike(like),
                Student.last_name.ilike(like),
                Student.student_id.ilike(like),
                StudentDevice.asset_name.ilike(like),
                StudentDevice.device_name.ilike(like),
                StudentDevice.cord_number.ilike(like),
            )
        )
    records = q.order_by(StudentDevice.device_type, StudentDevice.asset_name).all()
    pending_students = [
        {
            **_serialize_student_option(s),
        }
        for s in _students_selectable_for_device()
    ]
    unassigned_count = StudentDevice.query.filter(StudentDevice.student_id.is_(None)).count()
    return {
        "records": [_serialize_device(d) for d in records],
        "pending_students": pending_students,
        "counts": {
            "shown": len(records),
            "unassigned": unassigned_count,
            "pending_students": len(pending_students),
        },
        "filters": {"type": device_type, "q": search, "assignment": assignment},
        "device_types": list(DEVICE_TYPES),
    }


def build_device_form_payload(device_id: int | None = None) -> tuple[dict[str, Any] | None, str | None, int]:
    device = StudentDevice.query.get(device_id) if device_id else None
    if device_id and not device:
        return None, "Device not found", 404
    students = _students_selectable_for_device(exclude_device_id=device.id if device else None)
    if device and device.student and device.student not in students:
        students = sorted(
            students + [device.student],
            key=lambda s: ((s.last_name or "").lower(), (s.first_name or "").lower()),
        )
    return {
        "device": _serialize_device(device) if device else None,
        "students": [_serialize_student_option(s) for s in students],
        "device_types": list(DEVICE_TYPES),
    }, None, 200


def save_device(*, device_id: int | None, body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    device_type = _normalize_device_type(body.get("device_type"))
    asset_name = (body.get("asset_name") or "").strip()
    device_name = (body.get("device_name") or "").strip() or None
    cord_number = (body.get("cord_number") or "").strip() or None
    operating_system = (body.get("operating_system") or "").strip() or None
    raw_student = body.get("student_id")
    student_id = None
    if raw_student not in (None, "", "null"):
        try:
            student_id = int(raw_student)
        except (TypeError, ValueError):
            return None, "Invalid student selection.", 400

    if not device_type:
        return None, "Select a valid device type (laptop or tablet).", 400
    if not asset_name:
        return None, "Asset name is required.", 400

    stu = None
    if student_id is not None:
        stu = Student.query.get(student_id)
        if not stu:
            return None, "Student not found.", 404
        if not _device_type_fits_grade(device_type, stu.grade_level):
            exp = _expected_device_label(stu.grade_level)
            return (
                None,
                f"Device type does not match grade policy (expected {exp or 'appropriate type'}).",
                400,
            )

    if device_id:
        device = StudentDevice.query.get(device_id)
        if not device:
            return None, "Device not found", 404
        if student_id is not None:
            other = StudentDevice.query.filter(
                StudentDevice.student_id == student_id,
                StudentDevice.id != device.id,
            ).first()
            if other:
                return None, "That student already has a different device assigned.", 400
        device.device_type = device_type
        device.asset_name = asset_name
        device.device_name = device_name
        device.cord_number = cord_number
        device.operating_system = operating_system
        device.student_id = student_id
    else:
        if stu is not None and stu.assigned_school_device:
            return None, "That student already has a device assigned.", 400
        device = StudentDevice(
            device_type=device_type,
            asset_name=asset_name,
            device_name=device_name,
            cord_number=cord_number,
            operating_system=operating_system,
            student_id=student_id,
        )
        db.session.add(device)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "Could not save: duplicate asset name or conflicting assignment.", 400

    msg = "Device updated." if device_id else (
        "Device assigned successfully." if student_id else "Unassigned device added to inventory."
    )
    return {
        "success": True,
        "message": msg,
        "device": _serialize_device(device),
        "redirect": "/app/tech/devices",
    }, None, 200


def delete_device(device_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    device = StudentDevice.query.get(device_id)
    if not device:
        return None, "Device not found", 404
    db.session.delete(device)
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return None, f"Could not remove device: {exc}", 500
    return {"success": True, "message": "Device removed from inventory."}, None, 200


def bulk_upload_devices_from_csv(raw: bytes) -> tuple[dict[str, Any] | None, str | None, int]:
    """Import devices from CSV bytes. Blank student columns = unassigned stock."""
    import csv
    import io

    from tech_routes.routes import (
        _csv_cell,
        _norm_csv_header,
        _normalize_device_type as legacy_normalize_device_type,
        _student_from_csv_row,
        _upsert_device_from_csv_row,
    )

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None, "Could not read file as UTF-8. Save the spreadsheet as CSV UTF-8.", 400

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return None, "CSV has no header.", 400

    headers = [_norm_csv_header(h) for h in reader.fieldnames]
    if "device_type" not in headers or "asset_name" not in headers:
        return None, "CSV must include columns: device_type, asset_name (see Download template).", 400

    created = updated = 0
    errors: list[str] = []
    row_num = 1

    for raw_row in reader:
        row_num += 1
        if not raw_row or not any((v and str(v).strip()) for v in raw_row.values()):
            continue
        row: dict[str, str] = {}
        for k, v in raw_row.items():
            if k is None:
                continue
            nk = _norm_csv_header(k)
            row[nk] = "" if v is None or v == "" else str(v).strip()

        device_type = legacy_normalize_device_type(_csv_cell(row, "device_type", "type"))
        asset_name = _csv_cell(row, "asset_name", "laptop_name", "tablet_name", "inventory_name")
        device_name = _csv_cell(row, "device_name") or None
        cord_number = _csv_cell(row, "cord_number", "cord", "cord_#") or None
        operating_system = _csv_cell(row, "operating_system", "os") or None

        if not device_type:
            errors.append(f"Row {row_num}: invalid or missing device_type")
            continue
        if not asset_name:
            errors.append(f"Row {row_num}: missing asset_name")
            continue

        has_student_hint = bool(
            _csv_cell(
                row,
                "student_db_id",
                "student_pk",
                "db_student_id",
                "internal_student_id",
                "school_student_id",
                "school_id",
                "state_student_id",
                "student_id_number",
                "student_id",
            )
        )
        stu = _student_from_csv_row(row)
        if has_student_hint and not stu:
            errors.append(
                f"Row {row_num}: student not found (set student_db_id or school_student_id / student_id)"
            )
            continue

        try:
            ok, action = _upsert_device_from_csv_row(
                device_type, asset_name, device_name, cord_number, operating_system, stu, row_num
            )
            if not ok:
                errors.append(action)
                db.session.rollback()
                continue
            db.session.commit()
            if action == "created":
                created += 1
            else:
                updated += 1
        except IntegrityError:
            db.session.rollback()
            errors.append(f"Row {row_num}: database conflict (duplicate asset or student)")
        except Exception as exc:
            db.session.rollback()
            errors.append(f"Row {row_num}: {exc}")

    if not created and not updated:
        detail = "No rows were imported."
        if errors:
            detail += " " + "; ".join(errors[:5])
        return None, detail, 400

    return {
        "success": True,
        "message": f"Bulk import finished: {created} created, {updated} updated."
        + (f" {len(errors)} row(s) skipped." if errors else ""),
        "created": created,
        "updated": updated,
        "errors": errors[:25],
    }, None, 200


# --- Logs --------------------------------------------------------------------


def build_activity_log_payload(
    *,
    user_id: int | None = None,
    action: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    from services.activity_log import get_user_activity_log

    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            pass
    limit = max(50, min(int(limit or 100), 500))
    logs = get_user_activity_log(
        user_id=user_id,
        action=action or None,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit,
    )
    users = User.query.order_by(User.username).all()
    actions = [a[0] for a in db.session.query(ActivityLog.action).distinct().all() if a[0]]
    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else None,
                "action": log.action,
                "details": log.details,
                "ip_address": log.ip_address,
                "success": bool(log.success),
                "error_message": log.error_message,
                "timestamp": _iso(log.timestamp),
                "timestamp_display": _fmt(log.timestamp),
            }
            for log in logs
        ],
        "users": [{"id": u.id, "username": u.username, "role": u.role} for u in users],
        "actions": sorted(actions),
        "filters": {
            "user_id": user_id,
            "action": action or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
            "limit": limit,
        },
    }


def build_audit_logs_payload(
    *,
    q: str = "",
    method: str = "",
    status: str = "",
    user_id: int | None = None,
    start: str = "",
    end: str = "",
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    query = AdminAuditLog.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                AdminAuditLog.path.ilike(like),
                AdminAuditLog.endpoint.ilike(like),
                AdminAuditLog.user_role.ilike(like),
            )
        )
    if method:
        query = query.filter(AdminAuditLog.method == method.upper())
    if status:
        try:
            query = query.filter(AdminAuditLog.status_code == int(status))
        except ValueError:
            pass
    if user_id:
        query = query.filter(AdminAuditLog.user_id == user_id)
    if start:
        try:
            query = query.filter(AdminAuditLog.created_at >= datetime.strptime(start, "%Y-%m-%d"))
        except ValueError:
            pass
    if end:
        try:
            query = query.filter(
                AdminAuditLog.created_at < datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
            )
        except ValueError:
            pass

    per_page = max(20, min(int(per_page or 50), 200))
    page = max(1, int(page or 1))
    pagination = query.order_by(AdminAuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    user_options = [
        {"id": u.id, "label": f"{u.username} ({u.role})"}
        for u in User.query.order_by(User.username).limit(500).all()
    ]
    return {
        "logs": [
            {
                "id": row.id,
                "created_at": _iso(row.created_at),
                "created_display": _fmt(row.created_at),
                "user_id": row.user_id,
                "user_role": row.user_role,
                "method": row.method,
                "status_code": row.status_code,
                "duration_ms": row.duration_ms,
                "endpoint": row.endpoint,
                "path": row.path,
                "ip_address": row.ip_address,
            }
            for row in pagination.items
        ],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        },
        "user_options": user_options,
        "filters": {
            "q": q or "",
            "method": method or "",
            "status": status or "",
            "user_id": user_id,
            "start": start or "",
            "end": end or "",
            "page": page,
            "per_page": per_page,
        },
    }


def build_error_reports_payload(
    *,
    type_filter: str = "All",
    status_filter: str = "All",
    date_filter: str = "7d",
) -> dict[str, Any]:
    error_logs = (
        ActivityLog.query.filter(ActivityLog.success == False)  # noqa: E712
        .order_by(ActivityLog.timestamp.desc())
        .limit(50)
        .all()
    )
    bug_reports = BugReport.query.order_by(BugReport.created_at.desc()).limit(50).all()

    error_stats = (
        db.session.query(ActivityLog.action, db.func.count(ActivityLog.id))
        .filter(ActivityLog.success == False)  # noqa: E712
        .group_by(ActivityLog.action)
        .all()
    )
    bug_stats = (
        db.session.query(BugReport.status, db.func.count(BugReport.id))
        .group_by(BugReport.status)
        .all()
    )

    if type_filter == "Errors":
        bug_reports = []
    elif type_filter == "Bugs":
        error_logs = []
    if status_filter != "All":
        bug_reports = [r for r in bug_reports if r.status == status_filter]

    cutoff = None
    if date_filter == "24h":
        cutoff = datetime.now() - timedelta(hours=24)
    elif date_filter == "7d":
        cutoff = datetime.now() - timedelta(days=7)
    elif date_filter == "30d":
        cutoff = datetime.now() - timedelta(days=30)
    if cutoff:
        error_logs = [log for log in error_logs if log.timestamp and log.timestamp >= cutoff]
        bug_reports = [r for r in bug_reports if r.created_at and r.created_at >= cutoff]

    entries = []
    for log in error_logs:
        entries.append(
            {
                "type": "error",
                "timestamp": _iso(log.timestamp),
                "timestamp_display": _fmt(log.timestamp),
                "action": log.action,
                "error_message": log.error_message,
                "username": log.user.username if log.user else None,
                "details": log.details,
            }
        )
    for report in bug_reports:
        entries.append(
            {
                "type": "bug",
                "timestamp": _iso(report.created_at),
                "timestamp_display": _fmt(report.created_at),
                "id": report.id,
                "title": report.title,
                "status": report.status,
                "severity": report.severity,
                "description": report.description,
                "username": report.reporter.username if getattr(report, "reporter", None) else None,
            }
        )
    entries.sort(key=lambda e: e.get("timestamp") or "", reverse=True)

    return {
        "entries": entries,
        "error_stats": [{"action": a, "count": c} for a, c in error_stats],
        "bug_stats": [{"status": s, "count": c} for s, c in bug_stats],
        "filters": {
            "type_filter": type_filter,
            "status_filter": status_filter,
            "date_filter": date_filter,
        },
    }


# --- System ------------------------------------------------------------------


def build_system_payload() -> dict[str, Any]:
    import flask
    import psutil

    now = datetime.now()
    from utils.maintenance_mode import get_active_maintenance

    maintenance = get_active_maintenance()
    maint_on = maintenance is not None

    try:
        cpu_percent = psutil.cpu_percent(interval=0.2)
        memory = psutil.virtual_memory()
        try:
            disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
            disk_percent = disk.percent
            disk_used_gb = round(disk.used / (1024**3), 2)
            disk_total_gb = round(disk.total / (1024**3), 2)
        except Exception:
            disk_percent = disk_used_gb = disk_total_gb = None
        try:
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
        except Exception:
            network_bytes_sent = network_bytes_recv = None
        try:
            uptime = str(now - datetime.fromtimestamp(psutil.boot_time()))
        except Exception:
            uptime = None
        status = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk_percent,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "network_bytes_sent": network_bytes_sent,
            "network_bytes_recv": network_bytes_recv,
            "uptime": uptime,
            "total_users": User.query.count(),
            "total_students": Student.query.count(),
            "total_teachers": TeacherStaff.query.count(),
            "recent_activities": ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(days=1)
            ).count(),
            "recent_errors": ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(days=1),
                ActivityLog.success == False,  # noqa: E712
            ).count(),
            "open_bugs": BugReport.query.filter(BugReport.status == "open").count(),
            "total_bugs": BugReport.query.count(),
            "is_maintenance_mode": maint_on,
            "now": _iso(now),
        }
    except Exception as exc:
        status = {
            "error": str(exc),
            "total_users": User.query.count(),
            "total_students": Student.query.count(),
            "total_teachers": TeacherStaff.query.count(),
            "open_bugs": BugReport.query.filter(BugReport.status == "open").count(),
            "total_bugs": BugReport.query.count(),
            "is_maintenance_mode": maint_on,
            "now": _iso(now),
        }

    config = {
        "debug_mode": SystemConfig.get_value("debug_mode", "Development Server"),
        "database_path": SystemConfig.get_value("database_path", "instance/app.db"),
        "max_upload_size": SystemConfig.get_value("max_upload_size", "16 MB"),
        "session_timeout": SystemConfig.get_value("session_timeout", "24 hours"),
        "backup_location": SystemConfig.get_value("backup_location", "backups/"),
        "log_level": SystemConfig.get_value("log_level", "INFO"),
    }
    site_theme_override = SystemConfig.get_value("site_theme_override") or ""

    from utils.school_timezone import (
        DEFAULT_SCHOOL_TIMEZONE,
        SYSTEM_CONFIG_KEY,
        get_school_timezone_name,
        is_valid_iana_tz,
    )

    db_school_tz = (SystemConfig.get_value(SYSTEM_CONFIG_KEY, "") or "").strip()
    env_school_tz = (current_app.config.get("SCHOOL_TIMEZONE") or "").strip() or DEFAULT_SCHOOL_TIMEZONE
    effective_school_tz = get_school_timezone_name()
    try:
        from zoneinfo import ZoneInfo

        school_tz_now = datetime.now(ZoneInfo(effective_school_tz)).strftime("%Y-%m-%d %I:%M %p %Z")
    except Exception:
        school_tz_now = "—"
    if db_school_tz and is_valid_iana_tz(db_school_tz):
        school_tz_source = "Tech database override (applies to everyone)"
    elif db_school_tz:
        school_tz_source = "Invalid override stored; using server default"
    else:
        school_tz_source = "Server configuration (SCHOOL_TIMEZONE in .env / hosting)"

    return {
        "status": status,
        "config": config,
        "system_info": {
            "python_version": sys.version.split()[0],
            "flask_version": flask.__version__,
            "database": "SQLite",
            "server": "Development" if config["debug_mode"] == "Development Server" else "Production",
        },
        "site_theme_override": site_theme_override,
        "school_timezone": {
            "effective": effective_school_tz,
            "env": env_school_tz,
            "db_raw": db_school_tz,
            "source_label": school_tz_source,
            "now_sample": school_tz_now,
        },
        "maintenance": _maintenance_payload(maintenance),
        "theme_choices": [
            "default",
            "light",
            "dark",
            "snowy",
            "autumn",
            "spring",
            "summer",
            "ocean",
            "forest",
            "holiday",
            "sunset",
            "midnight",
            "desert",
            "lavender",
            "rose",
            "cherry",
            "aurora",
            "storm",
            "wine",
            "mint",
        ],
    }


def run_database_backup() -> tuple[dict[str, Any] | None, str | None, int]:
    from services.activity_log import log_activity

    try:
        db_path = os.path.join(os.getcwd(), "instance", "app.db")
        if not os.path.exists(db_path):
            return None, "Database file not found. Cannot create backup.", 404
        backup_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"app_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        shutil.copy2(db_path, backup_path)
        log_activity(
            user_id=current_user.id,
            action="database_backup",
            details={"backup_file": backup_filename, "backup_size": os.path.getsize(backup_path)},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        return {
            "success": True,
            "message": f"Database backup created successfully: {backup_filename}",
            "backup_file": backup_filename,
        }, None, 200
    except Exception as exc:
        return None, f"Error creating database backup: {exc}", 500


def run_database_integrity() -> tuple[dict[str, Any] | None, str | None, int]:
    from services.activity_log import log_activity

    try:
        result = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
        existing = {row[0] for row in result.fetchall()}
        tables_to_check = [
            "user",
            "student",
            "teacher_staff",
            "school_year",
            "class",
            "assignment",
            "submission",
            "grade",
            "report_card",
            "announcement",
            "notification",
            "maintenance_mode",
            "activity_log",
            "bug_report",
            "attendance",
            "system_config",
        ]
        tables = [t for t in tables_to_check if t in existing]
        results = {}
        errors_found = 0
        for table in tables:
            try:
                count = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}")).scalar()
                results[table] = {"status": "OK", "count": count}
            except Exception as exc:
                results[table] = {"status": "ERROR", "error": str(exc)}
                errors_found += 1
        log_activity(
            user_id=current_user.id,
            action="database_integrity_check",
            details={"tables_checked": len(tables), "errors_found": errors_found, "results": results},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        msg = (
            f"Database integrity check completed successfully. {len(tables)} tables checked."
            if errors_found == 0
            else f"Integrity check completed with {errors_found} errors."
        )
        return {"success": True, "message": msg, "errors_found": errors_found, "results": results}, None, 200
    except Exception as exc:
        return None, f"Error checking database integrity: {exc}", 500


def clear_app_cache() -> tuple[dict[str, Any] | None, str | None, int]:
    try:
        cache_dirs = ["__pycache__", "instance/cache"]
        cleared = 0
        for rel in cache_dirs:
            path = os.path.join(os.getcwd(), rel)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                cleared += 1
        return {"success": True, "message": f"Cache cleared ({cleared} locations)."}, None, 200
    except Exception as exc:
        return None, f"Error clearing cache: {exc}", 500


def start_maintenance_mode(body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    try:
        duration_minutes = int(body.get("duration_minutes") or 60)
        reason = (body.get("reason") or "Scheduled maintenance").strip()
        maintenance_message = (
            body.get("maintenance_message")
            or "System is under maintenance. Please check back later."
        ).strip()
        max_duration = 7 * 24 * 60
        if duration_minutes > max_duration:
            return None, f"Maximum maintenance duration is 7 days ({max_duration} minutes).", 400
        MaintenanceMode.query.update({"is_active": False})
        db.session.commit()
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=duration_minutes)
        maintenance = MaintenanceMode(
            is_active=True,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            reason=reason,
            initiated_by=current_user.id,
            maintenance_message=maintenance_message,
            allow_tech_access=True,
        )
        db.session.add(maintenance)
        db.session.commit()
        return {
            "success": True,
            "message": f"Maintenance mode activated until {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC.",
            "maintenance": _maintenance_payload(maintenance),
        }, None, 200
    except Exception as exc:
        db.session.rollback()
        return None, f"Error starting maintenance mode: {exc}", 500


def stop_maintenance_mode() -> tuple[dict[str, Any] | None, str | None, int]:
    try:
        MaintenanceMode.query.update({"is_active": False})
        db.session.commit()
        return {"success": True, "message": "Maintenance mode deactivated successfully."}, None, 200
    except Exception as exc:
        db.session.rollback()
        return None, f"Error stopping maintenance mode: {exc}", 500


def update_system_config(body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    keys = [
        "debug_mode",
        "database_path",
        "max_upload_size",
        "session_timeout",
        "backup_location",
        "log_level",
    ]
    try:
        for key in keys:
            if key in body and body[key] is not None:
                SystemConfig.set_value(key, str(body[key]).strip())
        return {"success": True, "message": "System configuration updated successfully."}, None, 200
    except Exception as exc:
        return None, f"Error updating configuration: {exc}", 500


def set_school_timezone_spa(body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    from utils.school_timezone import SYSTEM_CONFIG_KEY, is_valid_iana_tz

    action = (body.get("action") or "set").strip().lower()
    try:
        if action == "clear":
            SystemConfig.set_value(SYSTEM_CONFIG_KEY, "")
            return {"success": True, "message": "School timezone override cleared."}, None, 200
        tz = (body.get("school_timezone") or "").strip()
        if not tz or not is_valid_iana_tz(tz):
            return None, "Provide a valid IANA timezone (e.g. America/New_York).", 400
        SystemConfig.set_value(SYSTEM_CONFIG_KEY, tz)
        return {"success": True, "message": f"School timezone set to {tz}."}, None, 200
    except Exception as exc:
        return None, f"Error updating timezone: {exc}", 500


def set_site_theme_spa(body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, int]:
    theme = (body.get("theme") or "").strip().lower()
    choices = {
        "default",
        "light",
        "dark",
        "snowy",
        "autumn",
        "spring",
        "summer",
        "ocean",
        "forest",
        "holiday",
        "sunset",
        "midnight",
        "desert",
        "lavender",
        "rose",
        "cherry",
        "aurora",
        "storm",
        "wine",
        "mint",
        "",
    }
    if theme not in choices:
        return None, "Invalid theme choice.", 400
    try:
        SystemConfig.set_value("site_theme_override", theme)
        msg = "Site theme override cleared." if not theme else f"Site theme override set to {theme}."
        return {"success": True, "message": msg}, None, 200
    except Exception as exc:
        return None, f"Error updating site theme: {exc}", 500


# --- Users -------------------------------------------------------------------


def build_user_management_payload() -> dict[str, Any]:
    return build_tech_user_management_lists()


def build_user_detail_payload(user_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    user = User.query.options(
        joinedload(User.student_profile),
        joinedload(User.teacher_staff_profile),
    ).get(user_id)
    if not user:
        return None, "User not found", 404
    profile = None
    if user.student_profile:
        sp = user.student_profile
        profile = {
            "kind": "student",
            "first_name": sp.first_name,
            "last_name": sp.last_name,
            "student_id": sp.student_id,
            "grade_level": sp.grade_level,
            "email": sp.email,
            "is_active": sp.is_active,
        }
    elif user.teacher_staff_profile:
        tp = user.teacher_staff_profile
        profile = {
            "kind": "staff",
            "first_name": tp.first_name,
            "last_name": tp.last_name,
            "staff_id": getattr(tp, "staff_id", None),
            "position": tp.position,
            "email": tp.email,
            "is_active": tp.is_active,
        }
    from utils.tech_user_management import serialize_tech_mgmt_user_row

    return {
        "user": serialize_tech_mgmt_user_row(user),
        "profile": profile,
        "can_impersonate": user.id != current_user.id,
    }, None, 200


def reset_user_password_spa(user_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    import secrets
    import string

    from werkzeug.security import generate_password_hash

    user = User.query.get(user_id)
    if not user:
        return None, "User not found", 404
    alphabet = string.ascii_letters + string.digits
    temp = "".join(secrets.choice(alphabet) for _ in range(12))
    user.password_hash = generate_password_hash(temp)
    user.is_temporary_password = True
    user.password_changed_at = None
    db.session.commit()
    return {
        "success": True,
        "message": f"Temporary password set for {user.username}.",
        "temporary_password": temp,
    }, None, 200


def impersonate_user_spa(user_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    from services.activity_log import log_activity

    target = User.query.get(user_id)
    if not target:
        return None, "User not found", 404
    if target.id == current_user.id:
        return None, "You cannot impersonate yourself.", 400
    log_activity(
        user_id=current_user.id,
        action="impersonate_user",
        details={
            "target_user_id": target.id,
            "target_username": target.username,
            "target_role": target.role,
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )
    session["original_user_id"] = current_user.id
    session["original_username"] = current_user.username
    session["impersonating_user_id"] = target.id
    session["impersonating_username"] = target.username
    login_user(target)
    return {
        "success": True,
        "message": f"Now impersonating {target.username} ({target.role})",
        "redirect": "/app",
    }, None, 200
