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
    return role in TEACHER_ROLES or 'Teacher' in role

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
