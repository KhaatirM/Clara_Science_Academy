from functools import wraps
from flask import abort, request
from flask_login import current_user
import json

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
    """Check if a role is considered a teacher role"""
    if not role:
        return False
    return role in TEACHER_ROLES or 'Teacher' in role


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
            if allow_admin and current_user.role in ['School Administrator', 'Director']:
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
        if current_user.role != 'Director':
            abort(403)  # Forbidden - wrong role
        return f(*args, **kwargs)
    return decorated_function

def tech_required(f):
    """Restricts access to users with 'Tech', 'IT Support', or 'Director' roles."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in
        if current_user.role not in ['Tech', 'IT Support', 'Director']:
            abort(403)  # Forbidden - wrong role
        return f(*args, **kwargs)
    return decorated_function

def management_required(f):
    """Restricts access to users with 'School Administrator' or 'Director' roles."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in
        if current_user.role in ['School Administrator', 'Director']:
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
        
        # Get role and normalize it (strip whitespace)
        role = str(current_user.role).strip() if current_user.role else None
        
        # Debug output (will show in console)
        print(f"[DEBUG teacher_required] User: {current_user.username}, Role: '{role}'")
        
        # Check if role is a teacher role or admin role
        is_teacher = is_teacher_role(role)
        is_admin_role = role in ['School Administrator', 'Director']
        
        print(f"[DEBUG teacher_required] is_teacher_role: {is_teacher}, is_admin: {is_admin_role}")
        
        if not (is_teacher or is_admin_role):
            # Debug output
            print(f"[ERROR] Teacher required check FAILED for user {current_user.username}")
            print(f"[ERROR] Role: '{role}' (type: {type(role)})")
            print(f"[ERROR] TEACHER_ROLES list: {TEACHER_ROLES}")
            print(f"[ERROR] 'Teacher' in role: {'Teacher' in str(role) if role else False}")
            abort(403)  # Forbidden - wrong role
        
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """Restricts access to users with the 'Student' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in
        if current_user.role != 'Student':
            abort(403)  # Forbidden - wrong role
        return f(*args, **kwargs)
    return decorated_function
