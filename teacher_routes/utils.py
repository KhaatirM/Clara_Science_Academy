"""
Shared utilities and helper functions for teacher routes.
"""

from flask import current_app
from flask_login import current_user
from models import TeacherStaff, Class
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

def is_authorized_for_class(class_obj):
    """Check if current user is authorized to access a specific class."""
    if current_user.role == 'Director':
        return True  # Directors have access to all classes
    elif current_user.role == 'School Administrator':
        # School Administrators can access classes they are assigned to as teachers
        teacher_staff = None
        if current_user.teacher_staff_id:
            teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
        return teacher_staff and class_obj.teacher_id == teacher_staff.id
    else:
        # Regular teachers can only access their own classes
        teacher = get_teacher_or_admin()
        return teacher and class_obj.teacher_id == teacher.id

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
        
        # Get all grades for the student, excluding Voided assignments
        grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student_id,
            Assignment.status != 'Voided'  # Exclude Voided assignments from GPA calculation
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

