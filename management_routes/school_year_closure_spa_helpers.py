"""SPA helpers for school-year closure workflow."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from flask import current_app

from models import Class, SchoolYear, SchoolYearClosure, SchoolYearClosureExtension, TeacherStaff, User, db
from services import school_year_closure as syc

from management_routes.school_year_closure import _build_next_year_suggestion


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _date_str(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _datetime_str(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _serialize_extension(ext: SchoolYearClosureExtension) -> dict[str, Any]:
    target_label = "Unknown scope"
    if ext.scope_user:
        target_label = ext.scope_user.username
    elif ext.scope_class:
        target_label = ext.scope_class.name
    return {
        "id": ext.id,
        "for_role": ext.for_role,
        "extended_until": _date_str(ext.extended_until),
        "reason": ext.reason or "",
        "target_label": target_label,
        "scope_user_id": ext.scope_user_id,
        "scope_class_id": ext.scope_class_id,
        "granted_by": ext.granted_by.username if ext.granted_by else None,
    }


def _serialize_event(ev) -> dict[str, Any]:
    return {
        "id": ev.id,
        "event_type": ev.event_type,
        "created_at": _datetime_str(ev.created_at),
        "actor": ev.actor.username if ev.actor else None,
        "actor_label": ev.actor_label,
    }


def query_closure_schedule_form() -> dict[str, Any]:
    today = date.today()
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    active = SchoolYear.query.filter_by(is_active=True).first()
    suggested_date = active.end_date if active and active.end_date else today
    active_closures = {
        c.school_year_id: {
            "id": c.id,
            "phase": c.phase,
            "phase_label": syc.PHASE_LABELS.get(c.phase, c.phase),
            "school_year_name": c.school_year.name if c.school_year else None,
        }
        for c in SchoolYearClosure.query.filter(
            SchoolYearClosure.phase.notin_(syc.TERMINAL_PHASES)
        ).all()
    }
    return {
        "today": _date_str(today),
        "suggested_date": _date_str(suggested_date),
        "suggested_year_id": active.id if active else None,
        "school_years": [
            {
                "id": sy.id,
                "name": sy.name,
                "is_active": sy.is_active,
                "start_date": _date_str(sy.start_date),
                "end_date": _date_str(sy.end_date),
                "has_active_closure": sy.id in active_closures,
            }
            for sy in school_years
        ],
        "active_closures": active_closures,
        "phase_labels": syc.PHASE_LABELS,
    }


def create_closure_from_body(body: dict[str, Any], actor: User) -> dict[str, Any]:
    school_year_id = body.get("school_year_id")
    if isinstance(school_year_id, str) and school_year_id.isdigit():
        school_year_id = int(school_year_id)
    closure_date = _parse_date(body.get("closure_date"))
    notes = (body.get("notes") or "").strip() or None
    confirm = (body.get("confirm") or "").strip()
    today = date.today()

    if not school_year_id:
        raise ValueError("Select a school year.")
    if not closure_date:
        raise ValueError("Provide a valid closure date (YYYY-MM-DD).")
    if closure_date < today - timedelta(days=365):
        raise ValueError("Closure date is too far in the past.")
    if confirm != "SCHEDULE CLOSURE":
        raise ValueError("You must type SCHEDULE CLOSURE exactly to confirm.")

    sy = SchoolYear.query.get(school_year_id)
    if not sy:
        raise ValueError("School year not found.")

    closure = syc.create_closure(
        school_year=sy,
        closure_date=closure_date,
        actor=actor,
        notes=notes,
    )
    syc.advance_closure_if_due(closure, actor_label="manual_create")

    message = (
        f"School-year closure scheduled for {sy.name}. Day 0 = "
        f"{closure_date.strftime('%b %d, %Y')}."
    )
    if closure_date < today:
        message = (
            f"School-year closure scheduled for {sy.name}. "
            f"Day 0 was {closure_date.strftime('%b %d, %Y')} — milestones run from today. "
            f"Student lockout: {closure.student_lockout_at.strftime('%b %d, %Y')}."
        )

    return {
        "success": True,
        "message": message,
        "closure_id": closure.id,
        "redirect_url": f"/app/management/school-year/closure/{closure.id}",
    }


def query_closure_dashboard(closure_id: int) -> dict[str, Any]:
    closure = SchoolYearClosure.query.get(closure_id)
    if not closure:
        raise ValueError("Closure not found.")

    if closure.phase not in syc.TERMINAL_PHASES and closure.phase != syc.PHASE_PAUSED:
        try:
            syc.advance_closure_if_due(closure, actor_label="dashboard_view")
        except Exception:
            current_app.logger.exception("Dashboard tick for closure %s failed", closure_id)

    today = date.today()
    days_to = {
        "student_lockout": (closure.student_lockout_at - today).days,
        "teacher_lockout": (closure.teacher_lockout_at - today).days,
        "finalize": (closure.finalize_at - today).days,
    }

    checklist = None
    if closure.phase in (syc.PHASE_TEACHER_WINDOW, syc.PHASE_ADMIN_WINDOW):
        try:
            checklist = syc.build_prefinalize_checklist(closure)
        except Exception:
            current_app.logger.exception("Pre-finalize checklist build failed")

    finalize_stats = None
    if closure.finalize_stats:
        try:
            finalize_stats = json.loads(closure.finalize_stats)
        except Exception:
            finalize_stats = None

    next_year_suggestion = None
    next_year_exists = False
    if closure.phase == syc.PHASE_FINALIZED:
        suggestion = _build_next_year_suggestion(closure)
        if suggestion:
            next_year_suggestion = {
                "name": suggestion["name"],
                "start_date": _date_str(suggestion["start_date"]),
                "end_date": _date_str(suggestion["end_date"]),
                "prior_year_name": suggestion["prior_year_name"],
                "prior_year_start": _date_str(suggestion.get("prior_year_start")),
                "prior_year_end": _date_str(suggestion.get("prior_year_end")),
            }
            next_year_exists = (
                SchoolYear.query.filter_by(name=suggestion["name"]).first() is not None
            )

    teachers = (
        TeacherStaff.query.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()
    )
    classes_in_year = (
        Class.query.filter_by(school_year_id=closure.school_year_id)
        .order_by(Class.name)
        .all()
    )

    extensions = syc.list_active_extensions(closure)
    events = sorted(closure.events, key=lambda e: e.created_at, reverse=True)[:30]

    sy = closure.school_year
    return {
        "closure": {
            "id": closure.id,
            "phase": closure.phase,
            "phase_label": syc.PHASE_LABELS.get(closure.phase, closure.phase),
            "closure_date": _date_str(closure.closure_date),
            "student_lockout_at": _date_str(closure.student_lockout_at),
            "teacher_lockout_at": _date_str(closure.teacher_lockout_at),
            "finalize_at": _date_str(closure.finalize_at),
            "finalized_at": _datetime_str(closure.finalized_at),
            "notes": closure.notes,
            "created_by": closure.created_by.username if closure.created_by else None,
            "paused_by": closure.paused_by.username if closure.paused_by else None,
            "paused_at": _datetime_str(closure.paused_at),
            "cancelled_by": closure.cancelled_by.username if closure.cancelled_by else None,
            "cancelled_at": _datetime_str(closure.cancelled_at),
            "cancellation_reason": closure.cancellation_reason,
        },
        "school_year": {
            "id": sy.id if sy else None,
            "name": sy.name if sy else None,
        },
        "today": _date_str(today),
        "days_to": days_to,
        "extensions": [_serialize_extension(e) for e in extensions],
        "events": [_serialize_event(e) for e in events],
        "checklist": checklist,
        "finalize_stats": finalize_stats,
        "next_year_suggestion": next_year_suggestion,
        "next_year_exists": next_year_exists,
        "phase_labels": syc.PHASE_LABELS,
        "terminal_phases": list(syc.TERMINAL_PHASES),
        "teachers": [
            {
                "id": t.id,
                "name": f"{t.first_name} {t.last_name}".strip(),
                "user_id": t.user.id if t.user else None,
                "username": t.user.username if t.user else None,
            }
            for t in teachers
            if t.user
        ],
        "classes": [
            {"id": c.id, "name": c.name, "subject": getattr(c, "subject", None) or ""}
            for c in classes_in_year
        ],
    }


def run_closure_action(closure_id: int, action: str, body: dict[str, Any], actor: User) -> dict[str, Any]:
    closure = SchoolYearClosure.query.get(closure_id)
    if not closure:
        raise ValueError("Closure not found.")

    reason = (body.get("reason") or "").strip() or None

    if action == "pause":
        syc.pause_closure(closure, actor=actor, reason=reason)
        return {"success": True, "message": "Closure paused."}
    if action == "resume":
        syc.resume_closure(closure, actor=actor)
        return {"success": True, "message": "Closure resumed."}
    if action == "reset-milestones":
        syc.reset_milestones_from_today(closure, actor=actor, reason=reason)
        return {
            "success": True,
            "message": (
                f"Milestones restarted. Student lockout: "
                f"{closure.student_lockout_at.strftime('%b %d, %Y')}."
            ),
        }
    if action == "postpone":
        days = int(body.get("days") or 0)
        if days <= 0 or days > 90:
            raise ValueError("Postpone days must be between 1 and 90.")
        syc.postpone_closure(closure, actor=actor, days=days, reason=reason)
        return {
            "success": True,
            "message": f"Closure postponed by {days} day(s).",
        }
    if action == "cancel":
        if (body.get("confirm") or "").strip() != "CANCEL":
            raise ValueError("You must type CANCEL to confirm.")
        syc.cancel_closure(closure, actor=actor, reason=reason)
        return {"success": True, "message": "Closure cancelled."}
    if action == "advance":
        target = (body.get("target_phase") or "").strip()
        syc.advance_closure_phase(closure, actor=actor, target_phase=target)
        label = syc.PHASE_LABELS.get(target, target)
        return {"success": True, "message": f"Closure advanced to '{label}'."}
    if action == "finalize-now":
        if (body.get("confirm") or "").strip() != "FINALIZE NOW":
            raise ValueError("You must type FINALIZE NOW exactly to confirm.")
        stats = syc.finalize_closure(closure, triggered_by="manual", actor=actor)
        return {
            "success": True,
            "message": (
                f"School year finalized. Report cards saved: {stats.get('report_cards_ok', 0)}; "
                f"errors: {stats.get('report_cards_errors', 0)}."
            ),
        }
    if action == "reopen":
        if (body.get("confirm") or "").strip() != "REOPEN":
            raise ValueError("You must type REOPEN to confirm.")
        syc.reopen_closure(closure, actor=actor, reason=reason)
        return {"success": True, "message": "Closure reopened."}

    raise ValueError(f"Unknown action: {action}")


def grant_closure_extension(closure_id: int, body: dict[str, Any], actor: User) -> dict[str, Any]:
    closure = SchoolYearClosure.query.get(closure_id)
    if not closure:
        raise ValueError("Closure not found.")

    scope = (body.get("scope") or "").strip()
    for_role = (body.get("for_role") or "both").strip()
    extended_until = _parse_date(body.get("extended_until"))
    reason = (body.get("reason") or "").strip() or None
    scope_user_id = body.get("target_user_id") or body.get("scope_user_id")
    scope_class_id = body.get("target_class_id") or body.get("scope_class_id")

    if scope == "user":
        if not scope_user_id:
            raise ValueError("Pick a teacher or student to extend.")
        scope_user_id = int(scope_user_id)
        scope_class_id = None
    elif scope == "class":
        if not scope_class_id:
            raise ValueError("Pick a class to extend.")
        scope_class_id = int(scope_class_id)
        scope_user_id = None
    else:
        raise ValueError("Invalid extension scope.")

    if not extended_until:
        raise ValueError("Provide a valid extended-until date.")

    syc.grant_extension(
        closure,
        actor=actor,
        extended_until=extended_until,
        for_role=for_role,
        scope_user_id=scope_user_id,
        scope_class_id=scope_class_id,
        reason=reason,
    )
    return {
        "success": True,
        "message": f"Extension granted until {extended_until.strftime('%b %d, %Y')}.",
    }


def revoke_closure_extension(closure_id: int, extension_id: int, body: dict[str, Any], actor: User) -> dict[str, Any]:
    closure = SchoolYearClosure.query.get(closure_id)
    if not closure:
        raise ValueError("Closure not found.")
    ext = SchoolYearClosureExtension.query.get(extension_id)
    if not ext or ext.closure_id != closure.id:
        raise ValueError("Extension not found.")
    reason = (body.get("reason") or "").strip() or None
    syc.revoke_extension(ext, actor=actor, reason=reason)
    return {"success": True, "message": "Extension revoked."}


def create_next_school_year(body: dict[str, Any]) -> dict[str, Any]:
    """Create and optionally activate the next school year (post-finalize)."""
    from management_routes.utils import add_academic_periods_for_year

    name = (body.get("name") or "").strip()
    start_date_str = (body.get("start_date") or "").strip()
    end_date_str = (body.get("end_date") or "").strip()
    is_active = bool(body.get("is_active", True))
    auto_generate_quarters = bool(body.get("auto_generate_quarters", True))

    if not all([name, start_date_str, end_date_str]):
        raise ValueError("All fields are required to create a school year.")

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    if is_active:
        SchoolYear.query.update({SchoolYear.is_active: False})

    new_year = SchoolYear(
        name=name,
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )
    db.session.add(new_year)
    db.session.flush()

    message = f'School year "{name}" created successfully.'
    if auto_generate_quarters:
        try:
            add_academic_periods_for_year(new_year.id)
            message += " Academic periods and calendar dates generated."
        except Exception as exc:
            message += f" Warning: could not generate periods: {exc}"

    db.session.commit()
    return {"success": True, "message": message, "school_year_id": new_year.id}
