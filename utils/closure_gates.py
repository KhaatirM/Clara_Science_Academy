"""
Read/write access enforcement for the phased school-year-closure workflow.

This module exposes two things:

  1. ``register_closure_gates(app)`` — registers a ``before_app_request`` hook
     that blocks known student/teacher write endpoints once the closure has
     advanced past the relevant lockout, honoring any extensions.

  2. Helpers for student-facing views that need to filter classes / grades by
     school year accessibility:
        ``student_year_access(student_user, school_year)``
        ``teacher_year_access(teacher_user, school_year)``

The actual phase logic lives in ``services.school_year_closure``; this file is
the thin glue layer that ties phase state to HTTP requests and templates.
"""
from __future__ import annotations

from typing import Optional

from flask import flash, g, redirect, request, url_for, current_app
from flask_login import current_user


# ---------------------------------------------------------------------------
# Endpoint catalogs
# ---------------------------------------------------------------------------
# Student endpoints that constitute a "write" against a class's gradebook /
# submissions and should be blocked once students are locked out.
# Each entry maps endpoint → name-of-arg holding the assignment / class id
# (or ``None`` to derive from current_user's classes).
STUDENT_WRITE_ENDPOINTS = {
    # endpoint name                              : (kind, arg_name)
    'student.submit_assignment':                  ('assignment', 'assignment_id'),
    'student.submit_group_assignment':            ('group_assignment', 'assignment_id'),
    'student.submit_quiz':                        ('assignment', 'assignment_id'),
    'student.save_quiz_progress':                 ('assignment', 'assignment_id'),
    'student.request_extension':                  ('current_year', None),
    'student.request_redo':                       ('current_year', None),
    'student.create_discussion_thread':           ('assignment', 'assignment_id'),
    'student.reply_to_discussion_thread':         ('current_year', None),
    'student.edit_discussion_thread':             ('current_year', None),
    'student.edit_discussion_post':               ('current_year', None),
}

# Student-assistant endpoints that modify attendance / grades / assignments for a class.
# These should be locked on the same timeline as TEACHER write access (Day 21+).
ASSISTANT_WRITE_ENDPOINTS = {
    # endpoint name                                 : (kind, arg_name)
    'student_assistant.take_attendance':             ('class', 'class_id'),
    'student_assistant.grade_assignment':            ('assignment', 'assignment_id'),
    'student_assistant.grade_group_assignment':      ('group_assignment', 'assignment_id'),
    'student_assistant.assistant_add_assignment':    ('class', 'class_id'),
    'student_assistant.assistant_add_quiz_assignment': ('class', 'class_id'),
    'student_assistant.assistant_add_discussion_assignment': ('class', 'class_id'),
    'student_assistant.assistant_save_group_assignment': ('class', 'class_id'),
}

# Teacher endpoints that should be blocked once teachers are locked out.
# These names are the ACTUAL Flask endpoint names registered in this app
# (verified by inspection of teacher_routes/*.py). Misspelled or removed
# endpoints here would silently leak around the lockout.
TEACHER_WRITE_ENDPOINTS = {
    # Whole-assignment grade entry (POST /teacher/grade/assignment/<id>)
    'teacher.grading.grade_assignment':           ('assignment', 'assignment_id'),
    # Per-student grade save (POST /teacher/grade/assignment/<id>/student/<sid>)
    'teacher.grading.save_student_grade':         ('assignment', 'assignment_id'),
    # Void/unvoid an assignment (POST /teacher/assignment/<id>/void & /unvoid-assignment/<id>)
    'teacher.assignments.void_assignment':                ('assignment', 'assignment_id'),
    'teacher.assignments.unvoid_assignment_for_students': ('assignment', 'assignment_id'),
    # Bulk void multiple assignments at once
    'teacher.assignments.bulk_void_assignments':  ('current_year', None),
    # Reopening / extending / redo-grant are write operations against the class
    'teacher.assignments.reopen_assignment':      ('assignment', 'assignment_id'),
}


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------
def _resolve_school_year_for_request(kind: str, arg_name: Optional[str]):
    """Return the SchoolYear most relevant to this request, or None."""
    from models import (
        Assignment, GroupAssignment, SchoolYear, Class,
    )
    view_args = request.view_args or {}
    if kind == 'assignment' and arg_name and view_args.get(arg_name) is not None:
        a = Assignment.query.get(view_args.get(arg_name))
        if a:
            return SchoolYear.query.get(a.school_year_id)
    if kind == 'group_assignment' and arg_name and view_args.get(arg_name) is not None:
        ga = GroupAssignment.query.get(view_args.get(arg_name))
        if ga:
            return SchoolYear.query.get(ga.school_year_id)
    if kind == 'class' and arg_name and view_args.get(arg_name) is not None:
        c = Class.query.get(view_args.get(arg_name))
        if c:
            return SchoolYear.query.get(c.school_year_id)
    if kind == 'current_year':
        return SchoolYear.query.filter_by(is_active=True).first()
    return None


