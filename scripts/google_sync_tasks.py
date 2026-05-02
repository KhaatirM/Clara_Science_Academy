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
from datetime import datetime

# Support running as a script (cwd=scripts) and as an import (cwd=repo root)
try:
    from google_classroom_service import get_google_service, list_classroom_coursework, get_coursework_grades
except ModuleNotFoundError:
    from scripts.google_classroom_service import get_google_service, list_classroom_coursework, get_coursework_grades
from services.google_directory_service import (
    get_google_user,
    move_user_to_ou,
    suspend_user,
    sync_group_members,
    sync_user_groups,
    sync_user_suspension_with_db_is_active,
)
from services.google_ou_policy import resolve_student_ou, school_level_group_for_grade
from utils.student_login_policy import (
    google_workspace_sync_should_skip_student,
    parse_grade_level_for_policy,
)


ELEMENTARY_GROUP_EMAIL = "elementary@clarascienceacademy.org"
MIDDLE_SCHOOL_GROUP_EMAIL = "middle_school@clarascienceacademy.org"
HIGH_SCHOOL_GROUP_EMAIL = "highschool@clarascienceacademy.org"
STUDENT_ASSEMBLY_GROUP_EMAIL = "studentassembly@clarascienceacademy.org"

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


def sync_directory_data():
    """
    Sync Google Workspace Directory state from the database SSOT.

    - Students: compute OU based on grade_level + grad_year (+ alumni/removal rules) and move if needed.
      If marked for removal / inactive, suspend after ~6 months.
    - Classes: for any Class with google_group_email, sync membership to match current roster.
    """
    # --- Student OU + suspension sync ---
    students = (
        db.session.query(Student, User.google_workspace_email)
        .join(User, User.student_id == Student.id)
        .filter(User.google_workspace_email.isnot(None))
        .all()
    )

    moved = 0
    suspended = 0
    ou_skipped = 0

    group_synced_students = 0
    for student, ws_email in students:
        ws_email = (ws_email or "").strip()
        if not ws_email:
            continue

        if google_workspace_sync_should_skip_student(getattr(student, "grade_level", None)):
            gl = parse_grade_level_for_policy(getattr(student, "grade_level", None))
            current_app.logger.info(
                "[INFO] Grade Gate: Skipping %s %s (Grade %s).",
                (getattr(student, "first_name", None) or "").strip(),
                (getattr(student, "last_name", None) or "").strip(),
                gl if gl is not None else "?",
            )
            continue

        sync_user_suspension_with_db_is_active(ws_email, bool(getattr(student, "is_active", True)))

        decision = resolve_student_ou(
            grade_level=getattr(student, "grade_level", None),
            grad_year=getattr(student, "grad_year", None),
            expected_grad_date=getattr(student, "expected_grad_date", None),
            is_active=bool(getattr(student, "is_active", True)),
            marked_for_removal=bool(getattr(student, "marked_for_removal", False)),
            status_updated_at=getattr(student, "status_updated_at", None),
            expected_graduation_year=getattr(student, "expected_graduation_year", None),
        )

        g_user = get_google_user(ws_email)
        if not g_user:
            current_app.logger.warning(f"Directory user not found or unreadable: {ws_email}")
            ou_skipped += 1
            continue

        if not bool(getattr(student, "is_active", True)):
            # DB inactive: suspension already aligned above; skip OU / policy / group churn.
            continue

        current_ou = g_user.get("orgUnitPath")
        is_suspended = bool(g_user.get("suspended", False))

        # Start the 6-month clock the first time we detect removal/inactive without a timestamp
        if decision.reason == "marked_for_removal_or_inactive" and not getattr(student, "status_updated_at", None):
            try:
                student.status_updated_at = datetime.utcnow()
                db.session.commit()
            except Exception:
                db.session.rollback()

        if current_ou != decision.target_ou_path:
            ou_res = move_user_to_ou(ws_email, decision.target_ou_path)
            if ou_res is True:
                moved += 1
            elif ou_res is False:
                current_app.logger.warning(
                    f"Failed to move {ws_email} from {current_ou} to {decision.target_ou_path}"
                )

        if decision.should_suspend_now and not is_suspended:
            if suspend_user(ws_email):
                suspended += 1
            else:
                current_app.logger.warning(f"Failed to suspend {ws_email}")

        # --- School-level + student assembly group membership ---
        # Keep exactly one of Elementary/Middle/High at a time (plus Student Assembly for all actives).
        level_key = school_level_group_for_grade(getattr(student, "grade_level", None))
        level_email = None
        if level_key == "elementary":
            level_email = ELEMENTARY_GROUP_EMAIL
        elif level_key == "middle_school":
            level_email = MIDDLE_SCHOOL_GROUP_EMAIL
        elif level_key == "highschool":
            level_email = HIGH_SCHOOL_GROUP_EMAIL

        desired_groups = []
        if level_email:
            desired_groups.append(level_email)
        desired_groups.append(STUDENT_ASSEMBLY_GROUP_EMAIL)

        # Only enforce for active, non-removed students
        if bool(getattr(student, "is_active", True)) and not bool(getattr(student, "marked_for_removal", False)):
            sg_res = sync_user_groups(ws_email, desired_groups)
            if sg_res is True:
                group_synced_students += 1
            elif sg_res is False:
                current_app.logger.warning(f"Failed to sync school-level groups for {ws_email}")

    current_app.logger.info(
        f"Directory student sync: moved={moved}, suspended={suspended}, skipped={ou_skipped}, group_synced={group_synced_students}"
    )

    # --- Google Group roster sync ---
    group_classes = Class.query.filter(Class.google_group_email.isnot(None)).all()
    group_synced = 0
    for c in group_classes:
        group_email = (c.google_group_email or "").strip()
        if not group_email:
            continue

        roster_rows = (
            db.session.query(User.google_workspace_email)
            .join(Student, Student.id == User.student_id)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .filter(
                Enrollment.class_id == c.id,
                Enrollment.is_active == True,
                Student.is_deleted == False,
                User.google_workspace_email.isnot(None),
            )
            .all()
        )
        roster_emails = [(r[0] or "").strip() for r in roster_rows if r and r[0]]

        if sync_group_members(group_email, roster_emails):
            group_synced += 1
        else:
            current_app.logger.warning(f"Failed to sync group roster for {group_email} (class_id={c.id})")

    current_app.logger.info(f"Directory group sync complete: groups_synced={group_synced}")
    return True

