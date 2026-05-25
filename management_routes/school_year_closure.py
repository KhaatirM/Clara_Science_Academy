"""
Management routes for the phased school-year-closure workflow.

Endpoints (all under /management/school-year/closure):
  GET  /schedule                          schedule form
  POST /schedule                          create a new SchoolYearClosure
  GET  /<id>                              dashboard
  POST /<id>/pause                        freeze transitions
  POST /<id>/resume                       resume after pause
  POST /<id>/postpone                     bump every milestone by N days
  POST /<id>/cancel                       abort the workflow
  POST /<id>/advance                      force a phase transition early
  POST /<id>/finalize-now                 run finalize ahead of schedule
  POST /<id>/reopen                       undo finalization
  POST /<id>/extensions                   grant a new extension
  POST /<id>/extensions/<eid>/revoke      revoke an existing extension
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, abort, current_app
)
from flask_login import current_user, login_required

from decorators import management_required
from extensions import db
from models import (
    Class,
    SchoolYear,
    SchoolYearClosure,
    SchoolYearClosureExtension,
    Student,
    TeacherStaff,
    User,
)
from services import school_year_closure as syc


school_year_closure_bp = Blueprint(
    'school_year_closure',
    __name__,
    url_prefix='/management/school-year/closure',
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _closure_or_404(closure_id: int) -> SchoolYearClosure:
    closure = SchoolYearClosure.query.get(closure_id)
    if not closure:
        abort(404)
    return closure


def _back_to_dashboard(closure_id: int):
    return redirect(url_for('school_year_closure.dashboard', closure_id=closure_id))


# ---------------------------------------------------------------------------
# Schedule a new closure
# ---------------------------------------------------------------------------
@school_year_closure_bp.route('/schedule', methods=['GET', 'POST'])
@login_required
@management_required
def schedule():
    """Pick a school year and a Day-0 date; show timeline preview; create the closure."""
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    today = date.today()

    if request.method == 'GET':
        # Suggest a sensible default date if there's a single active year.
        active = SchoolYear.query.filter_by(is_active=True).first()
        suggested_date = (active.end_date if active and active.end_date else today)
        suggested_year_id = active.id if active else None
        return render_template(
            'management/school_year_closure_schedule.html',
            school_years=school_years,
            today=today,
            suggested_date=suggested_date,
            suggested_year_id=suggested_year_id,
            active_closures={c.school_year_id: c for c in
                             SchoolYearClosure.query
                             .filter(SchoolYearClosure.phase.notin_(syc.TERMINAL_PHASES))
                             .all()},
        )

    school_year_id = request.form.get('school_year_id', type=int)
    closure_date = _parse_date(request.form.get('closure_date'))
    notes = (request.form.get('notes') or '').strip() or None
    confirm = (request.form.get('confirm') or '').strip()

    if not school_year_id:
        flash('Select a school year.', 'danger')
        return redirect(url_for('school_year_closure.schedule'))
    if not closure_date:
        flash('Provide a valid closure date (YYYY-MM-DD).', 'danger')
        return redirect(url_for('school_year_closure.schedule'))
    if closure_date < today - timedelta(days=365):
        flash('Closure date is too far in the past.', 'danger')
        return redirect(url_for('school_year_closure.schedule'))
    if confirm != 'SCHEDULE CLOSURE':
        flash('You must type SCHEDULE CLOSURE exactly to confirm.', 'danger')
        return redirect(url_for('school_year_closure.schedule'))

    sy = SchoolYear.query.get_or_404(school_year_id)
    try:
        closure = syc.create_closure(
            school_year=sy,
            closure_date=closure_date,
            actor=current_user,
            notes=notes,
        )
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('school_year_closure.schedule'))

    # If closure_date was today or in the past, immediately advance phases so the
    # workflow doesn't sit at 'scheduled' until midnight.
    syc.advance_closure_if_due(closure, actor_label='manual_create')

    if closure_date < today:
        flash(
            f"School-year closure scheduled for {sy.name}. "
            f"You picked {closure_date.strftime('%b %d, %Y')} as Day 0 — "
            f"since that's in the past, the 1-week / 3-week / 4-week countdowns "
            f"now run from today. Students lockout: "
            f"{closure.student_lockout_at.strftime('%b %d, %Y')}.",
            'info',
        )
    else:
        flash(
            f"School-year closure scheduled for {sy.name}. Day 0 = "
            f"{closure_date.strftime('%b %d, %Y')}. Students will be notified "
            f"automatically.",
            'success',
        )
    return _back_to_dashboard(closure.id)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@school_year_closure_bp.route('/<int:closure_id>', methods=['GET'])
@login_required
@management_required
def dashboard(closure_id: int):
    closure = _closure_or_404(closure_id)

    # Run the tick once per request — gives directors immediate visibility into
    # state changes without depending on the scheduler.
    if closure.phase not in syc.TERMINAL_PHASES and closure.phase != syc.PHASE_PAUSED:
        try:
            syc.advance_closure_if_due(closure, actor_label='dashboard_view')
        except Exception:
            current_app.logger.exception("Dashboard tick for closure %s failed", closure_id)

    # When a closure has finalized, surface a "Start next school year" affordance
    # with smart defaults derived from the closed year.
    next_year_suggestion = _build_next_year_suggestion(closure) if closure.phase == syc.PHASE_FINALIZED else None
    next_year_exists = False
    if next_year_suggestion:
        next_year_exists = SchoolYear.query.filter_by(name=next_year_suggestion['name']).first() is not None

    today = date.today()
    extensions = syc.list_active_extensions(closure)

    # Days-to-next-phase calculations for the dashboard
    days_to = {
        'student_lockout': (closure.student_lockout_at - today).days,
        'teacher_lockout': (closure.teacher_lockout_at - today).days,
        'finalize': (closure.finalize_at - today).days,
    }

    # Pre-finalize checklist (only meaningful once we're in/past teacher_window)
    checklist = None
    if closure.phase in (syc.PHASE_TEACHER_WINDOW, syc.PHASE_ADMIN_WINDOW):
        try:
            checklist = syc.build_prefinalize_checklist(closure)
        except Exception:
            current_app.logger.exception("Pre-finalize checklist build failed")

    # Latest 30 events for the timeline
    events = sorted(closure.events, key=lambda e: e.created_at, reverse=True)[:30]

    finalize_stats = None
    if closure.finalize_stats:
        try:
            finalize_stats = json.loads(closure.finalize_stats)
        except Exception:
            finalize_stats = None

    teachers = (
        TeacherStaff.query
        .order_by(TeacherStaff.last_name, TeacherStaff.first_name)
        .all()
    )
    classes_in_year = (
        Class.query
        .filter_by(school_year_id=closure.school_year_id)
        .order_by(Class.name)
        .all()
    )
    return render_template(
        'management/school_year_closure_dashboard.html',
        closure=closure,
        school_year=closure.school_year,
        today=today,
        days_to=days_to,
        extensions=extensions,
        events=events,
        checklist=checklist,
        finalize_stats=finalize_stats,
        teachers=teachers,
        classes_in_year=classes_in_year,
        phase_labels=syc.PHASE_LABELS,
        next_year_suggestion=next_year_suggestion,
        next_year_exists=next_year_exists,
    )


def _build_next_year_suggestion(closure: SchoolYearClosure) -> dict:
    """
    Suggest a starter name + dates for the next school year, given the closed one.

    Strategy: preserve the school's calendar by adding exactly one calendar
    year to each of the closed year's start_date and end_date. So a year that
    ran Aug 24 2025 -> June 15 2026 suggests Aug 24 2026 -> June 15 2027.
    The director can override either field in the form. We deliberately
    avoid "day after end_date" — that lands in summer break.

    Name parsing handles ``2025-2026``, ``2025-26``, ``2025/26``, and the
    YYYY-YYYY fallback derived from end_date.
    """
    sy = closure.school_year
    if not sy:
        return None

    name_in = (sy.name or '').strip()
    next_name = None
    # Try to detect a four-digit "YYYY-YYYY" pattern and increment both halves.
    import re
    m = re.match(r'^(\d{4})\s*[-/]\s*(\d{4})$', name_in)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        next_name = f"{a + 1}-{b + 1}"
    if not next_name:
        # "YYYY-YY" pattern (two-digit second half)
        m = re.match(r'^(\d{4})\s*[-/]\s*(\d{2})$', name_in)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            next_name = f"{a + 1}-{(b + 1) % 100:02d}"
    if not next_name and sy.end_date:
        # Fall back: just use end-year and next year
        y = sy.end_date.year
        next_name = f"{y}-{y + 1}"
    if not next_name:
        next_name = "New school year"

    # Date suggestions: bump prior start/end forward exactly one calendar
    # year (preserves the school's typical first/last day pattern).
    from datetime import date as _date

    def _add_one_year(d):
        if not d:
            return None
        try:
            return d.replace(year=d.year + 1)
        except ValueError:
            # Feb 29 in a non-leap year — slide back to Feb 28
            return d.replace(month=2, day=28, year=d.year + 1)

    today = _date.today()
    start = _add_one_year(sy.start_date) if sy.start_date else None
    end = _add_one_year(sy.end_date) if sy.end_date else None

    # If the closed year had no start_date, fall back to mid-August of the
    # year following end_date (or today's year).
    if start is None:
        anchor_year = (sy.end_date.year if sy.end_date else today.year)
        start = _date(anchor_year + 1, 8, 15)
    if end is None:
        # Default term length: ~10 months
        end = _date(start.year + 1, 6, 15)

    return {
        'name': next_name,
        'start_date': start,
        'end_date': end,
        'prior_year_name': sy.name,
        'prior_year_start': sy.start_date,
        'prior_year_end': sy.end_date,
    }


# ---------------------------------------------------------------------------
# Lifecycle actions
# ---------------------------------------------------------------------------
@school_year_closure_bp.route('/<int:closure_id>/pause', methods=['POST'])
@login_required
@management_required
def pause(closure_id: int):
    closure = _closure_or_404(closure_id)
    reason = (request.form.get('reason') or '').strip() or None
    try:
        syc.pause_closure(closure, actor=current_user, reason=reason)
        flash('Closure paused. Transitions and notifications are frozen until resumed.', 'info')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


@school_year_closure_bp.route('/<int:closure_id>/resume', methods=['POST'])
@login_required
@management_required
def resume(closure_id: int):
    closure = _closure_or_404(closure_id)
    try:
        syc.resume_closure(closure, actor=current_user)
        flash('Closure resumed.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


@school_year_closure_bp.route('/<int:closure_id>/reset-milestones', methods=['POST'])
@login_required
@management_required
def reset_milestones(closure_id: int):
    closure = _closure_or_404(closure_id)
    reason = (request.form.get('reason') or '').strip() or None
    try:
        syc.reset_milestones_from_today(closure, actor=current_user, reason=reason)
        flash(
            f"Milestones restarted from today. Students lockout: "
            f"{closure.student_lockout_at.strftime('%b %d, %Y')}; "
            f"teachers lockout: {closure.teacher_lockout_at.strftime('%b %d, %Y')}; "
            f"auto-finalize: {closure.finalize_at.strftime('%b %d, %Y')}.",
            'success',
        )
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


@school_year_closure_bp.route('/<int:closure_id>/postpone', methods=['POST'])
@login_required
@management_required
def postpone(closure_id: int):
    closure = _closure_or_404(closure_id)
    days = request.form.get('days', type=int) or 0
    reason = (request.form.get('reason') or '').strip() or None
    if days <= 0 or days > 90:
        flash('Postpone days must be between 1 and 90.', 'danger')
        return _back_to_dashboard(closure_id)
    try:
        syc.postpone_closure(closure, actor=current_user, days=days, reason=reason)
        flash(
            f'Closure postponed by {days} day(s). New Day-0 is '
            f'{closure.closure_date.strftime("%b %d, %Y")}.',
            'success',
        )
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


@school_year_closure_bp.route('/<int:closure_id>/cancel', methods=['POST'])
@login_required
@management_required
def cancel(closure_id: int):
    closure = _closure_or_404(closure_id)
    reason = (request.form.get('reason') or '').strip() or None
    confirm = (request.form.get('confirm') or '').strip()
    if confirm != 'CANCEL':
        flash('You must type CANCEL to confirm.', 'danger')
        return _back_to_dashboard(closure_id)
    try:
        syc.cancel_closure(closure, actor=current_user, reason=reason)
        flash('Closure cancelled. The school year continues normally.', 'warning')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


@school_year_closure_bp.route('/<int:closure_id>/advance', methods=['POST'])
@login_required
@management_required
def advance(closure_id: int):
    closure = _closure_or_404(closure_id)
    target = (request.form.get('target_phase') or '').strip()
    try:
        syc.advance_closure_phase(closure, actor=current_user, target_phase=target)
        flash(f"Closure advanced to '{syc.PHASE_LABELS.get(target, target)}'.", 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


@school_year_closure_bp.route('/<int:closure_id>/finalize-now', methods=['POST'])
@login_required
@management_required
def finalize_now(closure_id: int):
    closure = _closure_or_404(closure_id)
    confirm = (request.form.get('confirm') or '').strip()
    if confirm != 'FINALIZE NOW':
        flash('You must type FINALIZE NOW exactly to confirm.', 'danger')
        return _back_to_dashboard(closure_id)
    try:
        stats = syc.finalize_closure(closure, triggered_by='manual', actor=current_user)
    except Exception as exc:
        current_app.logger.exception("Manual finalize failed for closure %s", closure_id)
        flash(f'Finalize failed: {exc}', 'danger')
        return _back_to_dashboard(closure_id)
    flash(
        f"School year finalized. "
        f"Report cards saved: {stats.get('report_cards_ok', 0)}; "
        f"errors: {stats.get('report_cards_errors', 0)}; "
        f"classes archived: {stats.get('classes_archived', 0)}.",
        'success',
    )
    return _back_to_dashboard(closure_id)


@school_year_closure_bp.route('/<int:closure_id>/reopen', methods=['POST'])
@login_required
@management_required
def reopen(closure_id: int):
    closure = _closure_or_404(closure_id)
    reason = (request.form.get('reason') or '').strip() or None
    confirm = (request.form.get('confirm') or '').strip()
    if confirm != 'REOPEN':
        flash('You must type REOPEN to confirm.', 'danger')
        return _back_to_dashboard(closure_id)
    try:
        syc.reopen_closure(closure, actor=current_user, reason=reason)
        flash('Closure reopened. The school year is active again for corrections.', 'info')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------
@school_year_closure_bp.route('/<int:closure_id>/extensions', methods=['POST'])
@login_required
@management_required
def grant_extension_route(closure_id: int):
    closure = _closure_or_404(closure_id)
    scope = (request.form.get('scope') or '').strip()  # 'user' | 'class'
    for_role = (request.form.get('for_role') or 'both').strip()
    extended_until = _parse_date(request.form.get('extended_until'))
    reason = (request.form.get('reason') or '').strip() or None

    scope_user_id = None
    scope_class_id = None

    if scope == 'user':
        target_id = request.form.get('target_user_id', type=int)
        if not target_id:
            flash('Pick a teacher or student to extend.', 'danger')
            return _back_to_dashboard(closure_id)
        scope_user_id = target_id
    elif scope == 'class':
        target_id = request.form.get('target_class_id', type=int)
        if not target_id:
            flash('Pick a class to extend.', 'danger')
            return _back_to_dashboard(closure_id)
        scope_class_id = target_id
    else:
        flash('Invalid extension scope.', 'danger')
        return _back_to_dashboard(closure_id)

    if not extended_until:
        flash('Provide a valid extended-until date.', 'danger')
        return _back_to_dashboard(closure_id)

    try:
        syc.grant_extension(
            closure,
            actor=current_user,
            extended_until=extended_until,
            for_role=for_role,
            scope_user_id=scope_user_id,
            scope_class_id=scope_class_id,
            reason=reason,
        )
        flash(
            f"Extension granted until {extended_until.strftime('%b %d, %Y')}.",
            'success',
        )
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


@school_year_closure_bp.route(
    '/<int:closure_id>/extensions/<int:extension_id>/revoke', methods=['POST']
)
@login_required
@management_required
def revoke_extension_route(closure_id: int, extension_id: int):
    closure = _closure_or_404(closure_id)
    ext = SchoolYearClosureExtension.query.get(extension_id)
    if not ext or ext.closure_id != closure.id:
        abort(404)
    reason = (request.form.get('reason') or '').strip() or None
    try:
        syc.revoke_extension(ext, actor=current_user, reason=reason)
        flash('Extension revoked.', 'info')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return _back_to_dashboard(closure_id)


# ---------------------------------------------------------------------------
# Legacy redirect: the old instant-close button now points here.
# ---------------------------------------------------------------------------
@school_year_closure_bp.route('/legacy-close-redirect')
@login_required
@management_required
def legacy_close_redirect():
    flash(
        'The instant "Close school year" button has been replaced by the phased '
        'closure workflow. Schedule a closure here instead — students get one week '
        'of advance notice, teachers get three weeks to finalize grades, and the '
        'system auto-archives the year four weeks after the closure date.',
        'info',
    )
    return redirect(url_for('school_year_closure.schedule'))
