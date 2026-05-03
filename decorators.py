from functools import wraps
from flask import abort, request, flash, redirect, url_for
from flask_login import current_user
import json

from utils.user_roles import (
    user_has_tech_route_access,
    user_has_management_entry_access,
    canonical_role_label,
)

TEACHER_ROLES = [
    'History Teacher',
    'Science Teacher',
    'Physics Teacher',
    'English Language Arts Teacher',
    'Math Teacher',
    'Substitute Teacher',
    'School Counselor',
    # Simplified role labels (new staff creation)
    'Teacher',
    'Substitute',
    'Counselor',
]

def is_teacher_role(role):
    """Check if a role is considered a teacher role (case-insensitive; accepts ``teacher``, subject teachers, etc.)."""
    if not role:
        return False
    r = str(role).strip()
    if r in TEACHER_ROLES:
        return True
    canon = canonical_role_label(r)
    if canon in TEACHER_ROLES:
        return True
    if canon == 'Teacher':
        return True
    rl = r.lower()
    if rl in ('teacher', 'substitute', 'counselor'):
        return True
    if 'teacher' in rl or 'counselor' in rl:
        return True
    return 'Teacher' in r


def get_user_permissions(user):
    """Return a normalized set of permission strings for a user."""
    if not user:
        return set()
    raw = getattr(user, 'permissions', None)
    if not raw:
        return set()
    try:
        if isinstance(raw, (list, tuple, set)):
            perms = list(raw)
        else:
            perms = json.loads(raw)
        if not isinstance(perms, list):
            return set()
        out = set()
        for p in perms:
            if isinstance(p, str) and p.strip():
                out.add(p.strip())
        return out
    except Exception:
        return set()


def has_permission(user, perm):
    """Check if user has a specific permission string."""
    if not user or not perm:
        return False
    return perm in get_user_permissions(user)


def has_any_permission(user, perms):
    """Check if user has any of the provided permissions."""
    if not user:
        return False
    pset = get_user_permissions(user)
    return any(p in pset for p in (perms or []))


def permissions_required(*perms, require_all=False, allow_admin=True):
    """
    Allow access if:
    - user is Director/School Administrator (when allow_admin), OR
    - user has any (or all) required perms.
    """
    perms = [p for p in perms if p]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if allow_admin and user_has_management_entry_access(current_user):
                return f(*args, **kwargs)
            if not perms:
                abort(403)
            if require_all:
                ok = all(has_permission(current_user, p) for p in perms)
            else:
                ok = has_any_permission(current_user, perms)
            if not ok:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Restricts access to users with the 'Director' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in
        if canonical_role_label(current_user.role) != 'Director':
            abort(403)  # Forbidden - wrong role
        return f(*args, **kwargs)
    return decorated_function