def _resolve_class_for_request(kind: str, arg_name: Optional[str]):
    """Return the Class most relevant to this request, or None."""
    from models import Assignment, GroupAssignment, Class
    view_args = request.view_args or {}
    if kind == 'assignment' and arg_name and view_args.get(arg_name) is not None:
        a = Assignment.query.get(view_args.get(arg_name))
        return Class.query.get(a.class_id) if a else None
    if kind == 'group_assignment' and arg_name and view_args.get(arg_name) is not None:
        ga = GroupAssignment.query.get(view_args.get(arg_name))
        return Class.query.get(ga.class_id) if ga else None
    if kind == 'class' and arg_name and view_args.get(arg_name) is not None:
        return Class.query.get(view_args.get(arg_name))
    return None


# ---------------------------------------------------------------------------
# Public helpers (called from templates / views)
# ---------------------------------------------------------------------------
def student_year_access(student_user, school_year) -> str:
    """Returns 'full' | 'readonly' | 'hidden'. Safe to call with None values."""
    from services.school_year_closure import get_student_access_status
    return get_student_access_status(student_user, school_year)


def teacher_year_access(teacher_user, school_year) -> str:
    """Returns 'full' | 'readonly'. Safe to call with None values."""
    from services.school_year_closure import get_teacher_access_status
    return get_teacher_access_status(teacher_user, school_year)


def filter_classes_by_student_access(classes, student_user) -> dict:
    """
    Split a list of Class objects into three buckets based on the closure state
    of each one's SchoolYear. Returns:
       {
         'active':    [...],  # show in My Classes
         'readonly':  [...],  # show but disable writes
         'archived':  [...],  # show under "Previous years" only
       }
    """
    from models import SchoolYear
    from services.school_year_closure import (
        get_student_access_status,
        ACCESS_FULL, ACCESS_READONLY, ACCESS_HIDDEN,
    )

    buckets = {'active': [], 'readonly': [], 'archived': []}
    # Bulk-load school years to avoid N+1
    sy_ids = list({getattr(c, 'school_year_id', None) for c in classes if getattr(c, 'school_year_id', None)})
    sy_map = {sy.id: sy for sy in SchoolYear.query.filter(SchoolYear.id.in_(sy_ids)).all()}

    for c in classes:
        sy = sy_map.get(getattr(c, 'school_year_id', None))
        status = get_student_access_status(student_user, sy)
        if status == ACCESS_FULL:
            buckets['active'].append(c)
        elif status == ACCESS_READONLY:
            buckets['readonly'].append(c)
        else:
            buckets['archived'].append(c)
    return buckets


