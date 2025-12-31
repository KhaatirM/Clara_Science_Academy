"""
Helper functions for communications system.
"""

from models import User, Student, TeacherStaff

def get_user_full_name(user):
    """Get user's full name (first + last) from User model."""
    if not user:
        return 'Unknown'
    
    # Check if user is a student
    if user.student_id:
        student = Student.query.get(user.student_id)
        if student:
            return f"{student.first_name} {student.last_name}"
    
    # Check if user is a teacher/staff
    if user.teacher_staff_id:
        teacher = TeacherStaff.query.get(user.teacher_staff_id)
        if teacher:
            return f"{teacher.first_name} {teacher.last_name}"
    
    # Fallback to username if no profile found
    return user.username

