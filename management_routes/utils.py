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
    """Update assignment statuses (Assignment and GroupAssignment) based on open_date, close_date, and due_date."""
    try:
        from models import Assignment, GroupAssignment, db
        from datetime import timezone
        
        now = datetime.now(timezone.utc)
        today = now.date()
        
        def ensure_aware(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        
        # --- Regular Assignments ---
        assignments = Assignment.query.all()
        for assignment in assignments:
            try:
                # Skip voided assignments - don't change their status
                if assignment.status == 'Voided':
                    continue
                # Clear expired status override, then run normal logic
                if getattr(assignment, 'status_override_until', None):
                    until_dt = assignment.status_override_until
                    if hasattr(until_dt, 'tzinfo') and until_dt.tzinfo is None and hasattr(until_dt, 'replace'):
                        until_dt = until_dt.replace(tzinfo=timezone.utc)
                    if until_dt and until_dt < now:
                        assignment.status_override = None
                        assignment.status_override_until = None
                # Skip if status override is active (manual override until date)
                if getattr(assignment, 'status_override', None) and getattr(assignment, 'status_override_until', None):
                    until_dt = assignment.status_override_until
                    if hasattr(until_dt, 'tzinfo') and until_dt.tzinfo is None and hasattr(until_dt, 'replace'):
                        until_dt = until_dt.replace(tzinfo=timezone.utc)
                    if until_dt and until_dt > now:
                        continue  # Don't overwrite - teacher set temporary override
                
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
        
        # --- Group Assignments (same logic: due/close date -> Inactive) ---
        from datetime import date as date_type
        group_assignments = GroupAssignment.query.all()
        for ga in group_assignments:
            try:
                if ga.status == 'Voided':
                    continue
                # Clear expired status override
                if getattr(ga, 'status_override_until', None):
                    until_dt = ga.status_override_until
                    if hasattr(until_dt, 'tzinfo') and until_dt.tzinfo is None and hasattr(until_dt, 'replace'):
                        until_dt = until_dt.replace(tzinfo=timezone.utc)
                    if until_dt and until_dt < now:
                        ga.status_override = None
                        ga.status_override_until = None
                # Skip if status override is active
                if getattr(ga, 'status_override', None) and getattr(ga, 'status_override_until', None):
                    until_dt = ga.status_override_until
                    if hasattr(until_dt, 'tzinfo') and until_dt.tzinfo is None and hasattr(until_dt, 'replace'):
                        until_dt = until_dt.replace(tzinfo=timezone.utc)
                    if until_dt and until_dt > now:
                        continue
                raw_open_date = getattr(ga, 'open_date', None) and ga.open_date or None
                raw_close_date = getattr(ga, 'close_date', None) and ga.close_date or None
                due_date = ga.due_date
                if due_date:
                    due_date = due_date.date() if hasattr(due_date, 'date') else due_date
                if raw_open_date:
                    if isinstance(raw_open_date, datetime):
                        open_date_dt = ensure_aware(raw_open_date)
                    else:
                        open_date_dt = datetime.combine(raw_open_date, datetime.min.time()).replace(tzinfo=timezone.utc) if isinstance(raw_open_date, date_type) else ensure_aware(raw_open_date)
                    if open_date_dt > now:
                        if ga.status != 'Upcoming':
                            ga.status = 'Upcoming'
                        continue
                if raw_close_date:
                    if isinstance(raw_close_date, datetime):
                        close_date_dt = ensure_aware(raw_close_date)
                    else:
                        close_date_dt = datetime.combine(raw_close_date, datetime.max.time()).replace(tzinfo=timezone.utc) if isinstance(raw_close_date, date_type) else ensure_aware(raw_close_date)
                    if close_date_dt < now:
                        if ga.status != 'Inactive':
                            ga.status = 'Inactive'
                        continue
                # When no close_date, treat past due_date as closed -> Inactive (so they go inactive on admin/student side)
                if due_date and due_date < today:
                    if ga.status != 'Inactive':
                        ga.status = 'Inactive'
                    continue
                if due_date and due_date >= today:
                    if ga.status == 'Overdue':
                        ga.status = 'Active'
                    elif ga.status == 'Upcoming' and (not raw_open_date or (raw_open_date and (
                        (isinstance(raw_open_date, datetime) and ensure_aware(raw_open_date) <= now) or
                        (not isinstance(raw_open_date, datetime) and datetime.combine(raw_open_date, datetime.min.time()).replace(tzinfo=timezone.utc) <= now)
                    ))):
                        ga.status = 'Active'
            except (AttributeError, TypeError) as e:
                print(f"Error updating group assignment {ga.id}: {e}")
                continue
        
        db.session.commit()
        # Apply automatic 0 for students with no grade 7 days after due/close
        apply_auto_zeros_for_past_due_assignments()
    except Exception as e:
        print(f"Error updating assignment statuses: {e}")
        db.session.rollback()


def apply_auto_zeros_for_past_due_assignments():
    """
    For assignments (regular and group) that are past due/close: if a student has no grade
    by 7 days after the due/close date, automatically assign a 0. Respects per-student
    extensions. Voided assignments are skipped. New grades are checked for late-enrollment voiding.
    """
    try:
        from models import (
            Assignment, GroupAssignment, Grade, GroupGrade,
            Enrollment, AssignmentExtension, GroupAssignmentExtension,
            StudentGroup, StudentGroupMember, TeacherStaff, db
        )
        from datetime import timezone
        import json

        now = datetime.now(timezone.utc)
        auto_zero_grace_days = timedelta(days=7)

        def to_aware_dt(raw):
            """Return timezone-aware datetime (end of day if date-only)."""
            if not raw:
                return None
            if getattr(raw, 'tzinfo', None):
                return raw.replace(tzinfo=timezone.utc) if raw.tzinfo is None else raw
            if hasattr(raw, 'date'):
                d = raw.date() if callable(getattr(raw, 'date', None)) else raw
                return datetime.combine(d, datetime.max.time()).replace(tzinfo=timezone.utc)
            return datetime.combine(raw, datetime.max.time()).replace(tzinfo=timezone.utc)

        def effective_close_dt(assignment):
            """Return timezone-aware datetime for assignment close (close_date or due_date)."""
            raw = getattr(assignment, 'close_date', None) and assignment.close_date or assignment.due_date
            return to_aware_dt(raw)

        # --- Regular assignments ---
        for assignment in Assignment.query.filter(Assignment.status != 'Voided').all():
            try:
                base_close = effective_close_dt(assignment)
                if not base_close or now <= base_close + auto_zero_grace_days:
                    continue
                total_points = getattr(assignment, 'total_points', None) or 100.0
                enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
                for enr in enrollments:
                    if not enr.student_id:
                        continue
                    student_id = enr.student_id
                    # Student's effective close: extension if active, else base
                    ext = AssignmentExtension.query.filter_by(
                        assignment_id=assignment.id, student_id=student_id, is_active=True
                    ).first()
                    student_close = to_aware_dt(ext.extended_due_date) if ext and getattr(ext, 'extended_due_date', None) else base_close
                    if not student_close or now <= student_close + auto_zero_grace_days:
                        continue
                    existing = Grade.query.filter_by(assignment_id=assignment.id, student_id=student_id).first()
                    if existing:
                        continue
                    grade_data = json.dumps({
                        'score': 0.0, 'points_earned': 0.0, 'total_points': total_points,
                        'max_score': total_points, 'percentage': 0.0, 'feedback': '',
                        'comment': '', 'graded_at': now.isoformat(), 'auto_zero': True
                    })
                    g = Grade(
                        student_id=student_id, assignment_id=assignment.id,
                        grade_data=grade_data, graded_at=now
                    )
                    db.session.add(g)
                    db.session.flush()
                    try:
                        from management_routes.late_enrollment_utils import check_and_void_grade
                        check_and_void_grade(g)
                    except Exception:
                        pass
            except Exception as e:
                current_app.logger.warning("apply_auto_zeros assignment %s: %s", getattr(assignment, 'id', '?'), e)
                continue

        # --- Group assignments ---
        for ga in GroupAssignment.query.filter(GroupAssignment.status != 'Voided').all():
            try:
                base_close = effective_close_dt(ga)
                if not base_close or now <= base_close + auto_zero_grace_days:
                    continue
                total_points = getattr(ga, 'total_points', None) or 100.0
                # Students in this assignment's groups
                try:
                    sel = ga.selected_group_ids
                    if sel:
                        ids = json.loads(sel) if isinstance(sel, str) else sel
                        ids = [int(x) for x in ids]
                        members = StudentGroupMember.query.join(StudentGroup).filter(
                            StudentGroup.id.in_(ids),
                            StudentGroup.class_id == ga.class_id,
                            StudentGroup.is_active == True
                        ).all()
                    else:
                        members = StudentGroupMember.query.join(StudentGroup).filter(
                            StudentGroup.class_id == ga.class_id,
                            StudentGroup.is_active == True
                        ).all()
                except Exception:
                    members = StudentGroupMember.query.join(StudentGroup).filter(
                        StudentGroup.class_id == ga.class_id,
                        StudentGroup.is_active == True
                    ).all()
                student_ids = list({m.student_id for m in members if m.student_id})

                graded_by_id = None
                if ga.class_info and getattr(ga.class_info, 'teacher_id', None):
                    graded_by_id = ga.class_info.teacher_id
                if not graded_by_id:
                    t = TeacherStaff.query.limit(1).first()
                    if t:
                        graded_by_id = t.id
                if not graded_by_id:
                    continue

                for student_id in student_ids:
                    ext = GroupAssignmentExtension.query.filter_by(
                        group_assignment_id=ga.id, student_id=student_id, is_active=True
                    ).first()
                    student_close = to_aware_dt(ext.extended_due_date) if ext and getattr(ext, 'extended_due_date', None) else base_close
                    if not student_close or now <= student_close + auto_zero_grace_days:
                        continue
                    existing = GroupGrade.query.filter_by(
                        group_assignment_id=ga.id, student_id=student_id
                    ).first()
                    if existing:
                        continue
                    grade_data = json.dumps({
                        'score': 0.0, 'points_earned': 0.0, 'total_points': total_points,
                        'max_score': total_points, 'percentage': 0.0, 'letter_grade': 'F',
                        'auto_zero': True
                    })
                    gg = GroupGrade(
                        group_assignment_id=ga.id, group_id=None, student_id=student_id,
                        grade_data=grade_data, graded_by=graded_by_id, comments=None
                    )
                    db.session.add(gg)
            except Exception as e:
                current_app.logger.warning("apply_auto_zeros group assignment %s: %s", getattr(ga, 'id', '?'), e)
                continue

        db.session.commit()
    except Exception as e:
        current_app.logger.exception("apply_auto_zeros_for_past_due_assignments failed")
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
        if percentage >= 93:
            return 4.0
        elif percentage >= 90:
            return 3.67
        elif percentage >= 87:
            return 3.33
        elif percentage >= 83:
            return 3.0
        elif percentage >= 80:
            return 2.67
        elif percentage >= 77:
            return 2.33
        elif percentage >= 73:
            return 2.0
        elif percentage >= 70:
            return 1.67
        elif percentage >= 67:
            return 1.33
        elif percentage >= 63:
            return 1.0
        elif percentage >= 60:
            return 0.67
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



