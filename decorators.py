from functools import wraps
from flask import abort
from flask_login import current_user

TEACHER_ROLES = [
    'History Teacher',
    'Science Teacher',
    'Physics Teacher',
    'English Language Arts Teacher',
    'Math Teacher',
    'Substitute Teacher',
    'School Counselor'
]

def is_teacher_role(role):
    """Check if a role is considered a teacher role"""
    if not role:
        return False
    return role in TEACHER_ROLES or 'Teacher' in role or role == 'Director' or role == 'School Administrator'

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
        if current_user.role not in ['School Administrator', 'Director']:
            abort(403)  # Forbidden - wrong role
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    """Restricts access to users with teacher roles (including School Administrator and Director)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized - not logged in
        if not is_teacher_role(current_user.role):
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