# ---------------------------------------------------------------------------
# Write-gate hook
# ---------------------------------------------------------------------------
def register_closure_gates(app):
    """
    Install a ``before_app_request`` hook that blocks known student/teacher
    write endpoints once the relevant lockout is in effect.

    Idempotent: safe to call multiple times during app init.
    """
    if getattr(app, '_closure_gates_registered', False):
        return
    app._closure_gates_registered = True

    from services.school_year_closure import (
        get_student_access_status, get_teacher_access_status,
        class_is_locked_for_writes, ACCESS_FULL,
    )

    @app.before_request
    def _enforce_closure_lockouts():
        # Only POST / PUT / DELETE / PATCH writes are gated; GETs are filtered
        # by the view-level helpers above (so students still see read-only history).
        if request.method not in ('POST', 'PUT', 'DELETE', 'PATCH'):
            return

        endpoint = request.endpoint or ''

        user = _safe_current_user()
        user_id = getattr(user, 'id', None)

        if endpoint in STUDENT_WRITE_ENDPOINTS:
            kind, arg = STUDENT_WRITE_ENDPOINTS[endpoint]
            try:
                klass = _resolve_class_for_request(kind, arg)
                sy = _resolve_school_year_for_request(kind, arg)
            except Exception:
                current_app.logger.exception("closure_gate resolve failed for %s", endpoint)
                return  # fail-open: don't break the request

            # Always check the user-level access first so per-user extensions
            # short-circuit the more restrictive class-level lock.
            if sy and get_student_access_status(user, sy) == ACCESS_FULL:
                return  # extension lets them through
            if klass and class_is_locked_for_writes(klass, for_role='student',
                                                    user_id=user_id):
                return _student_locked_response(endpoint)
            if sy and get_student_access_status(user, sy) != ACCESS_FULL:
                return _student_locked_response(endpoint)

        elif endpoint in TEACHER_WRITE_ENDPOINTS:
            kind, arg = TEACHER_WRITE_ENDPOINTS[endpoint]
            try:
                klass = _resolve_class_for_request(kind, arg)
                sy = _resolve_school_year_for_request(kind, arg)
            except Exception:
                current_app.logger.exception("closure_gate resolve failed for %s", endpoint)
                return

            if sy and get_teacher_access_status(user, sy) == ACCESS_FULL:
                return  # extension lets them through
            if klass and class_is_locked_for_writes(klass, for_role='teacher',
                                                    user_id=user_id):
                return _teacher_locked_response(endpoint)
            if sy and get_teacher_access_status(user, sy) != ACCESS_FULL:
                return _teacher_locked_response(endpoint)

        elif endpoint in ASSISTANT_WRITE_ENDPOINTS:
            kind, arg = ASSISTANT_WRITE_ENDPOINTS[endpoint]
            try:
                klass = _resolve_class_for_request(kind, arg)
                sy = _resolve_school_year_for_request(kind, arg)
            except Exception:
                current_app.logger.exception("closure_gate resolve failed for %s", endpoint)
                return

            # Student assistants should be locked on the teacher timeline (Day 21+),
            # not the student lockout (Day 7+).
            if klass and class_is_locked_for_writes(klass, for_role='teacher', user_id=None):
                return _assistant_locked_response(endpoint)
            if sy and get_teacher_access_status(user, sy) != ACCESS_FULL:
                return _assistant_locked_response(endpoint)


def _safe_current_user():
    try:
        return current_user._get_current_object()
    except Exception:
        return current_user


def _student_locked_response(endpoint: str):
    flash(
        "This school year is in read-only mode. Submissions and edits are closed for the "
        "year. Contact your teacher or the school administrator if you need an extension.",
        "warning",
    )
    # Best-effort redirect back to the dashboard
    try:
        return redirect(request.referrer or url_for('student.student_dashboard'))
    except Exception:
        return redirect('/')


def _teacher_locked_response(endpoint: str):
    flash(
        "The teacher window for this school year has ended. Contact the Director or School "
        "Administrator to request an extension if you still need to update grades.",
        "warning",
    )
    try:
        return redirect(request.referrer or url_for('teacher.dashboard.my_classes'))
    except Exception:
        return redirect('/')


def _assistant_locked_response(endpoint: str):
    flash(
        "The teacher window for this school year has ended. Student assistant edits are locked. "
        "Contact the Director or School Administrator if you still need to update grades or attendance.",
        "warning",
    )
    try:
        return redirect(request.referrer or url_for('student_assistant.assistant_console'))
    except Exception:
        return redirect('/')
