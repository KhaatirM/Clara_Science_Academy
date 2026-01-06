"""
Shared utilities and helper functions for management routes.
"""

from flask import current_app
from flask_login import current_user
from models import TeacherStaff, Class, SchoolYear, AcademicPeriod
from datetime import datetime, date, timedelta

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_assignment_statuses():
    """Update assignment statuses based on open_date, close_date, and due_date."""
    try:
        from models import Assignment, db
        from datetime import timezone
        
        assignments = Assignment.query.all()
        now = datetime.now(timezone.utc)
        today = now.date()
        
        for assignment in assignments:
            try:
                # Skip voided assignments - don't change their status
                if assignment.status == 'Voided':
                    continue
                
                # Check open_date and close_date if they exist
                # Helper to ensure timezone-aware datetime
                def ensure_aware(dt):
                    if dt is None:
                        return None
                    if dt.tzinfo is None:
                        return dt.replace(tzinfo=timezone.utc)
                    return dt
                
                # Get raw dates first
                raw_open_date = assignment.open_date if hasattr(assignment, 'open_date') and assignment.open_date else None
                raw_close_date = assignment.close_date if hasattr(assignment, 'close_date') and assignment.close_date else None
                due_date = assignment.due_date
                
                # Handle due_date - convert to date if datetime
                if due_date:
                    due_date = due_date.date() if hasattr(due_date, 'date') else due_date
                
                # Priority 1: Check if assignment is upcoming (open_date is in the future)
                if raw_open_date:
                    # Convert to timezone-aware datetime
                    if isinstance(raw_open_date, datetime):
                        open_date_dt = ensure_aware(raw_open_date)
                    else:
                        # It's a date object, convert to datetime at start of day
                        from datetime import date as date_type
                        if isinstance(raw_open_date, date_type):
                            open_date_dt = datetime.combine(raw_open_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                        else:
                            open_date_dt = ensure_aware(raw_open_date)
                    if open_date_dt > now:
                        # Assignment hasn't opened yet - set to Upcoming
                        if assignment.status != 'Upcoming':
                            assignment.status = 'Upcoming'
                        continue
                
                # Priority 2: Check if assignment has closed (close_date is in the past)
                if raw_close_date:
                    # Convert to timezone-aware datetime
                    if isinstance(raw_close_date, datetime):
                        close_date_dt = ensure_aware(raw_close_date)
                    else:
                        # It's a date object, convert to datetime at end of day
                        from datetime import date as date_type
                        if isinstance(raw_close_date, date_type):
                            close_date_dt = datetime.combine(raw_close_date, datetime.max.time()).replace(tzinfo=timezone.utc)
                        else:
                            close_date_dt = ensure_aware(raw_close_date)
                    if close_date_dt < now:
                        # Assignment has closed - set to Inactive
                        if assignment.status != 'Inactive':
                            assignment.status = 'Inactive'
                        continue
                
                # Priority 3: Check if assignment is past due
                if due_date and due_date < today:
                    if assignment.status == 'Active':
                        assignment.status = 'Overdue'
                elif due_date and due_date >= today:
                    # Assignment is not past due
                    if assignment.status == 'Overdue':
                        assignment.status = 'Active'
                    # If status is Upcoming but open_date has passed, set to Active
                    elif assignment.status == 'Upcoming' and (not raw_open_date or (raw_open_date and (
                        (isinstance(raw_open_date, datetime) and ensure_aware(raw_open_date) <= now) or
                        (not isinstance(raw_open_date, datetime) and datetime.combine(raw_open_date, datetime.min.time()).replace(tzinfo=timezone.utc) <= now)
                    ))):
                        assignment.status = 'Active'
                
            except (AttributeError, TypeError) as e:
                # Skip assignments with invalid dates
                print(f"Error updating assignment {assignment.id}: {e}")
                continue
        
        db.session.commit()
    except Exception as e:
        print(f"Error updating assignment statuses: {e}")
        db.session.rollback()

def get_current_quarter():
    """Get the current quarter based on AcademicPeriod dates"""
    try:
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

def add_academic_periods_for_year(school_year_id):
    """Create default academic periods for a school year"""
    from models import AcademicPeriod, SchoolYear, db
    
    # Get the school year to extract start and end dates
    school_year = SchoolYear.query.get(school_year_id)
    if not school_year:
        return
    
    # Create quarters (Q1, Q2, Q3, Q4)
    quarters = [
        ('Q1', date(school_year.start_date.year, school_year.start_date.month, 1), date(school_year.start_date.year, school_year.start_date.month + 2, 28)),
        ('Q2', date(school_year.start_date.year, school_year.start_date.month + 3, 1), date(school_year.start_date.year, school_year.start_date.month + 5, 30)),
        ('Q3', date(school_year.start_date.year, school_year.start_date.month + 6, 1), date(school_year.start_date.year, school_year.start_date.month + 8, 30)),
        ('Q4', date(school_year.start_date.year, school_year.start_date.month + 9, 1), date(school_year.end_date.year, school_year.end_date.month, school_year.end_date.day))
    ]
    
    for name, start_date, end_date in quarters:
        period = AcademicPeriod(
            school_year_id=school_year_id,
            name=name,
            period_type='quarter',
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        db.session.add(period)
    
    db.session.commit()



