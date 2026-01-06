"""
Google Synchronization Tasks

Contains the core logic for polling Google Classroom for new assignments and grades
and syncing them back to the Clara Science Academy database.

NOTE: This function needs to be run periodically (e.g., every 15 minutes) 
using a cron job or background scheduler.
"""

from flask import Flask, current_app
from extensions import db
from models import User, Class, Assignment, Enrollment, Grade, Student, SchoolYear, AcademicPeriod
from google_classroom_service import get_google_service, list_classroom_coursework, get_coursework_grades
from datetime import datetime

# --- ACADEMIC PERIOD LOOKUP (Ensure this logic is robust in your app) ---
def get_current_academic_period():
    """Fetches the active school year and current quarter for dating new assignments."""
    try:
        current_year = SchoolYear.query.filter_by(is_active=True).order_by(SchoolYear.start_date.desc()).first()
        if not current_year:
            return None, None
            
        current_quarter = AcademicPeriod.query.filter_by(
            school_year_id=current_year.id, 
            period_type='quarter', 
            is_active=True
        ).order_by(AcademicPeriod.start_date.desc()).first()
        
        return current_year, current_quarter
    except Exception as e:
        current_app.logger.error(f"Failed to retrieve current academic period: {e}")
        return None, None
# ------------------------------------------------------------------------


