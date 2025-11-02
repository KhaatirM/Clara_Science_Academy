"""
Utilities for handling late enrollment and automatic assignment voiding.
"""

from datetime import datetime, timedelta, date
from models import (
    db, Enrollment, Grade, Assignment, AcademicPeriod, Class
)


def is_late_enrollment(enrollment_date, academic_period):
    """
    Check if a student enrolled within 2 weeks before the end of an academic period.
    
    Args:
        enrollment_date: datetime/date when student was enrolled
        academic_period: AcademicPeriod object
        
    Returns:
        bool: True if enrolled within 2 weeks of period end
    """
    if not academic_period or not enrollment_date:
        return False
    
    # Convert enrollment_date to date if it's datetime
    if isinstance(enrollment_date, datetime):
        enrollment_date = enrollment_date.date()
    
    # Calculate 2 weeks before period end
    two_weeks_before_end = academic_period.end_date - timedelta(days=14)
    
    # Check if enrollment is within this window
    return two_weeks_before_end <= enrollment_date <= academic_period.end_date


def get_academic_period_for_assignment(assignment):
    """
    Get the AcademicPeriod for an assignment, falling back to quarter calculation.
    
    Args:
        assignment: Assignment object
        
    Returns:
        AcademicPeriod or None
    """
    # First try to use the academic_period_id if set
    if assignment.academic_period_id:
        return assignment.academic_period
    
    # Fall back to finding period by quarter and school year
    if assignment.quarter and assignment.school_year_id:
        # Assignment quarter might be "1", "2", "3", "4" or "Q1", "Q2", "Q3", "Q4"
        # AcademicPeriod.name is typically "Q1", "Q2", "Q3", "Q4"
        quarter_value = assignment.quarter.strip()
        
        # Normalize quarter value to "Q1", "Q2", etc.
        if quarter_value and not quarter_value.startswith('Q'):
            # It's just a number, add "Q" prefix
            quarter_name = f"Q{quarter_value}"
        else:
            quarter_name = quarter_value
        
        # Try exact match first
        period = AcademicPeriod.query.filter_by(
            school_year_id=assignment.school_year_id,
            name=quarter_name,
            period_type='quarter'
        ).first()
        
        if period:
            return period
        
        # Try without the "Q" prefix as fallback
        if quarter_name.startswith('Q'):
            period = AcademicPeriod.query.filter_by(
                school_year_id=assignment.school_year_id,
                name=quarter_name[1:],  # Remove "Q" prefix
                period_type='quarter'
            ).first()
            if period:
                return period
        
        # Last resort: try matching by due date within period range
        if assignment.due_date:
            from sqlalchemy import and_
            periods = AcademicPeriod.query.filter_by(
                school_year_id=assignment.school_year_id,
                period_type='quarter'
            ).all()
            
            assignment_date = assignment.due_date.date() if hasattr(assignment.due_date, 'date') else assignment.due_date
            
            for period in periods:
                if period.start_date <= assignment_date <= period.end_date:
                    return period
    
    return None


def should_void_assignment_for_student(student_id, assignment, enrollment):
    """
    Determine if an assignment should be voided for a student based on late enrollment.
    
    Policy:
    - Q1: If enrolled within 2 weeks of Q1 end, void all Q1 assignments
    - Q2+: Only void assignments from quarters where enrollment was within 2 weeks of that quarter's end
    
    Args:
        student_id: ID of the student
        assignment: Assignment object
        enrollment: Enrollment object for the student in this class
        
    Returns:
        bool: True if assignment should be voided
    """
    if not enrollment or not enrollment.enrolled_at:
        return False
    
    # Get the academic period for this assignment
    academic_period = get_academic_period_for_assignment(assignment)
    if not academic_period:
        # If we can't determine the period, don't void (conservative approach)
        return False
    
    # Check if enrollment was within 2 weeks of this specific quarter's end OR after quarter ended
    enrollment_date = enrollment.enrolled_at.date() if isinstance(enrollment.enrolled_at, datetime) else enrollment.enrolled_at
    
    # If enrolled after quarter ended, definitely void
    if enrollment_date > academic_period.end_date:
        return True
    
    # If enrolled within 2 weeks before quarter end, void
    return is_late_enrollment(enrollment.enrolled_at, academic_period)


