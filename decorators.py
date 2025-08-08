from functools import wraps
from flask import abort
from flask_login import current_user

TEACHER_ROLES = [
    'History Teacher',
    'Science Teacher',
    'Physics Teacher',
    'English Language Arts Teacher',
    'Math Teacher',
    'Substitute Teacher'
]

def admin_required(f):
    """Restricts access to users with the 'Director' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Director':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def tech_required(f):
    """Restricts access to users with 'Tech', 'IT Support', or 'Director' roles."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['Tech', 'IT Support', 'Director']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def management_required(f):
    """Restricts access to users with 'School Administrator' or 'Director' roles."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['School Administrator', 'Director']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    """Restricts access to users with specific teacher roles, School Administrator, or Director."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (
            current_user.role not in TEACHER_ROLES and
            current_user.role not in ['School Administrator', 'Director']
        ):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """Restricts access to users with the 'Student' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Student':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