def sync_google_classroom_data(teacher_user_id):
    """
    Main task to synchronize assignments and grades for a given teacher's linked Google Classrooms.
    
    Args:
        teacher_user_id (int): The ID of the teacher who has connected their Google Account.
    
    Returns:
        bool: True if sync completed successfully, False otherwise
    """
    teacher_user = User.query.get(teacher_user_id)
    if not teacher_user:
        current_app.logger.error(f"Teacher User ID {teacher_user_id} not found for sync.")
        return False

    service = get_google_service(teacher_user)
    if not service:
        current_app.logger.error(f"Could not build Google service for teacher {teacher_user_id}. Sync aborted.")
        return False

    # Get all internal classes linked to ANY Google Classroom by this teacher
    linked_classes = Class.query.filter(
        Class.google_classroom_id.isnot(None),
        Class.teacher_id == teacher_user.teacher_staff_id # Filter to classes assigned to this teacher
    ).all()

    # Group classes by Google Classroom ID (GC ID) to reduce redundant API calls
    gc_id_map = {} # {gc_id: [class_id_1, class_id_2, ...]}
    for class_item in linked_classes:
        gc_id_map.setdefault(class_item.google_classroom_id, []).append(class_item.id)
    
    if not gc_id_map:
        current_app.logger.info(f"No active internal classes linked to Google Classroom IDs for teacher {teacher_user_id}.")
        return True

    current_year, current_quarter = get_current_academic_period()
    if not current_year or not current_quarter:
        # Proceed with a warning, using fallbacks if necessary for compatibility
        current_app.logger.warning("Could not determine current academic period. Using generic fallbacks.")
        
    for gc_id, internal_class_ids in gc_id_map.items():
        # A. SYNC ASSIGNMENTS (Coursework)
        gc_coursework_list = list_classroom_coursework(service, gc_id)
        
        # 1. Identify all Coursework that needs syncing
        assignments_to_sync = [
            cw for cw in gc_coursework_list 
            if cw.get('workType') == 'ASSIGNMENT'
        ]

        for gc_coursework in assignments_to_sync:
            gc_coursework_id = gc_coursework.get('id')
            gc_title = gc_coursework.get('title')
            gc_description = gc_coursework.get('description')
            gc_max_points = gc_coursework.get('maxPoints', 100.0) # Default to 100 if missing
            
            # --- Date Parsing Logic ---
            due_date = None
            if gc_coursework.get('dueDate'):
                try:
                    date_info = gc_coursework['dueDate']
                    time_info = gc_coursework.get('dueTime', {'hours': 23, 'minutes': 59})
                    due_date_str = f"{date_info['year']}-{date_info['month']}-{date_info['day']} {time_info.get('hours', 23)}:{time_info.get('minutes', 59)}:00"
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    current_app.logger.warning(f"Failed to parse due date for GC Coursework {gc_coursework_id}: {e}")
            # --------------------------
            
            # Check for existing assignments linked to this GC Coursework ID
            existing_assignments = Assignment.query.filter_by(google_coursework_id=gc_coursework_id).all()
            existing_class_ids = {a.class_id for a in existing_assignments}

            # Loop through all target internal classes that should have this assignment
            for internal_class_id in internal_class_ids:
                if internal_class_id in existing_class_ids:
                    # Assignment exists: skip creation, ensure latest metadata is synced (optional: implement update logic here)
                    continue 
                
                # Create New Assignment for the internal class (only if it doesn't exist)
                new_assignment = Assignment(
                    title=gc_title,
                    description=gc_description,
                    class_id=internal_class_id,
                    due_date=due_date if due_date else datetime.utcnow(),
                    quarter=current_quarter.name if current_quarter else 'Q1', 
                    academic_period_id=current_quarter.id if current_quarter else None,
                    school_year_id=current_year.id if current_year else None,
                    status='Active',
                    assignment_type='pdf', # As requested: default to 'pdf' for file/paper assignments
                    assignment_context='homework',
                    total_points=float(gc_max_points),
                    created_by=teacher_user_id,
                    google_coursework_id=gc_coursework_id # CRITICAL LINK
                )
                db.session.add(new_assignment)

        # Commit all new assignment creations for this GC to ensure they get an ID for grade sync
        try:
            db.session.commit()
            current_app.logger.info(f"Committed new assignments for GC ID: {gc_id}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to commit assignment creation for GC {gc_id}: {e}")
            continue

        # B. SYNC GRADES (Submissions)
        
        # Re-query all internal assignments now linked to any coursework ID in this GC
        gc_coursework_ids_in_db = [cw.get('id') for cw in assignments_to_sync]
        linked_assignments = Assignment.query.filter(
            Assignment.google_coursework_id.in_(gc_coursework_ids_in_db),
            Assignment.class_id.in_(internal_class_ids)
        ).all()
        
        # Group linked assignments by their GC Coursework ID for efficient grade fetching
        db_assignments_by_gc_id = {}
        for assignment in linked_assignments:
            db_assignments_by_gc_id.setdefault(assignment.google_coursework_id, []).append(assignment)

        for gc_coursework_id, assignments_list in db_assignments_by_gc_id.items():
            
            # 1. Get grades for the coursework from Google
            gc_submissions = get_coursework_grades(service, gc_id, gc_coursework_id)
            
            if not gc_submissions:
                continue

            for internal_assignment in assignments_list:
                
                # 2. Get roster and map of Google Emails to internal Student IDs for the CURRENT CLASS
                # This complex query is the core filtering step.
                class_roster_data = db.session.query(Student.id, User.google_workspace_email).\
                    join(Enrollment, Enrollment.student_id == Student.id).\
                    join(User, User.student_id == Student.id).\
                    filter(
                        Enrollment.class_id == internal_assignment.class_id,
                        Enrollment.is_active == True,
                        User.google_workspace_email.isnot(None)
                    ).all()
                
                # Create a lookup dictionary for fast checking
                roster_email_map = {email: student_id for student_id, email in class_roster_data}

                updates_made = False
                for submission in gc_submissions:
                    student_email = submission.get('userId')
                    assigned_grade = submission.get('assignedGrade')
                    
                    if assigned_grade is None or assigned_grade == -1: # -1 is often 'no grade' in GC
                        continue

                    # 3. CRITICAL FILTER: Only process the grade if the student is in the current internal class roster
                    if student_email in roster_email_map:
                        student_id = roster_email_map[student_email]
                        
                        # Find or Create Grade record
                        internal_grade = Grade.query.filter_by(
                            student_id=student_id,
                            assignment_id=internal_assignment.id
                        ).first()
                        
                        # Grade data includes the score and a flag indicating GC source
                        grade_data = f'{{"score": {assigned_grade}, "gc_source": true, "max_points": {internal_assignment.total_points}}}'
                        
                        if internal_grade:
                            # Update existing grade
                            internal_grade.grade_data = grade_data
                            internal_grade.graded_at = datetime.utcnow()
                        else:
                            # Create new grade
                            new_grade = Grade(
                                student_id=student_id,
                                assignment_id=internal_assignment.id,
                                grade_data=grade_data,
                                graded_at=datetime.utcnow()
                            )
                            db.session.add(new_grade)
                        
                        updates_made = True
                
                # Commit all grades updated/created for this internal assignment
                if updates_made:
                    try:
                        db.session.commit()
                        current_app.logger.info(f"Committed grades for internal assignment {internal_assignment.id} linked to GC Coursework {gc_coursework_id}.")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Failed to commit grades for assignment {internal_assignment.id}: {e}")

    current_app.logger.info(f"Google Classroom sync complete for teacher {teacher_user_id}.")
    return True

