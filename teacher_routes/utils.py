"""
Shared utilities and helper functions for teacher routes.
"""

from flask import current_app
from flask_login import current_user
from models import TeacherStaff, Class, db, class_additional_teachers, class_substitute_teachers
from sqlalchemy import or_
from datetime import datetime

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_teacher_or_admin():
    """Helper function to get teacher object or None for administrators."""
    if current_user.role in ['Director', 'School Administrator']:
        return None
    else:
        if current_user.teacher_staff_id:
            return TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first()
        return None

def teacher_or_management_for_group_assignment(f):
    """Allows Directors, School Administrators, OR teachers authorized for the assignment's class."""
    from functools import wraps
    from flask import abort
    from flask_login import current_user
    from models import GroupAssignment

    @wraps(f)
    def decorated_function(assignment_id, *args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role in ['Director', 'School Administrator']:
            return f(assignment_id, *args, **kwargs)
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        if is_authorized_for_class(group_assignment.class_info):
            return f(assignment_id, *args, **kwargs)
        abort(403)
    return decorated_function


def is_authorized_for_class(class_obj):
    """Check if current user is authorized to access a specific class."""
    # --- DEBUG PRINT: Check your server console when you click a class ---
    user_role = str(current_user.role) if current_user.role else 'None'
    class_id = class_obj.id if class_obj else 'None'
    username = current_user.username if hasattr(current_user, 'username') else 'Unknown'
    
    print(f"[DEBUG AUTH] User: {username}, Role: '{user_role}', Class ID: {class_id}")
    print(f"[DEBUG AUTH] Role type: {type(current_user.role)}, Role repr: {repr(current_user.role)}")
    print(f"[DEBUG AUTH] Checking if role in ['Director', 'School Administrator']: {user_role in ['Director', 'School Administrator']}")
    
    # Directors and School Administrators have access to all classes
    # IMPORTANT: This check MUST be first to grant global access to admins
    if current_user.role in ['Director', 'School Administrator']:
        print(f"[DEBUG AUTH] ✓ Authorized: User is Director or School Administrator")
        print(f"[DEBUG AUTH] ===== ADMIN ACCESS GRANTED ===== Role: '{current_user.role}'")
        return True
    else:
        print(f"[DEBUG AUTH] ✗ Not Director/Admin, checking teacher assignments...")
    
    # Regular teachers can access classes where they are primary, additional, or substitute
    teacher = get_teacher_or_admin()
    if not teacher:
        print(f"[DEBUG AUTH] ✗ Not authorized: No teacher object found")
        return False
    
    print(f"[DEBUG AUTH] Teacher ID: {teacher.id}, Class teacher_id: {class_obj.teacher_id}")
    
    # Check if teacher is primary teacher
    if class_obj.teacher_id == teacher.id:
        print(f"[DEBUG AUTH] ✓ Authorized: Teacher is primary teacher")
        return True
    
    # Check additional teachers
    additional_count = db.session.query(class_additional_teachers).filter(
        class_additional_teachers.c.class_id == class_obj.id,
        class_additional_teachers.c.teacher_id == teacher.id
    ).count()
    print(f"[DEBUG AUTH] Additional teachers count: {additional_count}")
    if additional_count > 0:
        print(f"[DEBUG AUTH] ✓ Authorized: Teacher is additional teacher")
        return True
    
    # Check substitute teachers
    substitute_count = db.session.query(class_substitute_teachers).filter(
        class_substitute_teachers.c.class_id == class_obj.id,
        class_substitute_teachers.c.teacher_id == teacher.id
    ).count()
    print(f"[DEBUG AUTH] Substitute teachers count: {substitute_count}")
    if substitute_count > 0:
        print(f"[DEBUG AUTH] ✓ Authorized: Teacher is substitute teacher")
        return True
    
    print(f"[DEBUG AUTH] ✗ Not authorized: Teacher has no relationship to this class")
    return False

def is_admin():
    """Helper function to check if user is an administrator."""
    return current_user.role in ['Director', 'School Administrator']

def get_current_quarter():
    """Get the current quarter based on AcademicPeriod dates"""
    try:
        from datetime import date
        from models import SchoolYear, AcademicPeriod
        
        # Get the active school year
        current_school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_school_year:
            return "1"  # Default to Q1 if no active school year
        
        # Get all active quarters for the current school year
        quarters = AcademicPeriod.query.filter_by(
            school_year_id=current_school_year.id,
            period_type='quarter',
            is_active=True
        ).order_by(AcademicPeriod.start_date).all()
        
        if not quarters:
            return "1"  # Default to Q1 if no quarters defined
        
        # Get today's date
        today = date.today()
        
        # Find which quarter we're currently in
        for quarter in quarters:
            if quarter.start_date <= today <= quarter.end_date:
                # Extract quarter number from name (e.g., "Q1" -> "1")
                quarter_num = quarter.name.replace('Q', '')
                return quarter_num
        
        # If we're not in any quarter period, find the closest one
        # Check if we're before the first quarter
        if today < quarters[0].start_date:
            return quarters[0].name.replace('Q', '')
        
        # Check if we're after the last quarter
        if today > quarters[-1].end_date:
            return quarters[-1].name.replace('Q', '')
        
        # Default to Q1 if we can't determine
        return "1"
        
    except Exception as e:
        print(f"Error determining current quarter: {e}")
        return "1"  # Default to Q1 on error

def calculate_student_gpa(student_id):
    """Calculate GPA for a student based on their grades"""
    try:
        from models import Grade, Assignment
        
        # Get all grades for the student, excluding Voided assignments and voided grades
        grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student_id,
            Assignment.status != 'Voided',  # Exclude Voided assignments from GPA calculation
            Grade.is_voided == False  # Exclude voided individual grades
        ).all()
        
        if not grades:
            return 0.0
        
        total_points = 0
        earned_points = 0
        
        for grade in grades:
            total_points += grade.assignment.points
            earned_points += grade.points_earned
        
        if total_points == 0:
            return 0.0
        
        percentage = (earned_points / total_points) * 100
        
        # Convert percentage to GPA (4.0 scale)
        if percentage >= 97:
            return 4.0
        elif percentage >= 93:
            return 3.7
        elif percentage >= 90:
            return 3.3
        elif percentage >= 87:
            return 3.0
        elif percentage >= 83:
            return 2.7
        elif percentage >= 80:
            return 2.3
        elif percentage >= 77:
            return 2.0
        elif percentage >= 73:
            return 1.7
        elif percentage >= 70:
            return 1.3
        elif percentage >= 67:
            return 1.0
        else:
            return 0.0
            
    except Exception as e:
        print(f"Error calculating GPA for student {student_id}: {e}")
        return 0.0

