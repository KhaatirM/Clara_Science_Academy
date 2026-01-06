"""
Utility functions for assignment status and date calculations.
"""
from datetime import datetime, timezone
from models import AssignmentExtension

def calculate_assignment_status(assignment):
    """
    Calculate assignment status based on open_date, close_date, and current date.
    
    Status logic:
    - 'Voided': If assignment.status is 'Voided' (manual override)
    - 'Upcoming': If current time is before open_date (or before close_date if no open_date)
    - 'Active': If current time is between open_date and close_date (or past open_date if no close_date)
    - 'Inactive': If current time is past close_date (or past due_date if no close_date)
    
    Returns:
        str: 'Upcoming', 'Active', 'Inactive', or 'Voided'
    """
    if assignment.status == 'Voided':
        return 'Voided'
    
    now = datetime.now(timezone.utc)  # Use timezone-aware datetime
    
    # If assignment has open_date, check if we're before it
    if assignment.open_date:
        open_datetime = assignment.open_date
        # Ensure open_datetime is timezone-aware
        if isinstance(open_datetime, datetime):
            if open_datetime.tzinfo is None:
                open_datetime = open_datetime.replace(tzinfo=timezone.utc)
        else:
            open_datetime = datetime.combine(open_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
        if now < open_datetime:
            return 'Upcoming'
    
    # Check close_date (or due_date if close_date not set)
    close_datetime = None
    if assignment.close_date:
        close_datetime = assignment.close_date
        # Ensure close_datetime is timezone-aware
        if isinstance(close_datetime, datetime):
            if close_datetime.tzinfo is None:
                close_datetime = close_datetime.replace(tzinfo=timezone.utc)
        else:
            close_datetime = datetime.combine(close_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
    elif assignment.due_date:
        # If close_date not set, use due_date as close_date
        close_datetime = assignment.due_date
        # Ensure close_datetime is timezone-aware
        if isinstance(close_datetime, datetime):
            if close_datetime.tzinfo is None:
                close_datetime = close_datetime.replace(tzinfo=timezone.utc)
        else:
            close_datetime = datetime.combine(close_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    if close_datetime:
        if now > close_datetime:
            return 'Inactive'
        else:
            # We're past open_date (if set) and before close_date
            return 'Active'
    else:
        # No close_date or due_date - default to Active if we're past open_date (or always Active if no open_date)
        if assignment.open_date:
            open_datetime = assignment.open_date
            # Ensure open_datetime is timezone-aware
            if isinstance(open_datetime, datetime):
                if open_datetime.tzinfo is None:
                    open_datetime = open_datetime.replace(tzinfo=timezone.utc)
            else:
                open_datetime = datetime.combine(open_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
            if now >= open_datetime:
                return 'Active'
            else:
                return 'Upcoming'
        else:
            # No open_date or close_date - default to Active
            return 'Active'


def get_student_close_date(assignment, student_id):
    """
    Get the effective close date for a student, considering extensions.
    
    Args:
        assignment: Assignment object
        student_id: Student ID to check for extensions
    
    Returns:
        datetime: The effective close date for this student (extension date if exists, otherwise assignment close_date or due_date)
    """
    # Check for active extension
    if student_id:
        extension = AssignmentExtension.query.filter_by(
            assignment_id=assignment.id,
            student_id=student_id,
            is_active=True
        ).first()
        
        if extension and extension.extended_due_date:
            return extension.extended_due_date
    
    # No extension - use close_date or due_date
    if assignment.close_date:
        close_dt = assignment.close_date
        if isinstance(close_dt, datetime):
            # Ensure timezone-aware
            if close_dt.tzinfo is None:
                close_dt = close_dt.replace(tzinfo=timezone.utc)
            return close_dt
        else:
            return datetime.combine(close_dt, datetime.min.time()).replace(tzinfo=timezone.utc)
    elif assignment.due_date:
        due_dt = assignment.due_date
        if isinstance(due_dt, datetime):
            # Ensure timezone-aware
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            return due_dt
        else:
            return datetime.combine(due_dt, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    return None


def is_assignment_open_for_student(assignment, student_id):
    """
    Check if an assignment is currently open for submission for a specific student.
    
    Args:
        assignment: Assignment object
        student_id: Student ID to check
    
    Returns:
        bool: True if assignment is open for this student, False otherwise
    """
    # Check if assignment is voided
    if assignment.status == 'Voided':
        return False
    
    now = datetime.now(timezone.utc)  # Use timezone-aware datetime
    
    # Check open_date
    if assignment.open_date:
        open_datetime = assignment.open_date
        # Ensure open_datetime is timezone-aware
        if isinstance(open_datetime, datetime):
            if open_datetime.tzinfo is None:
                open_datetime = open_datetime.replace(tzinfo=timezone.utc)
        else:
            open_datetime = datetime.combine(open_datetime, datetime.min.time()).replace(tzinfo=timezone.utc)
        if now < open_datetime:
            return False  # Assignment hasn't opened yet
    
    # Check close_date (with extension support)
    student_close_date = get_student_close_date(assignment, student_id)
    if student_close_date:
        if now > student_close_date:
            return False  # Assignment is closed (even with extension)
    
    return True  # Assignment is open

