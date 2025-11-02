"""
Automatic quarter grade refresh script.
This should be run as a cron job every 3 hours to keep quarter grades up-to-date.

Can also be triggered manually by administrators.
"""

from datetime import datetime, date
from flask import current_app
from models import db, Student, SchoolYear, AcademicPeriod, Enrollment, Class
from utils.quarter_grade_calculator import update_quarter_grade


def should_calculate_quarter_grade(quarter_period, enrollment):
    """
    Determine if we should calculate a grade for this quarter.
    
    Rules:
    - Only calculate if quarter has ended
    - Only if student was enrolled before quarter ended
    - Only if student is still actively enrolled or dropped after quarter ended
    """
    if not quarter_period:
        return False
    
    today = date.today()
    
    # Only calculate for ended quarters
    if today < quarter_period.end_date:
        return False
    
    # Check enrollment timing
    if enrollment.enrolled_at:
        enrolled_date = enrollment.enrolled_at.date() if hasattr(enrollment.enrolled_at, 'date') else enrollment.enrolled_at
        
        # Don't calculate if enrolled after quarter ended
        if enrolled_date > quarter_period.end_date:
            return False
    
    # Check if dropped before quarter ended
    if enrollment.dropped_at:
        dropped_date = enrollment.dropped_at.date() if hasattr(enrollment.dropped_at, 'date') else enrollment.dropped_at
        
        # Don't calculate if dropped before quarter ended
        if dropped_date < quarter_period.end_date:
            return False
    
    return True


def refresh_all_quarter_grades(force=False, school_year_id=None):
    """
    Refresh quarter grades for all students in all classes.
    Respects 3-hour refresh interval unless force=True.
    
    Args:
        force: If True, recalculates even if recently updated
        school_year_id: If provided, only refresh for this school year
    
    Returns:
        dict: Statistics about the refresh
    """
    stats = {
        'total_students': 0,
        'total_grades_updated': 0,
        'total_grades_skipped': 0,
        'errors': 0,
        'started_at': datetime.utcnow()
    }
    
    # Get school year(s)
    if school_year_id:
        school_years = [SchoolYear.query.get(school_year_id)]
    else:
        # Only process active school year
        school_years = SchoolYear.query.filter_by(is_active=True).all()
    
    if not school_years:
        current_app.logger.warning("No school years to process")
        return stats
    
    for school_year in school_years:
        current_app.logger.info(f"Processing school year: {school_year.name}")
        
        # Get all academic periods for this school year
        quarters = AcademicPeriod.query.filter_by(
            school_year_id=school_year.id,
            period_type='quarter',
            is_active=True
        ).all()
        
        quarter_map = {q.name: q for q in quarters}
        
        # Get all students
        students = Student.query.all()
        stats['total_students'] += len(students)
        
        for student in students:
            try:
                # Get all enrollments for this student in this school year
                enrollments = Enrollment.query.join(Class).filter(
                    Enrollment.student_id == student.id,
                    Class.school_year_id == school_year.id
                ).all()
                
                for enrollment in enrollments:
                    # Process each quarter
                    for quarter_name in ['Q1', 'Q2', 'Q3', 'Q4']:
                        quarter_period = quarter_map.get(quarter_name)
                        
                        # Check if we should calculate this quarter
                        if not should_calculate_quarter_grade(quarter_period, enrollment):
                            stats['total_grades_skipped'] += 1
                            continue
                        
                        # Update the grade
                        result = update_quarter_grade(
                            student_id=student.id,
                            class_id=enrollment.class_id,
                            school_year_id=school_year.id,
                            quarter=quarter_name,
                            force=force
                        )
                        
                        if result:
                            stats['total_grades_updated'] += 1
                        else:
                            stats['total_grades_skipped'] += 1
                
            except Exception as e:
                current_app.logger.error(f"Error processing student {student.id}: {e}")
                stats['errors'] += 1
    
    stats['completed_at'] = datetime.utcnow()
    stats['duration_seconds'] = (stats['completed_at'] - stats['started_at']).total_seconds()
    
    return stats


def refresh_quarter_grades_for_ended_quarters():
    """
    Smart refresh - only processes quarters that have recently ended.
    Checks quarters that ended in the last 30 days.
    """
    from datetime import timedelta
    
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    
    # Get recently ended quarters
    recent_quarters = AcademicPeriod.query.filter(
        AcademicPeriod.period_type == 'quarter',
        AcademicPeriod.is_active == True,
        AcademicPeriod.end_date >= thirty_days_ago,
        AcademicPeriod.end_date <= today
    ).all()
    
    if not recent_quarters:
        current_app.logger.info("No recently ended quarters to process")
        return {'message': 'No recently ended quarters'}
    
    stats = {
        'quarters_processed': [],
        'total_grades_updated': 0,
        'started_at': datetime.utcnow()
    }
    
    for quarter in recent_quarters:
        current_app.logger.info(f"Processing recently ended quarter: {quarter.name} in {quarter.school_year.name}")
        
        # Get all students enrolled in classes for this school year
        students = Student.query.join(Enrollment).join(Class).filter(
            Class.school_year_id == quarter.school_year_id
        ).distinct().all()
        
        for student in students:
            enrollments = Enrollment.query.join(Class).filter(
                Enrollment.student_id == student.id,
                Class.school_year_id == quarter.school_year_id
            ).all()
            
            for enrollment in enrollments:
                if should_calculate_quarter_grade(quarter, enrollment):
                    result = update_quarter_grade(
                        student_id=student.id,
                        class_id=enrollment.class_id,
                        school_year_id=quarter.school_year_id,
                        quarter=quarter.name,
                        force=False  # Respects 3-hour window
                    )
                    if result:
                        stats['total_grades_updated'] += 1
        
        stats['quarters_processed'].append({
            'name': quarter.name,
            'school_year': quarter.school_year.name,
            'end_date': quarter.end_date.isoformat()
        })
    
    stats['completed_at'] = datetime.utcnow()
    return stats


if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    with app.app_context():
        print("Starting automatic quarter grade refresh...")
        stats = refresh_quarter_grades_for_ended_quarters()
        print(f"\n✓ Refresh completed!")
        print(f"  Quarters processed: {len(stats.get('quarters_processed', []))}")
        print(f"  Grades updated: {stats.get('total_grades_updated', 0)}")
        if stats.get('quarters_processed'):
            print("\n  Processed quarters:")
            for q in stats['quarters_processed']:
                print(f"    - {q['name']} ({q['school_year']}) ended {q['end_date']}")

