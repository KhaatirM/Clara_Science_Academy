"""
Utility module for calculating and updating quarter grades.
This module handles automatic quarter grade calculations that refresh every 3 hours.
"""

from datetime import datetime, timedelta
from flask import current_app
from models import db, QuarterGrade, Grade, Assignment, Student, Class, SchoolYear, Enrollment, AcademicPeriod, GroupGrade, GroupAssignment
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
    # Convert quarter string to number if needed (handle both 'Q1' and 1 formats)
    quarter_number = int(quarter.replace('Q', '')) if isinstance(quarter, str) and quarter.startswith('Q') else int(quarter)
    quarter_str = str(quarter_number)  # String version: '1', '2', '3', '4'
    quarter_q_format = f'Q{quarter_number}'  # Q format: 'Q1', 'Q2', 'Q3', 'Q4'
    
    # Fetch all non-voided grades for this student, class, and quarter (regular assignments)
    from sqlalchemy import cast, String
    grades = db.session.query(Grade).join(Assignment).filter(
        Grade.student_id == student_id,
        Assignment.class_id == class_id,
        Assignment.school_year_id == school_year_id,
        db.or_(
            Assignment.quarter == quarter_q_format,  # 'Q1'
            Assignment.quarter == quarter_str,        # '1'
            cast(Assignment.quarter, String) == quarter_str  # Cast for safety
        ),
        Grade.is_voided == False
    ).all()

    # Fetch group assignment grades for this student, class, and quarter
    group_grades = db.session.query(GroupGrade).join(GroupAssignment).filter(
        GroupGrade.student_id == student_id,
        GroupAssignment.class_id == class_id,
        GroupAssignment.school_year_id == school_year_id,
        GroupGrade.is_voided == False,
        db.or_(
            GroupAssignment.quarter == quarter_q_format,
            GroupAssignment.quarter == quarter_str,
            cast(GroupAssignment.quarter, String) == quarter_str
        )
    ).all()
    
    # Check if student was enrolled during the quarter
    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        class_id=class_id
    ).first()
    
    if not enrollment:
        return None  # Student not enrolled in this class
    
    # Get quarter period to check enrollment date (try Q1 and 1 formats)
    quarter_normalized = quarter.replace('Q', '') if isinstance(quarter, str) and quarter.startswith('Q') else str(quarter)
    academic_period = AcademicPeriod.query.filter_by(
        school_year_id=school_year_id,
        name=quarter,
        period_type='quarter'
    ).first()
    if not academic_period:
        academic_period = AcademicPeriod.query.filter_by(
            school_year_id=school_year_id,
            name=quarter_normalized,
            period_type='quarter'
        ).first()
    if not academic_period:
        return None  # Quarter period not found
    
    # If we have grades for this quarter, include them regardless of enrollment date
    # This handles cases where assignments from previous quarters exist in classes
    # created in later quarters (e.g., Q1 assignment in a Q2 class)
    if grades or group_grades:
        # Student has grades for this quarter, so we should calculate the grade
        # Skip the enrollment date check in this case - grades exist, so include them
        pass
    else:
        # No grades found - check enrollment date to see if student should have grades
        # Check if student was enrolled during this quarter
        if enrollment.enrolled_at:
            # Convert datetime to date if needed
            enrolled_date = enrollment.enrolled_at.date() if hasattr(enrollment.enrolled_at, 'date') else enrollment.enrolled_at
            quarter_start = academic_period.start_date
            quarter_end = academic_period.end_date
            
            # Student enrolled after quarter ended AND has no grades - don't include
            # But if they have grades, include them (handles late-added assignments)
            if enrolled_date > quarter_end:
                return None
    
    # Check if student was unenrolled before or during the quarter
    if not enrollment.is_active and enrollment.dropped_at:
        # Convert datetime to date if needed
        dropped_date = enrollment.dropped_at.date() if hasattr(enrollment.dropped_at, 'date') else enrollment.dropped_at
        quarter_start = academic_period.start_date
        
        # Student dropped before quarter started - don't include
        if dropped_date < quarter_start:
            return None
    
    # Calculate weighted average from grades based on points earned vs total points
    # This ensures assignments with different point values are properly weighted
    total_points_sum = 0.0
    points_earned_sum = 0.0
    valid_grades_count = 0
    
    for grade in grades:
        try:
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            if not grade_data:
                continue
            
            # Get assignment total points (from assignment object) - always use as source of truth
            assignment = grade.assignment
            assignment_total_points = assignment.total_points if (hasattr(assignment, 'total_points') and assignment.total_points) else 100.0
            
            # Get points_earned from grade_data
            points_earned = grade_data.get('points_earned')
            
            # Always use assignment's total_points, not stored value in grade_data
            total_pts = float(assignment_total_points)
            
            # If points_earned is not available, try to derive it from percentage or score (backward compatibility)
            if points_earned is None:
                percentage = grade_data.get('percentage')
                score = grade_data.get('score')
                
                if percentage is not None:
                    # We have percentage, calculate points_earned
                    points_earned = (float(percentage) / 100.0) * total_pts
                elif score is not None:
                    # For backward compatibility: score might be percentage (old format) or points (new format)
                    # If total_points is set (new system), assume score is likely points
                    # If total_points is not set (old system, default 100), assume score is percentage
                    score_val = float(score)
                    if total_pts == 100.0 and score_val <= 100:
                        # Old system: score is likely a percentage (0-100)
                        points_earned = (score_val / 100.0) * total_pts
                    elif score_val > total_pts:
                        # Score exceeds total_points, must be a percentage
                        points_earned = (score_val / 100.0) * total_pts
                    else:
                        # Score is within total_points, assume it's points earned
                        points_earned = score_val
                else:
                    continue  # Skip if we can't determine points_earned
            else:
                # Convert to float if it's not already
                points_earned = float(points_earned)
            
            # Add to sums for weighted average calculation
            points_earned_sum += float(points_earned)
            total_points_sum += total_pts
            valid_grades_count += 1
            
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
            current_app.logger.warning(f"Could not parse grade data for grade {grade.id}: {e}")
            continue

    # Process group assignment grades
    for group_grade in group_grades:
        try:
            grade_data = json.loads(group_grade.grade_data) if isinstance(group_grade.grade_data, str) else group_grade.grade_data
            if not grade_data:
                continue

            ga = group_grade.group_assignment
            total_pts = ga.total_points if (hasattr(ga, 'total_points') and ga.total_points) else 100.0
            points_earned = grade_data.get('points_earned')

            if points_earned is None:
                percentage = grade_data.get('percentage')
                score = grade_data.get('score')
                if percentage is not None:
                    points_earned = (float(percentage) / 100.0) * total_pts
                elif score is not None:
                    score_val = float(score)
                    if total_pts == 100.0 and score_val <= 100:
                        points_earned = (score_val / 100.0) * total_pts
                    elif score_val > total_pts:
                        points_earned = (score_val / 100.0) * total_pts
                    else:
                        points_earned = score_val
                else:
                    continue
            else:
                points_earned = float(points_earned)

            points_earned_sum += float(points_earned)
            total_points_sum += float(total_pts)
            valid_grades_count += 1
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
            current_app.logger.warning(f"Could not parse group grade data for group_grade {group_grade.id}: {e}")
            continue

    if total_points_sum == 0 or valid_grades_count == 0:
        return None  # No valid grades
    
    # Calculate weighted average percentage
    average = (points_earned_sum / total_points_sum) * 100.0
    
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
        letter = 'D'  # Minimum letter grade
    
    return {
        'letter_grade': letter,
        'percentage': round(average, 2),
        'assignments_count': valid_grades_count
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
        # Normalize quarter format: ensure it's 'Q1', 'Q2', etc., not '1', '2', etc.
        quarter_key = qg.quarter
        if quarter_key and not quarter_key.startswith('Q'):
            # Convert '1' to 'Q1', '2' to 'Q2', etc.
            quarter_key = f"Q{quarter_key}"
        
        # Only add if quarter_key is valid
        if quarter_key in result:
            result[quarter_key][class_name] = {
                'letter': qg.letter_grade,
                'percentage': qg.percentage,
                'average': qg.percentage,  # Alias for compatibility
                'assignments_count': qg.assignments_count
            }
    
    return result