def void_assignments_for_late_enrollment(student_id, class_id):
    """
    Automatically void all appropriate assignments for a student who enrolled late.
    This should be called when a student is enrolled in a class.
    
    Args:
        student_id: ID of the student
        class_id: ID of the class
        
    Returns:
        int: Number of grades voided
    """
    # Get the enrollment record
    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        class_id=class_id,
        is_active=True
    ).first()
    
    if not enrollment or not enrollment.enrolled_at:
        return 0
    
    # Get all assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).all()
    
    # Also get group assignments
    from models import GroupAssignment, GroupGrade, StudentGroupMember
    group_assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
    
    voided_count = 0
    
    # Void individual assignments
    for assignment in assignments:
        if should_void_assignment_for_student(student_id, assignment, enrollment):
            # Find or create grades for this assignment and void them
            grades = Grade.query.filter_by(
                student_id=student_id,
                assignment_id=assignment.id
            ).all()
            
            for grade in grades:
                if not grade.is_voided:
                    grade.is_voided = True
                    grade.voided_at = datetime.utcnow()
                    grade.voided_by = 1  # System user
                    grade.voided_reason = (
                        f"Student enrolled late ({enrollment.enrolled_at.strftime('%Y-%m-%d')}) "
                        f"within 2 weeks of Q{assignment.quarter} end. "
                        f"Assignment automatically voided per late enrollment policy."
                    )
                    voided_count += 1
    
    # Void group assignments
    for group_assignment in group_assignments:
        if should_void_assignment_for_student(student_id, group_assignment, enrollment):
            # Find student's group
            member = StudentGroupMember.query.filter_by(student_id=student_id).first()
            
            if member:
                # Find group grades
                group_grades = GroupGrade.query.filter_by(
                    group_assignment_id=group_assignment.id,
                    student_group_id=member.student_group_id
                ).all()
                
                for grade in group_grades:
                    if not grade.is_voided:
                        grade.is_voided = True
                        grade.voided_at = datetime.utcnow()
                        grade.voided_by = 1  # System user
                        grade.voided_reason = (
                            f"Student enrolled late ({enrollment.enrolled_at.strftime('%Y-%m-%d')}) "
                            f"within 2 weeks of Q{group_assignment.quarter} end. "
                            f"Group assignment automatically voided per late enrollment policy."
                        )
                        voided_count += 1
    
    if voided_count > 0:
        db.session.commit()
        
        # Update quarter grades for this student
        from utils.quarter_grade_calculator import update_all_quarter_grades_for_student
        try:
            class_obj = Class.query.get(class_id)
            if class_obj and class_obj.school_year_id:
                update_all_quarter_grades_for_student(
                    student_id=student_id,
                    school_year_id=class_obj.school_year_id,
                    force=True
                )
        except Exception as e:
            print(f"Could not update quarter grades for student {student_id}: {e}")
    
    return voided_count


def check_and_void_grade(grade):
    """
    Check if a grade should be voided based on late enrollment and void it if needed.
    This should be called whenever a grade is created or updated.
    
    Args:
        grade: Grade object (must have student_id and assignment_id set)
        
    Returns:
        bool: True if grade was voided, False otherwise
    """
    if not grade or not grade.assignment_id or not grade.student_id:
        return False
    
    # If already voided, don't do anything
    if hasattr(grade, 'is_voided') and grade.is_voided:
        return False
    
    # Get the assignment and enrollment
    assignment = Assignment.query.get(grade.assignment_id)
    if not assignment:
        return False
    
    enrollment = Enrollment.query.filter_by(
        student_id=grade.student_id,
        class_id=assignment.class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        return False
    
    # Check if this assignment should be voided
    if should_void_assignment_for_student(grade.student_id, assignment, enrollment):
        grade.is_voided = True
        grade.voided_at = datetime.utcnow()
        grade.voided_by = 1  # System user
        grade.voided_reason = (
            f"Student enrolled late ({enrollment.enrolled_at.strftime('%Y-%m-%d')}) "
            f"within 2 weeks of Q{assignment.quarter} end. "
            f"Assignment automatically voided per late enrollment policy."
        )
        # Don't commit here - let the calling function handle the commit
        # This allows it to work within existing transactions
        return True
    
    return False


def check_and_void_existing_enrollments():
    """
    Retroactively check all existing enrollments and void assignments for late enrollments.
    Useful for migrating existing data.
    
    Returns:
        dict: Summary of voided assignments per student
    """
    results = {}
    
    # Get all active enrollments
    enrollments = Enrollment.query.filter_by(is_active=True).all()
    
    for enrollment in enrollments:
        voided_count = void_assignments_for_late_enrollment(
            enrollment.student_id,
            enrollment.class_id
        )
        
        if voided_count > 0:
            student_key = f"{enrollment.student_id}_{enrollment.class_id}"
            results[student_key] = {
                'student_id': enrollment.student_id,
                'class_id': enrollment.class_id,
                'voided_count': voided_count
            }
    
    return results

