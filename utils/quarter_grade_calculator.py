"""
Utility module for calculating and updating quarter grades.
This module handles automatic quarter grade calculations that refresh every 3 hours.
"""

from datetime import datetime, timedelta
from flask import current_app
from models import db, QuarterGrade, Grade, Assignment, Student, Class, SchoolYear, Enrollment, AcademicPeriod
import json


def calculate_quarter_grade_for_student_class(student_id, class_id, school_year_id, quarter):
    """
    Calculate quarter grade for a specific student in a specific class.
    Only includes assignments for that quarter, excludes voided assignments.
    
    Args:
        student_id: ID of the student
        class_id: ID of the class
        school_year_id: ID of the school year
        quarter: Quarter name ('Q1', 'Q2', 'Q3', 'Q4')
    
    Returns:
        dict: {'letter_grade': 'A', 'percentage': 95.5, 'assignments_count': 10}
    """
    # Fetch all non-voided grades for this student, class, and quarter
    grades = db.session.query(Grade).join(Assignment).filter(
        Grade.student_id == student_id,
        Assignment.class_id == class_id,
        Assignment.school_year_id == school_year_id,
        Assignment.quarter == quarter,
        Grade.is_voided == False
    ).all()
    
    # Check if student was enrolled during the quarter
    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        class_id=class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        return None  # Student not enrolled in this class
    
    # Get quarter period to check enrollment date
    academic_period = AcademicPeriod.query.filter_by(
        school_year_id=school_year_id,
        name=quarter,
        period_type='quarter'
    ).first()
    
    # If student enrolled after quarter ended, don't calculate grade
    if academic_period and enrollment.enrolled_at:
        # Convert datetime to date if needed
        enrolled_date = enrollment.enrolled_at.date() if hasattr(enrollment.enrolled_at, 'date') else enrollment.enrolled_at
        quarter_end = academic_period.end_date
        
        if enrolled_date >= quarter_end:
            return None  # Student enrolled after quarter ended
    
    # Calculate average from grades
    scores = []
    for grade in grades:
        try:
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            if grade_data and 'score' in grade_data and grade_data['score'] is not None:
                scores.append(float(grade_data['score']))
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            current_app.logger.warning(f"Could not parse grade data for grade {grade.id}: {e}")
            continue
    
    if not scores:
        return None  # No valid grades
    
    # Calculate average
    average = sum(scores) / len(scores)
    
    # Convert to letter grade
    if average >= 95:
        letter = 'A'
    elif average >= 90:
        letter = 'A-'
    elif average >= 87:
        letter = 'B+'
    elif average >= 83:
        letter = 'B'
    elif average >= 80:
        letter = 'B-'
    elif average >= 77:
        letter = 'C+'
    elif average >= 73:
        letter = 'C'
    elif average >= 70:
        letter = 'C-'
    elif average >= 65:
        letter = 'D'
    else:
        letter = 'F'
    
    return {
        'letter_grade': letter,
        'percentage': round(average, 2),
        'assignments_count': len(scores)
    }


def update_quarter_grade(student_id, class_id, school_year_id, quarter, force=False):
    """
    Update or create a quarter grade record.
    Only updates if grade doesn't exist, is outdated (>3 hours), or force=True.
    
    Args:
        student_id: ID of the student
        class_id: ID of the class
        school_year_id: ID of the school year
        quarter: Quarter name ('Q1', 'Q2', 'Q3', 'Q4')
        force: If True, recalculates even if recently updated
    
    Returns:
        QuarterGrade object or None
    """
    # Check if grade already exists
    quarter_grade = QuarterGrade.query.filter_by(
        student_id=student_id,
        class_id=class_id,
        school_year_id=school_year_id,
        quarter=quarter
    ).first()
    
    # Check if we need to update
    now = datetime.utcnow()
    needs_update = False
    
    if not quarter_grade:
        needs_update = True
    elif force:
        needs_update = True
    elif quarter_grade.last_calculated:
        time_since_calculation = now - quarter_grade.last_calculated
        if time_since_calculation > timedelta(hours=3):
            needs_update = True
    else:
        needs_update = True
    
    if not needs_update:
        return quarter_grade
    
    # Calculate the grade
    grade_data = calculate_quarter_grade_for_student_class(
        student_id, class_id, school_year_id, quarter
    )
    
    if grade_data is None:
        # No grades or student not enrolled properly - delete if exists
        if quarter_grade:
            db.session.delete(quarter_grade)
            db.session.commit()
        return None
    
    # Create or update the record
    if not quarter_grade:
        quarter_grade = QuarterGrade(
            student_id=student_id,
            class_id=class_id,
            school_year_id=school_year_id,
            quarter=quarter
        )
        db.session.add(quarter_grade)
    
    quarter_grade.letter_grade = grade_data['letter_grade']
    quarter_grade.percentage = grade_data['percentage']
    quarter_grade.assignments_count = grade_data['assignments_count']
    quarter_grade.last_calculated = now
    
    db.session.commit()
    return quarter_grade


def update_all_quarter_grades_for_student(student_id, school_year_id, force=False):
    """
    Update quarter grades for all classes a student is enrolled in.
    
    Args:
        student_id: ID of the student
        school_year_id: ID of the school year
        force: If True, recalculates even if recently updated
    """
    # Get all active enrollments
    enrollments = Enrollment.query.filter_by(
        student_id=student_id,
        is_active=True
    ).join(Class).filter(
        Class.school_year_id == school_year_id
    ).all()
    
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    
    for enrollment in enrollments:
        for quarter in quarters:
            update_quarter_grade(
                student_id=student_id,
                class_id=enrollment.class_id,
                school_year_id=school_year_id,
                quarter=quarter,
                force=force
            )


def get_quarter_grades_for_report(student_id, school_year_id, class_ids=None):
    """
    Get formatted quarter grades for report card PDF generation.
    
    Args:
        student_id: ID of the student
        school_year_id: ID of the school year  
        class_ids: Optional list of class IDs to filter
    
    Returns:
        dict: {'Q1': {'Math [4th]': {'letter': 'A', 'percentage': 95}, ...}, ...}
    """
    query = QuarterGrade.query.filter_by(
        student_id=student_id,
        school_year_id=school_year_id
    ).join(Class)
    
    if class_ids:
        query = query.filter(QuarterGrade.class_id.in_(class_ids))
    
    quarter_grades = query.all()
    
    # Organize by quarter, then by class name
    result = {
        'Q1': {},
        'Q2': {},
        'Q3': {},
        'Q4': {}
    }
    
    for qg in quarter_grades:
        class_name = qg.class_info.name if qg.class_info else f"Class {qg.class_id}"
        result[qg.quarter][class_name] = {
            'letter': qg.letter_grade,
            'percentage': qg.percentage,
            'average': qg.percentage,  # Alias for compatibility
            'assignments_count': qg.assignments_count
        }
    
    return result