def tech_required(f):
    """Restricts access to users with 'Tech', 'IT Support', or 'Director' roles."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in
        if not user_has_tech_route_access(current_user):
            abort(403)  # Forbidden - wrong role
        return f(*args, **kwargs)
    return decorated_function

def management_required(f):
    """Restricts access to users with 'School Administrator' or 'Director' roles."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in
        if user_has_management_entry_access(current_user):
            return f(*args, **kwargs)

        # Permission-based access for non-admin staff in Administration department
        try:
            profile = getattr(current_user, 'teacher_staff_profile', None)
            dept = (getattr(profile, 'department', None) or '').strip() if profile else ''
            if 'Administration' not in (dept or ''):
                abort(403)

            endpoint = (request.endpoint or '').strip()
            # Endpoint-to-permissions allowlist. Keep this narrow to avoid exposing settings/billing/etc.
            endpoint_required_any = {
                # Management home
                'management.management_dashboard': [
                    'students:view', 'students:edit',
                    'teachers_staff:manage',
                    'classes:manage',
                    'assignments_grades:manage',
                    'attendance:manage',
                    'report_cards:view', 'report_cards:generate',
                ],
                # Students
                'management.students': ['students:view', 'students:edit'],
                'management.add_student': ['students:edit'],
                'management.view_student': ['students:view', 'students:edit'],
                'students.students': ['students:view', 'students:edit'],
                'students.add_student': ['students:edit'],
                'students.edit_student': ['students:edit'],
                'students.view_student': ['students:view', 'students:edit'],

                # Teachers & staff (view/manage)
                'management.teachers': ['teachers_staff:manage'],
                'management.edit_teacher_staff': ['teachers_staff:manage'],
                'management.remove_teacher_staff': ['teachers_staff:manage'],
                'management.view_teacher': ['teachers_staff:manage'],
                'teachers.teachers': ['teachers_staff:manage'],
                'teachers.edit_teacher_staff': ['teachers_staff:manage'],
                'teachers.remove_teacher_staff': ['teachers_staff:manage'],
                'teachers.view_teacher': ['teachers_staff:manage'],
                'teachers.edit_teacher': ['teachers_staff:manage'],

                # Classes
                'management.classes': ['classes:manage'],
                'classes.classes': ['classes:manage'],
                'classes.manage_class': ['classes:manage'],
                'classes.edit_class': ['classes:manage'],
                'classes.add_class': ['classes:manage'],

                # Attendance
                'management.unified_attendance': ['attendance:manage'],
                'attendance.unified_attendance': ['attendance:manage'],

                # Assignments & grades
                'management.assignments_and_grades': ['assignments_grades:manage'],
                'assignments.assignments_and_grades': ['assignments_grades:manage'],

                # Report cards
                'management.report_cards': ['report_cards:view', 'report_cards:generate'],
                'reports.report_cards': ['report_cards:view', 'report_cards:generate'],
                'reports.generate_report_card_form': ['report_cards:generate'],
                'reports.view_report_card': ['report_cards:view', 'report_cards:generate'],
                'reports.generate_report_card_pdf': ['report_cards:generate'],
                'reports.delete_report_card': ['report_cards:generate'],

                # Calendar is standard for permission-based Administration staff
                'management.calendar': [
                    'students:view', 'students:edit',
                    'teachers_staff:manage',
                    'classes:manage',
                    'assignments_grades:manage',
                    'attendance:manage',
                    'report_cards:view', 'report_cards:generate',
                ],

                # Communications
                'management.communications': ['communications:manage'],
                'management.management_messages': ['communications:manage'],
                'management.management_send_message': ['communications:manage'],
                'management.management_view_message': ['communications:manage'],
                'management.management_groups': ['communications:manage'],
                'management.management_create_group': ['communications:manage'],
                'management.management_view_group': ['communications:manage'],
                'management.management_create_announcement': ['communications:manage'],
                'management.management_schedule_announcement': ['communications:manage'],

                # Settings is standard for permission-based Administration staff
                'management.settings': [
                    'students:view', 'students:edit',
                    'teachers_staff:manage',
                    'classes:manage',
                    'assignments_grades:manage',
                    'attendance:manage',
                    'report_cards:view', 'report_cards:generate',
                ],

                # Billing & financials
                'management.billing': ['billing:manage'],
            }

            required = endpoint_required_any.get(endpoint)
            if not required:
                abort(403)
            if not has_any_permission(current_user, required):
                abort(403)
        except Exception:
            abort(403)  # Forbidden - wrong role/permission
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    """Restricts access to users with teacher roles, including School Administrators and Directors."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in

        role = str(current_user.role).strip() if current_user.role else None
        is_teacher = is_teacher_role(role)
        is_admin_role = user_has_management_entry_access(current_user)

        if not (is_teacher or is_admin_role):
            abort(403)  # Forbidden - wrong role

        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """Restricts access to users with the 'Student' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in
        if canonical_role_label(current_user.role) != 'Student':
            flash(
                'The student portal is only for student accounts. '
                'Staff should sign in from the main login page and open your staff dashboard.',
                'warning',
            )
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function
