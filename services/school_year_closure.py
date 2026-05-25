"""
School-year closure workflow engine.

Implements the phased Day 0 → Day 7 → Day 21 → Day 28 close-of-year flow:

  Day 0  (closure_date)
    student_window starts; students notified (in-app + no-reply email) that they
    have one week to submit work and contact teachers.

  Day 7  (student_lockout_at)
    student_window ends, teacher_window begins. Students lose write access; their
    current-year classes move to a "Previous years" section (still visible read-only).
    A reminder is sent to teachers that they have two more weeks to finalize grades.

  Day 21 (teacher_lockout_at)
    teacher_window ends, admin_window begins. Teachers lose write access. A
    pre-finalization warning is sent to Directors / School Administrators with a
    link to the closure dashboard and the unfinished-work checklist.

  Day 28 (finalize_at)
    admin_window ends; the system auto-runs finalize_closure(): bulk Q1–Q4 report
    cards, classes/enrollments/assignments archived, students promoted one grade
    (unless `is_repeating`), school year deactivated. Report cards are tagged
    `is_auto_generated=True`.

Failsafes the engine supports (see routes for the UI):
  - pause / resume          — freeze transitions without changing dates
  - postpone(days)          — push every milestone forward by N days
  - cancel(reason)          — abort the workflow
  - advance(phase)          — force a transition early
  - finalize_now()          — run finalize ahead of schedule
  - grant_extension(...)    — per-user or per-class extra time; honored by the
                              student_can_access_year / teacher_can_edit_year gates
  - revoke_extension(...)
  - reopen()                — undo finalization (rare; for grade-book corrections)

Every state change writes a SchoolYearClosureEvent row for the audit trail.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from flask import current_app, has_request_context, url_for
from sqlalchemy import or_, and_

from extensions import db
from models import (
    Class,
    Enrollment,
    ReportCard,
    SchoolYear,
    SchoolYearClosure,
    SchoolYearClosureEvent,
    SchoolYearClosureExtension,
    Student,
    TeacherStaff,
    User,
)


# ---------------------------------------------------------------------------
# Phase constants
# ---------------------------------------------------------------------------
PHASE_SCHEDULED = 'scheduled'
PHASE_STUDENT_WINDOW = 'student_window'
PHASE_TEACHER_WINDOW = 'teacher_window'
PHASE_ADMIN_WINDOW = 'admin_window'
PHASE_FINALIZED = 'finalized'
PHASE_PAUSED = 'paused'
PHASE_CANCELLED = 'cancelled'

ACTIVE_PHASES = (
    PHASE_SCHEDULED, PHASE_STUDENT_WINDOW, PHASE_TEACHER_WINDOW, PHASE_ADMIN_WINDOW,
)
TERMINAL_PHASES = (PHASE_FINALIZED, PHASE_CANCELLED)

PHASE_LABELS = {
    PHASE_SCHEDULED: 'Scheduled',
    PHASE_STUDENT_WINDOW: 'Student window',
    PHASE_TEACHER_WINDOW: 'Teacher window',
    PHASE_ADMIN_WINDOW: 'Admin window',
    PHASE_FINALIZED: 'Finalized',
    PHASE_PAUSED: 'Paused',
    PHASE_CANCELLED: 'Cancelled',
}

# Access status returned by gating helpers
ACCESS_FULL = 'full'        # write + read
ACCESS_READONLY = 'readonly'  # read only; year is locked or finalized
ACCESS_HIDDEN = 'hidden'    # do not list this year in the active classes UI

# Default milestone offsets from closure_date (Day 0)
STUDENT_LOCKOUT_DAYS = 7
TEACHER_LOCKOUT_DAYS = 21
FINALIZE_DAYS = 28


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _log_event(closure: SchoolYearClosure, event_type: str, *,
               actor: Optional[User] = None, actor_label: Optional[str] = None,
               payload: Optional[dict] = None) -> SchoolYearClosureEvent:
    """Append an audit row. Does not commit."""
    ev = SchoolYearClosureEvent()
    ev.closure_id = closure.id
    ev.event_type = event_type
    ev.actor_user_id = actor.id if actor else None
    ev.actor_label = actor_label or ('user' if actor else 'system')
    ev.payload = json.dumps(payload) if payload else None
    db.session.add(ev)
    return ev


def _today() -> date:
    return date.today()


def _now() -> datetime:
    return datetime.utcnow()


def _compute_milestones(closure_date: date, *,
                        creation_today: Optional[date] = None) -> tuple[date, date, date]:
    """
    (student_lockout, teacher_lockout, finalize) given a Day-0 date.

    The milestone clock starts from ``max(closure_date, today)`` — so if the
    director schedules a closure with a date that already passed (e.g. the
    historical Q4 end date was three weeks ago), the 1-week / 3-week / 4-week
    countdowns still run from "now" instead of having already expired.

    ``closure_date`` itself is preserved as the semantic "year ended on" marker.
    """
    effective_start = max(closure_date, creation_today or _today())
    return (
        effective_start + timedelta(days=STUDENT_LOCKOUT_DAYS),
        effective_start + timedelta(days=TEACHER_LOCKOUT_DAYS),
        effective_start + timedelta(days=FINALIZE_DAYS),
    )


def _safe_url(endpoint: str, **kwargs) -> Optional[str]:
    """Best-effort url_for inside or outside a request context."""
    try:
        return url_for(endpoint, _external=has_request_context(), **kwargs)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public queries
# ---------------------------------------------------------------------------
def get_active_closure_for_year(school_year_id: int) -> Optional[SchoolYearClosure]:
    """Returns the non-terminal closure for this school year, if any."""
    return (
        SchoolYearClosure.query
        .filter(SchoolYearClosure.school_year_id == school_year_id)
        .filter(SchoolYearClosure.phase.notin_(TERMINAL_PHASES))
        .order_by(SchoolYearClosure.created_at.desc())
        .first()
    )


def get_latest_closure_for_year(school_year_id: int) -> Optional[SchoolYearClosure]:
    """Returns the most-recent closure (any phase, including finalized)."""
    return (
        SchoolYearClosure.query
        .filter(SchoolYearClosure.school_year_id == school_year_id)
        .order_by(SchoolYearClosure.created_at.desc())
        .first()
    )


def list_all_closures() -> list[SchoolYearClosure]:
    return SchoolYearClosure.query.order_by(SchoolYearClosure.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Lifecycle: create / pause / resume / postpone / cancel / advance / finalize
# ---------------------------------------------------------------------------
def create_closure(*, school_year: SchoolYear, closure_date: date,
                   actor: Optional[User], notes: Optional[str] = None) -> SchoolYearClosure:
    """Schedule a new closure for `school_year` starting on `closure_date`."""
    # Reject duplicates: only one active closure per year at a time.
    existing = get_active_closure_for_year(school_year.id)
    if existing:
        raise ValueError(
            f"School year '{school_year.name}' already has an active closure "
            f"(phase={existing.phase}); cancel or finalize it first."
        )

    today = _today()
    student_lockout, teacher_lockout, finalize_at = _compute_milestones(
        closure_date, creation_today=today
    )
    snapped_from_past = closure_date < today

    closure = SchoolYearClosure()
    closure.school_year_id = school_year.id
    closure.closure_date = closure_date
    closure.student_lockout_at = student_lockout
    closure.teacher_lockout_at = teacher_lockout
    closure.finalize_at = finalize_at
    closure.phase = PHASE_SCHEDULED
    closure.created_by_user_id = actor.id if actor else None
    closure.notes = notes
    db.session.add(closure)
    db.session.flush()

    _log_event(closure, 'created', actor=actor, payload={
        'school_year_id': school_year.id,
        'school_year_name': school_year.name,
        'closure_date': closure_date.isoformat(),
        'student_lockout_at': student_lockout.isoformat(),
        'teacher_lockout_at': teacher_lockout.isoformat(),
        'finalize_at': finalize_at.isoformat(),
        'milestone_clock_started_today': snapped_from_past,
    })
    db.session.commit()
    current_app.logger.info(
        "Scheduled school-year closure id=%s for year=%s (Day0=%s)",
        closure.id, school_year.name, closure_date,
    )
    return closure


def pause_closure(closure: SchoolYearClosure, *, actor: User,
                  reason: Optional[str] = None) -> SchoolYearClosure:
    if closure.phase in TERMINAL_PHASES:
        raise ValueError(f"Cannot pause a {closure.phase} closure.")
    if closure.phase == PHASE_PAUSED:
        return closure
    closure.previous_phase = closure.phase
    closure.phase = PHASE_PAUSED
    closure.paused_at = _now()
    closure.paused_by_user_id = actor.id if actor else None
    _log_event(closure, 'paused', actor=actor, payload={'reason': reason})
    db.session.commit()
    return closure


def resume_closure(closure: SchoolYearClosure, *, actor: User) -> SchoolYearClosure:
    if closure.phase != PHASE_PAUSED:
        raise ValueError(f"Closure is not paused (current phase={closure.phase}).")
    closure.phase = closure.previous_phase or PHASE_SCHEDULED
    closure.previous_phase = None
    closure.paused_at = None
    closure.paused_by_user_id = None
    _log_event(closure, 'resumed', actor=actor, payload={'restored_phase': closure.phase})
    db.session.commit()
    # Immediately try to advance in case we missed milestones during the pause.
    advance_closure_if_due(closure, actor_label='resume')
    return closure


def reset_milestones_from_today(closure: SchoolYearClosure, *, actor: User,
                                reason: Optional[str] = None) -> SchoolYearClosure:
    """
    Recompute student/teacher/finalize milestone dates so they run from TODAY,
    regardless of the historical closure_date. Useful when:
      - The director picked a closure_date in the past and the engine has
        already advanced past lockouts that they didn't intend yet.
      - A pause/resume + postpone combo doesn't quite get the dates right.

    Also rewinds phase to ``student_window`` if we've already advanced past it,
    so the workflow effectively restarts the 1-week / 3-week / 4-week clock.
    """
    if closure.phase in TERMINAL_PHASES:
        raise ValueError(f"Cannot reset milestones on a {closure.phase} closure.")
    today = _today()
    student_lockout, teacher_lockout, finalize_at = _compute_milestones(
        today, creation_today=today
    )
    old_phase = closure.phase
    closure.student_lockout_at = student_lockout
    closure.teacher_lockout_at = teacher_lockout
    closure.finalize_at = finalize_at
    # If we already advanced past the student window, rewind so students get
    # their week back. We also clear the lockout stamps so the gating helpers
    # see "students are not locked again" until the new student_lockout_at hits.
    if closure.phase in (PHASE_TEACHER_WINDOW, PHASE_ADMIN_WINDOW):
        closure.phase = PHASE_STUDENT_WINDOW
        closure.students_locked_at = None
        closure.teachers_locked_at = None
        # Note: notifications won't re-fire — the engine treats their _sent_at
        # stamps as idempotency markers. That's intentional.

    _log_event(closure, 'milestones_reset', actor=actor, payload={
        'reason': reason,
        'old_phase': old_phase,
        'new_phase': closure.phase,
        'new_student_lockout_at': student_lockout.isoformat(),
        'new_teacher_lockout_at': teacher_lockout.isoformat(),
        'new_finalize_at': finalize_at.isoformat(),
    })
    db.session.commit()
    return closure


def postpone_closure(closure: SchoolYearClosure, *, actor: User, days: int,
                     reason: Optional[str] = None) -> SchoolYearClosure:
    if closure.phase in TERMINAL_PHASES:
        raise ValueError(f"Cannot postpone a {closure.phase} closure.")
    if days == 0:
        return closure
    delta = timedelta(days=days)
    closure.closure_date = closure.closure_date + delta
    closure.student_lockout_at = closure.student_lockout_at + delta
    closure.teacher_lockout_at = closure.teacher_lockout_at + delta
    closure.finalize_at = closure.finalize_at + delta
    _log_event(closure, 'postponed', actor=actor, payload={
        'days': days,
        'reason': reason,
        'new_closure_date': closure.closure_date.isoformat(),
        'new_finalize_at': closure.finalize_at.isoformat(),
    })
    db.session.commit()
    return closure


def cancel_closure(closure: SchoolYearClosure, *, actor: User,
                   reason: Optional[str] = None) -> SchoolYearClosure:
    if closure.phase in TERMINAL_PHASES:
        raise ValueError(f"Closure is already {closure.phase}.")
    closure.phase = PHASE_CANCELLED
    closure.cancelled_at = _now()
    closure.cancelled_by_user_id = actor.id if actor else None
    closure.cancellation_reason = reason
    _log_event(closure, 'cancelled', actor=actor, payload={'reason': reason})
    db.session.commit()
    current_app.logger.info("Cancelled school-year closure id=%s", closure.id)
    return closure


def advance_closure_phase(closure: SchoolYearClosure, *, actor: User,
                          target_phase: str) -> SchoolYearClosure:
    """Manually force a phase transition (admin override)."""
    if closure.phase in TERMINAL_PHASES:
        raise ValueError(f"Cannot advance a {closure.phase} closure.")
    valid_targets = (PHASE_STUDENT_WINDOW, PHASE_TEACHER_WINDOW, PHASE_ADMIN_WINDOW)
    if target_phase not in valid_targets:
        raise ValueError(f"Invalid target phase '{target_phase}'.")
    old = closure.phase
    _enter_phase(closure, target_phase, actor=actor, actor_label='manual_advance')
    db.session.commit()
    current_app.logger.info(
        "Manually advanced closure id=%s from %s to %s by user %s",
        closure.id, old, target_phase, getattr(actor, 'id', None),
    )
    return closure


def reopen_closure(closure: SchoolYearClosure, *, actor: User,
                   reason: Optional[str] = None) -> SchoolYearClosure:
    """Undo finalization. The year stays archived in the DB but you regain ability to
    schedule a fresh closure / regenerate cards. Used only for late grade corrections."""
    if closure.phase != PHASE_FINALIZED:
        raise ValueError(f"Only finalized closures can be reopened (current={closure.phase}).")
    closure.phase = PHASE_ADMIN_WINDOW
    closure.finalized_at = None
    _log_event(closure, 'reopened', actor=actor, payload={'reason': reason})
    # Re-activate the school year so manual edits are possible again.
    sy = SchoolYear.query.get(closure.school_year_id)
    if sy:
        sy.is_active = True
    db.session.commit()
    return closure


# ---------------------------------------------------------------------------
# Extension grants
# ---------------------------------------------------------------------------
def grant_extension(closure: SchoolYearClosure, *, actor: User,
                    extended_until: date, for_role: str = 'both',
                    scope_user_id: Optional[int] = None,
                    scope_class_id: Optional[int] = None,
                    reason: Optional[str] = None) -> SchoolYearClosureExtension:
    """Grant a per-user or per-class extension."""
    if for_role not in ('student', 'teacher', 'both'):
        raise ValueError("for_role must be 'student', 'teacher', or 'both'.")
    if not (scope_user_id or scope_class_id):
        raise ValueError("Must specify at least scope_user_id or scope_class_id.")
    if extended_until <= _today():
        raise ValueError("Extended-until date must be in the future.")

    ext = SchoolYearClosureExtension()
    ext.closure_id = closure.id
    ext.scope_user_id = scope_user_id
    ext.scope_class_id = scope_class_id
    ext.for_role = for_role
    ext.extended_until = extended_until
    ext.reason = reason
    ext.granted_by_user_id = actor.id if actor else None
    db.session.add(ext)
    db.session.flush()

    _log_event(closure, 'extension_granted', actor=actor, payload={
        'extension_id': ext.id,
        'scope_user_id': scope_user_id,
        'scope_class_id': scope_class_id,
        'for_role': for_role,
        'extended_until': extended_until.isoformat(),
        'reason': reason,
    })
    db.session.commit()
    return ext


def revoke_extension(extension: SchoolYearClosureExtension, *, actor: User,
                     reason: Optional[str] = None) -> SchoolYearClosureExtension:
    if extension.revoked_at:
        return extension
    extension.revoked_at = _now()
    extension.revoked_by_user_id = actor.id if actor else None
    extension.revoked_reason = reason
    _log_event(extension.closure, 'extension_revoked', actor=actor, payload={
        'extension_id': extension.id,
        'reason': reason,
    })
    db.session.commit()
    return extension


def list_active_extensions(closure: SchoolYearClosure) -> list[SchoolYearClosureExtension]:
    return [e for e in closure.extensions if e.revoked_at is None]


# ---------------------------------------------------------------------------
# Phase transition engine (idempotent — safe to call every day)
# ---------------------------------------------------------------------------
def _enter_phase(closure: SchoolYearClosure, new_phase: str, *,
                 actor: Optional[User] = None,
                 actor_label: str = 'system') -> None:
    """Atomically transition into a phase and fire side effects (notifications,
    lockout stamps). Caller must commit. Idempotent against repeated calls with
    the same target phase."""
    if closure.phase == new_phase:
        return
    old = closure.phase
    closure.phase = new_phase
    closure.last_tick_at = _now()
    _log_event(closure, 'phase_advanced', actor=actor, actor_label=actor_label, payload={
        'from': old, 'to': new_phase,
    })

    if new_phase == PHASE_STUDENT_WINDOW:
        _send_student_notice(closure, actor_label=actor_label)
    elif new_phase == PHASE_TEACHER_WINDOW:
        closure.students_locked_at = _now()
        _send_teacher_notice(closure, actor_label=actor_label)
    elif new_phase == PHASE_ADMIN_WINDOW:
        closure.teachers_locked_at = _now()
        _send_admin_pre_finalize_warning(closure, actor_label=actor_label)


def advance_closure_if_due(closure: SchoolYearClosure, *,
                           today: Optional[date] = None,
                           actor_label: str = 'system') -> Optional[str]:
    """
    Check today's date against milestone dates and transition the closure forward
    if it's overdue. Idempotent: re-running the same day is a no-op once each
    transition has been recorded.

    Returns the new phase if a transition happened, else None.
    Skips paused / cancelled / finalized closures.
    """
    if closure.phase in TERMINAL_PHASES or closure.phase == PHASE_PAUSED:
        return None

    t = today or _today()
    transitioned = None

    # scheduled → student_window once we hit Day 0
    if closure.phase == PHASE_SCHEDULED and t >= closure.closure_date:
        _enter_phase(closure, PHASE_STUDENT_WINDOW, actor_label=actor_label)
        transitioned = PHASE_STUDENT_WINDOW

    # student_window → teacher_window at Day 7
    if closure.phase == PHASE_STUDENT_WINDOW and t >= closure.student_lockout_at:
        _enter_phase(closure, PHASE_TEACHER_WINDOW, actor_label=actor_label)
        transitioned = PHASE_TEACHER_WINDOW

    # teacher_window → admin_window at Day 21
    if closure.phase == PHASE_TEACHER_WINDOW and t >= closure.teacher_lockout_at:
        _enter_phase(closure, PHASE_ADMIN_WINDOW, actor_label=actor_label)
        transitioned = PHASE_ADMIN_WINDOW

    # admin_window → finalized at Day 28 (auto-finalize)
    if closure.phase == PHASE_ADMIN_WINDOW and t >= closure.finalize_at:
        try:
            finalize_closure(closure, triggered_by='auto', actor=None)
            transitioned = PHASE_FINALIZED
        except Exception:
            current_app.logger.exception(
                "Auto-finalize failed for closure id=%s; will retry on next tick.", closure.id
            )

    closure.last_tick_at = _now()
    db.session.commit()
    return transitioned


def run_closure_tick(today: Optional[date] = None, actor_label: str = 'cron') -> dict:
    """Iterate every non-terminal closure and advance each. Safe to call hourly/daily."""
    stats = {'checked': 0, 'transitioned': 0, 'finalized': 0, 'errors': 0, 'details': []}
    closures = (
        SchoolYearClosure.query
        .filter(SchoolYearClosure.phase.notin_(TERMINAL_PHASES))
        .all()
    )
    stats['checked'] = len(closures)
    for closure in closures:
        try:
            new_phase = advance_closure_if_due(closure, today=today, actor_label=actor_label)
            if new_phase:
                stats['transitioned'] += 1
                if new_phase == PHASE_FINALIZED:
                    stats['finalized'] += 1
                stats['details'].append({'closure_id': closure.id, 'new_phase': new_phase})
        except Exception as exc:
            stats['errors'] += 1
            current_app.logger.exception(
                "run_closure_tick failed for closure id=%s: %s", closure.id, exc
            )
    return stats


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
def _send_student_notice(closure: SchoolYearClosure, *, actor_label: str = 'system') -> None:
    """Day 0: tell every student enrolled in this year that they have 1 week left."""
    from services.notifications import create_notifications_for_users

    sy = SchoolYear.query.get(closure.school_year_id)
    if not sy:
        return

    # All students with an active enrollment in this year's classes.
    user_ids = [
        row[0] for row in (
            db.session.query(User.id)
            .join(Student, Student.id == User.student_id)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .join(Class, Class.id == Enrollment.class_id)
            .filter(Class.school_year_id == sy.id)
            .filter(Enrollment.is_active.is_(True))
            .filter(Student.is_deleted.is_(False))
            .distinct()
            .all()
        )
    ]
    if not user_ids:
        return

    end_label = closure.student_lockout_at.strftime('%A, %B %d, %Y')
    link = _safe_url('student.student_assignments') or _safe_url('auth.login')
    title = f"School year {sy.name} ends {closure.closure_date.strftime('%B %d')} — 1 week to wrap up"
    message = (
        f"Hi! The {sy.name} school year ended on {closure.closure_date.strftime('%B %d, %Y')}. "
        f"You have one week — until {end_label} — to turn in any outstanding work, ask "
        f"your teachers questions, or request grade fixes. After that, your current-year "
        f"classes move to read-only and you won't be able to submit new work. "
        f"Your grades stay in your portal under the Grades tab."
    )
    try:
        create_notifications_for_users(user_ids, 'school_year_close', title, message, link)
        closure.student_notice_sent_at = _now()
        _log_event(closure, 'notification_sent', actor_label=actor_label, payload={
            'audience': 'students', 'count': len(user_ids),
        })
    except Exception as exc:
        current_app.logger.exception("Failed to send student notice for closure %s: %s", closure.id, exc)
        _log_event(closure, 'notification_failed', actor_label=actor_label, payload={
            'audience': 'students', 'error': str(exc),
        })


def _send_teacher_notice(closure: SchoolYearClosure, *, actor_label: str = 'system') -> None:
    """Day 7: tell every teacher of a class in this year that they have 2 weeks left."""
    from services.notifications import create_notifications_for_users

    sy = SchoolYear.query.get(closure.school_year_id)
    if not sy:
        return

    user_ids = [
        row[0] for row in (
            db.session.query(User.id)
            .join(TeacherStaff, TeacherStaff.id == User.teacher_staff_id)
            .join(Class, Class.teacher_id == TeacherStaff.id)
            .filter(Class.school_year_id == sy.id)
            .distinct()
            .all()
        )
    ]
    if not user_ids:
        return

    end_label = closure.teacher_lockout_at.strftime('%A, %B %d, %Y')
    link = _safe_url('teacher.dashboard.my_classes') or _safe_url('auth.login')
    title = f"Finalize {sy.name} grades by {closure.teacher_lockout_at.strftime('%b %d')}"
    message = (
        f"Heads up: students for {sy.name} are now in read-only mode. You have until "
        f"{end_label} (two more weeks) to finalize grades, enter report-card comments, "
        f"and resolve any disputes. After that, the gradebook for this year locks and "
        f"only the Director / School Administrator can make changes. If you need more "
        f"time, ask the Director to grant you a personal extension."
    )
    try:
        create_notifications_for_users(user_ids, 'school_year_close', title, message, link)
        closure.teacher_notice_sent_at = _now()
        _log_event(closure, 'notification_sent', actor_label=actor_label, payload={
            'audience': 'teachers', 'count': len(user_ids),
        })
    except Exception as exc:
        current_app.logger.exception("Failed to send teacher notice for closure %s: %s", closure.id, exc)
        _log_event(closure, 'notification_failed', actor_label=actor_label, payload={
            'audience': 'teachers', 'error': str(exc),
        })


def _send_admin_pre_finalize_warning(closure: SchoolYearClosure, *,
                                     actor_label: str = 'system') -> None:
    """Day 21: warn Directors / Admins that auto-finalize runs in 1 week."""
    from services.notifications import create_notifications_for_users
    from utils.user_roles import canonical_role_label

    user_ids = [
        u.id for u in User.query.all()
        if canonical_role_label(getattr(u, 'role', None)) in ('Director', 'School Administrator')
    ]
    if not user_ids:
        return

    sy = SchoolYear.query.get(closure.school_year_id)
    finalize_label = closure.finalize_at.strftime('%A, %B %d, %Y')
    link = _safe_url('management.school_year_closure_dashboard', closure_id=closure.id)
    title = f"Year-end finalize runs {closure.finalize_at.strftime('%b %d')} ({sy.name if sy else ''})"
    message = (
        f"The teacher window has ended for {sy.name if sy else 'the active closure'}. "
        f"You have one week (until {finalize_label}) to review report cards, grant any "
        f"last-minute extensions, and resolve unfinished gradebook items. On "
        f"{finalize_label} the system will automatically generate final report cards, "
        f"archive the year, and promote students. Open the closure dashboard to see the "
        f"pre-finalization checklist and override the timing if needed."
    )
    try:
        create_notifications_for_users(user_ids, 'school_year_close', title, message, link)
        closure.admin_warning_sent_at = _now()
        _log_event(closure, 'notification_sent', actor_label=actor_label, payload={
            'audience': 'admins', 'count': len(user_ids),
        })
    except Exception as exc:
        current_app.logger.exception(
            "Failed to send admin pre-finalize warning for closure %s: %s", closure.id, exc
        )
        _log_event(closure, 'notification_failed', actor_label=actor_label, payload={
            'audience': 'admins', 'error': str(exc),
        })


# ---------------------------------------------------------------------------
# Lockout gating helpers (called by student & teacher routes)
# ---------------------------------------------------------------------------
def get_student_access_status(student_user, school_year) -> str:
    """
    Returns one of:
      ACCESS_FULL     — student can still submit / view normally
      ACCESS_READONLY — class is visible but no writes allowed
      ACCESS_HIDDEN   — class should not appear in the active "My Classes" list

    Used by templates AND by submission endpoints. Always honors extensions.
    """
    if not school_year:
        return ACCESS_FULL

    closure = get_latest_closure_for_year(school_year.id)
    if not closure:
        # No closure scheduled and year is active → full access; year is inactive → readonly history.
        return ACCESS_FULL if school_year.is_active else ACCESS_READONLY

    if closure.phase in (PHASE_SCHEDULED, PHASE_STUDENT_WINDOW, PHASE_PAUSED):
        # Day 0..Day 7 (or paused mid-flight) — full write access.
        return ACCESS_FULL

    if closure.phase == PHASE_CANCELLED:
        return ACCESS_FULL if school_year.is_active else ACCESS_READONLY

    # Student lockout is in effect (teacher_window / admin_window / finalized).
    # Check for an extension that pushes this student's deadline forward.
    if student_user and _student_has_unexpired_extension(student_user.id, closure):
        return ACCESS_FULL

    if closure.phase == PHASE_FINALIZED:
        return ACCESS_HIDDEN if not school_year.is_active else ACCESS_READONLY
    # teacher_window, admin_window → hybrid: hide from active list, but show under "Previous years".
    return ACCESS_HIDDEN


def get_teacher_access_status(teacher_user, school_year) -> str:
    """Same semantics as student helper but for teachers and the teacher lockout."""
    if not school_year:
        return ACCESS_FULL

    closure = get_latest_closure_for_year(school_year.id)
    if not closure:
        return ACCESS_FULL if school_year.is_active else ACCESS_READONLY

    if closure.phase in (PHASE_SCHEDULED, PHASE_STUDENT_WINDOW, PHASE_TEACHER_WINDOW, PHASE_PAUSED):
        return ACCESS_FULL

    if closure.phase == PHASE_CANCELLED:
        return ACCESS_FULL if school_year.is_active else ACCESS_READONLY

    if teacher_user and _teacher_has_unexpired_extension(teacher_user.id, closure):
        return ACCESS_FULL

    if closure.phase == PHASE_FINALIZED:
        return ACCESS_READONLY
    # admin_window → teachers locked
    return ACCESS_READONLY


def can_student_submit(student_user, school_year) -> bool:
    return get_student_access_status(student_user, school_year) == ACCESS_FULL


def can_teacher_edit_grades(teacher_user, school_year) -> bool:
    return get_teacher_access_status(teacher_user, school_year) == ACCESS_FULL


def class_is_locked_for_writes(class_, *, for_role: str, user_id: Optional[int] = None) -> bool:
    """
    Returns True if writes to this class are currently blocked for the given
    role ('student' or 'teacher'). Used by individual save endpoints where we
    have a class id but need to look up the school year.

    Honors BOTH per-class extensions AND per-user extensions when ``user_id``
    is supplied. (Per-user extensions are how Directors grant a specific
    student or teacher more time without unlocking the whole class.)
    """
    if not class_:
        return False
    sy = SchoolYear.query.get(class_.school_year_id)
    if not sy:
        return False
    closure = get_latest_closure_for_year(sy.id)
    if not closure:
        return False

    # Per-class extension?
    if _class_has_unexpired_extension(class_.id, closure, for_role=for_role):
        return False

    # Per-user extension? (only relevant when caller passed a user_id)
    if user_id is not None:
        if for_role == 'student' and _student_has_unexpired_extension(user_id, closure):
            return False
        if for_role == 'teacher' and _teacher_has_unexpired_extension(user_id, closure):
            return False

    if for_role == 'student':
        return closure.phase in (PHASE_TEACHER_WINDOW, PHASE_ADMIN_WINDOW, PHASE_FINALIZED)
    if for_role == 'teacher':
        return closure.phase in (PHASE_ADMIN_WINDOW, PHASE_FINALIZED)
    return False


def _student_has_unexpired_extension(user_id: int, closure: SchoolYearClosure) -> bool:
    today = _today()
    # Per-user extension
    for e in closure.extensions:
        if e.revoked_at is not None:
            continue
        if e.scope_user_id == user_id and e.for_role in ('student', 'both') and e.extended_until >= today:
            return True
    # Per-class extension: does the student have an active enrollment in any extended class?
    extended_class_ids = [
        e.scope_class_id for e in closure.extensions
        if e.revoked_at is None and e.scope_class_id and e.for_role in ('student', 'both')
        and e.extended_until >= today
    ]
    if not extended_class_ids:
        return False
    user = User.query.get(user_id)
    if not user or not user.student_id:
        return False
    enrolled = (
        Enrollment.query
        .filter(Enrollment.student_id == user.student_id)
        .filter(Enrollment.class_id.in_(extended_class_ids))
        .first()
    )
    return enrolled is not None


def _teacher_has_unexpired_extension(user_id: int, closure: SchoolYearClosure) -> bool:
    today = _today()
    for e in closure.extensions:
        if e.revoked_at is not None:
            continue
        if e.scope_user_id == user_id and e.for_role in ('teacher', 'both') and e.extended_until >= today:
            return True
    extended_class_ids = [
        e.scope_class_id for e in closure.extensions
        if e.revoked_at is None and e.scope_class_id and e.for_role in ('teacher', 'both')
        and e.extended_until >= today
    ]
    if not extended_class_ids:
        return False
    user = User.query.get(user_id)
    if not user or not user.teacher_staff_id:
        return False
    teaches = (
        Class.query
        .filter(Class.id.in_(extended_class_ids))
        .filter(Class.teacher_id == user.teacher_staff_id)
        .first()
    )
    return teaches is not None


def _class_has_unexpired_extension(class_id: int, closure: SchoolYearClosure, *,
                                   for_role: str) -> bool:
    today = _today()
    for e in closure.extensions:
        if e.revoked_at is not None:
            continue
        if e.scope_class_id == class_id and e.extended_until >= today:
            if e.for_role == 'both' or e.for_role == for_role:
                return True
    return False


# ---------------------------------------------------------------------------
# Finalize (the actual year-end archival job — refactored from the old route)
# ---------------------------------------------------------------------------
def finalize_closure(closure: SchoolYearClosure, *, triggered_by: str = 'manual',
                     actor: Optional[User] = None) -> dict:
    """
    Run the irreversible finalize step:
      - Generate official Q1–Q4 report cards (marked is_auto_generated=True) for
        every student who had an active enrollment in this year's classes.
      - Mark every assignment / group assignment in those classes Inactive
        (preserving Voided).
      - Deactivate every enrollment in those classes.
      - Mark every class in the year inactive.
      - Promote enrolled students one grade level (skipping is_repeating and
        12th-grade as before; provisions new 3rd-grade portal logins on demand).
      - Mark the SchoolYear is_active=False.
      - Move closure to PHASE_FINALIZED with stats stored on the closure row.
    """
    if closure.phase in TERMINAL_PHASES:
        raise ValueError(f"Cannot finalize a {closure.phase} closure.")

    # Lazy import to avoid circular dependencies.
    from models import Assignment, GroupAssignment
    from management_routes.reports import (
        persist_report_card_record,
        _apply_grade_promotion_after_year_close,
    )

    sy = SchoolYear.query.get(closure.school_year_id)
    if not sy:
        raise ValueError(f"School year id={closure.school_year_id} not found.")

    actor_id = actor.id if actor else None
    classes_in_year = Class.query.filter_by(school_year_id=sy.id).all()
    class_ids = [c.id for c in classes_in_year]

    students = (
        Student.query.filter(Student.is_deleted.is_(False))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )

    ok_n = skip_n = err_n = 0
    errors_sample: list[str] = []
    enrolled_student_ids: set[int] = set()
    quarters_full = ['Q1', 'Q2', 'Q3', 'Q4']

    for student in students:
        enrs = (
            Enrollment.query.join(Class, Enrollment.class_id == Class.id)
            .filter(
                Class.school_year_id == sy.id,
                Enrollment.student_id == student.id,
                Enrollment.is_active.is_(True),
            )
            .all()
        )
        if not enrs:
            skip_n += 1
            continue
        enrolled_student_ids.add(student.id)
        cid_list = list({e.class_id for e in enrs})
        try:
            res = persist_report_card_record(
                student_id_int=student.id,
                school_year_id_int=sy.id,
                class_ids_int=cid_list,
                quarters_to_include=quarters_full,
                report_type='official',
                include_attendance=True,
                include_comments=True,
                enrollment_must_be_active=True,
                notify_admins=False,
            )
        except Exception as exc:
            err_n += 1
            if len(errors_sample) < 15:
                errors_sample.append(f"{student.first_name} {student.last_name}: {exc}")
            continue
        if res.get('ok'):
            ok_n += 1
            # Tag the just-saved ReportCard rows as auto-generated.
            try:
                _mark_report_cards_auto_generated(
                    student_id=student.id,
                    school_year_id=sy.id,
                    quarters=quarters_full,
                    actor_user_id=actor_id,
                    cutoff=_now(),
                )
            except Exception:
                current_app.logger.exception(
                    "Failed to tag auto-generated report cards for student %s", student.id
                )
        else:
            err_n += 1
            if len(errors_sample) < 15:
                errors_sample.append(f"{student.first_name} {student.last_name}: {res.get('error')}")

    if class_ids:
        Assignment.query.filter(
            Assignment.class_id.in_(class_ids),
            Assignment.status != 'Voided',
        ).update({Assignment.status: 'Inactive'}, synchronize_session=False)
        GroupAssignment.query.filter(
            GroupAssignment.class_id.in_(class_ids),
            GroupAssignment.status != 'Voided',
        ).update({GroupAssignment.status: 'Inactive'}, synchronize_session=False)

        Enrollment.query.filter(Enrollment.class_id.in_(class_ids)).update(
            {Enrollment.is_active: False, Enrollment.dropped_at: _now()},
            synchronize_session=False,
        )
        Class.query.filter(Class.id.in_(class_ids)).update(
            {Class.is_active: False}, synchronize_session=False,
        )

    promo_stats = None
    promo_failed = False
    if enrolled_student_ids:
        try:
            promo_stats = _apply_grade_promotion_after_year_close(enrolled_student_ids)
        except Exception:
            current_app.logger.exception("Grade promotion after closure %s failed", closure.id)
            promo_failed = True

    sy.is_active = False

    closure.phase = PHASE_FINALIZED
    closure.finalized_at = _now()
    closure.last_tick_at = _now()
    stats = {
        'triggered_by': triggered_by,
        'report_cards_ok': ok_n,
        'report_cards_skipped': skip_n,
        'report_cards_errors': err_n,
        'errors_sample': errors_sample,
        'promotion': promo_stats,
        'promotion_failed': promo_failed,
        'classes_archived': len(class_ids),
        'students_processed': len(enrolled_student_ids),
    }
    closure.finalize_stats = json.dumps(stats)

    _log_event(closure, 'finalized', actor=actor, actor_label=triggered_by, payload=stats)
    db.session.commit()
    current_app.logger.info(
        "Finalized school-year closure id=%s (year=%s): %s", closure.id, sy.name, stats
    )
    return stats


def _mark_report_cards_auto_generated(*, student_id: int, school_year_id: int,
                                      quarters: Iterable[str], actor_user_id: Optional[int],
                                      cutoff: datetime) -> None:
    """Set is_auto_generated=True on the just-created report card rows.

    persist_report_card_record stores the quarter label as a combined string
    (e.g. "Q1-Q4" when all four quarters are selected, "Q1" for a single
    quarter). Match against both the combined label AND every individual
    quarter so we catch whichever shape was actually persisted.
    """
    quarters_list = [q for q in quarters if q]
    # Derive the combined label the same way persist_report_card_record did
    from management_routes.reports import _quarter_str_from_selection
    combined = _quarter_str_from_selection(quarters_list)
    label_candidates = set(quarters_list)
    if combined:
        label_candidates.add(combined)
    if not label_candidates:
        return
    (
        ReportCard.query
        .filter(ReportCard.student_id == student_id)
        .filter(ReportCard.school_year_id == school_year_id)
        .filter(ReportCard.quarter.in_(list(label_candidates)))
        .filter(or_(ReportCard.generated_at.is_(None), ReportCard.generated_at <= cutoff))
        .update(
            {
                ReportCard.is_auto_generated: True,
                ReportCard.generated_by_user_id: actor_user_id,
            },
            synchronize_session=False,
        )
    )


# ---------------------------------------------------------------------------
# Pre-finalization checklist (for the dashboard)
# ---------------------------------------------------------------------------
def build_prefinalize_checklist(closure: SchoolYearClosure) -> dict:
    """
    Surface unfinished business that the director should review before Day 28:
      - Classes with students who have no recorded Q4 grade
      - Teachers who have not submitted comments for their classes (best-effort)
      - Students with no active enrollment in this year (will be skipped)
    Best-effort; missing models are tolerated.
    """
    sy = SchoolYear.query.get(closure.school_year_id)
    out = {
        'school_year_id': closure.school_year_id,
        'school_year_name': sy.name if sy else None,
        'classes_without_q4_grades': [],
        'classes_total': 0,
        'students_total': 0,
        'students_without_enrollment': 0,
    }
    if not sy:
        return out

    classes = Class.query.filter_by(school_year_id=sy.id).all()
    out['classes_total'] = len(classes)
    class_ids = [c.id for c in classes]

    try:
        from models import QuarterGrade  # type: ignore
        for c in classes:
            roster = (
                Enrollment.query
                .filter(Enrollment.class_id == c.id, Enrollment.is_active.is_(True))
                .all()
            )
            if not roster:
                continue
            student_ids = [e.student_id for e in roster]
            graded = {
                row[0] for row in (
                    db.session.query(QuarterGrade.student_id)
                    .filter(QuarterGrade.class_id == c.id)
                    .filter(QuarterGrade.school_year_id == sy.id)
                    .filter(QuarterGrade.quarter == 'Q4')
                    .filter(QuarterGrade.student_id.in_(student_ids))
                    .all()
                )
            }
            missing = [sid for sid in student_ids if sid not in graded]
            if missing:
                out['classes_without_q4_grades'].append({
                    'class_id': c.id,
                    'class_name': c.name,
                    'subject': c.subject,
                    'missing_student_count': len(missing),
                    'roster_size': len(student_ids),
                })
    except Exception:
        # QuarterGrade may be unavailable or the schema different — non-fatal.
        current_app.logger.debug("Pre-finalize Q4 check skipped", exc_info=True)

    out['students_total'] = (
        db.session.query(Student.id)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .join(Class, Class.id == Enrollment.class_id)
        .filter(Class.school_year_id == sy.id)
        .filter(Enrollment.is_active.is_(True))
        .filter(Student.is_deleted.is_(False))
        .distinct().count()
    )
    return out
