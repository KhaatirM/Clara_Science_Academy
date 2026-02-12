"""
Classes routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import db, Class, TeacherStaff, Student, Enrollment, Assignment, Attendance, Grade, Submission, StudentGroup, StudentGroupMember, GroupAssignment, GroupConflict, GroupGrade, SchoolDayAttendance, SchoolYear, AcademicPeriod
from datetime import datetime
import json


bp = Blueprint('classes', __name__)


def calculate_assignment_graded_status(assignment):
    """Calculate graded status for an assignment - returns dict with graded_count and total_students"""
    # Get enrolled students for this class
    enrolled_count = Enrollment.query.filter_by(
        class_id=assignment.class_id,
        is_active=True
    ).count()
    
    # Get all grades for this assignment
    grades = Grade.query.filter_by(assignment_id=assignment.id).all()
    
    # Count how many are actually graded (have graded_at timestamp)
    graded_count = sum(1 for g in grades if g.graded_at is not None and not g.is_voided)
    
    # Get all submissions for this assignment to count submitted
    submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    submitted_count = len(submissions)
    
    return {
        'graded_count': graded_count,
        'total_students': enrolled_count,
        'submitted_count': submitted_count
    }


def calculate_group_assignment_graded_status(group_assignment):
    """Calculate graded status for a group assignment - returns dict with graded_count and total_students"""
    # Get enrolled students for this class
    enrolled_count = Enrollment.query.filter_by(
        class_id=group_assignment.class_id,
        is_active=True
    ).count()
    
    # Get all group grades for this assignment
    from models import GroupGrade
    group_grades = GroupGrade.query.filter_by(group_assignment_id=group_assignment.id).all()
    
    # Count how many are actually graded (have grade_data and not voided)
    graded_count = sum(1 for g in group_grades if g.grade_data and not g.is_voided)
    
    return {
        'graded_count': graded_count,
        'total_students': enrolled_count,
        'submitted_count': len([g for g in group_grades if g.grade_data])
    }


# ============================================================
# Route: /api/class/<int:class_id>/groups', methods=['GET']
# Function: management_api_class_groups
# ============================================================

@bp.route('/api/class/<int:class_id>/groups', methods=['GET'])
@login_required
@management_required
def management_api_class_groups(class_id):
    """API endpoint to get groups for a class - Management access."""
    try:
        print(f"DEBUG: Management API called for class {class_id}")
        
        # Verify management has access to this class
        class_obj = Class.query.get_or_404(class_id)
        
        # Get groups for this class
        groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
        print(f"DEBUG: Found {len(groups)} groups for class {class_id}")
        
        groups_data = []
        for group in groups:
            groups_data.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'member_count': len(group.members),
                'created_at': group.created_at.isoformat() if group.created_at else None
            })
        
        return jsonify({
            'success': True,
            'groups': groups_data
        })
        
    except Exception as e:
        print(f"Error fetching groups: {e}")
        return jsonify({'success': False, 'message': 'Error fetching groups'}), 500



# ============================================================
# Route: /classes
# Function: classes
# ============================================================

@bp.route('/classes')
@login_required
@management_required
def classes():
    """Enhanced classes management page for Directors and School Administrators."""
    classes = Class.query.all()
    
    # Get unique student count (total students in system, not sum across classes)
    from models import Student
    unique_student_count = Student.query.count()
    
    return render_template('management/enhanced_classes.html', 
                         classes=classes,
                         unique_student_count=unique_student_count,
                         section='classes',
                         active_tab='classes')



# ============================================================
# Route: /add-class', methods=['GET', 'POST']
# Function: add_class
# ============================================================

@bp.route('/add-class', methods=['GET', 'POST'])
@login_required
@management_required
def add_class():
    """Add a new class with enhanced features."""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            subject = request.form.get('subject', '').strip()
            teacher_id = request.form.get('teacher_id', type=int)
            room_number = request.form.get('room_number', '').strip()
            schedule = request.form.get('schedule', '').strip()
            max_students = request.form.get('max_students', 30, type=int)
            description = request.form.get('description', '').strip()
            
            if not name or not subject or not teacher_id:
                flash('Please fill in all required fields.', 'danger')
                return redirect(url_for('management.classes'))
            
            # Get current school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash('Cannot create class: No active school year.', 'danger')
                return redirect(url_for('management.classes'))
            
            # Create new class
            new_class = Class(
                name=name,
                subject=subject,
                teacher_id=teacher_id,
                school_year_id=current_school_year.id,
                room_number=room_number if room_number else None,
                schedule=schedule if schedule else None,
                max_students=max_students,
                description=description if description else None,
                is_active=True
            )
            
            db.session.add(new_class)
            db.session.flush()  # Get the ID for the new class
            
            # Handle grade levels
            grade_level_ids = request.form.getlist('grade_levels')
            if grade_level_ids:
                grade_levels = [int(g) for g in grade_level_ids if g and str(g).isdigit()]
                new_class.set_grade_levels(grade_levels)
            
            # Handle multi-teacher assignments
            # Add substitute teachers
            substitute_teacher_ids = request.form.getlist('substitute_teachers')
            for teacher_id in substitute_teacher_ids:
                if teacher_id:  # Make sure it's not empty
                    teacher = TeacherStaff.query.get(int(teacher_id))
                    if teacher:
                        new_class.substitute_teachers.append(teacher)
            
            # Add additional teachers
            additional_teacher_ids = request.form.getlist('additional_teachers')
            for teacher_id in additional_teacher_ids:
                if teacher_id:  # Make sure it's not empty
                    teacher = TeacherStaff.query.get(int(teacher_id))
                    if teacher:
                        new_class.additional_teachers.append(teacher)
            
            # --- NEW GOOGLE CLASSROOM LOGIC ---
            google_classroom_created = False
            try:
                # Import the Google Classroom service helper
                from google_classroom_service import get_google_service
                
                # 1. Find the primary teacher's User account
                teacher_staff = TeacherStaff.query.get(new_class.teacher_id)
                
                # Try to get the user associated with this teacher
                if teacher_staff and teacher_staff.user:
                    teacher_user = teacher_staff.user
                    
                    if teacher_user and teacher_user.google_refresh_token:
                        # 2. Build the service, authenticated as this teacher
                        service = get_google_service(teacher_user)
                        
                        if service:
                            # 3. Create the Google Classroom
                            course_body = {
                                'name': new_class.name,
                                'ownerId': 'me'  # 'me' = the authenticated teacher
                            }
                            if new_class.description:
                                course_body['description'] = new_class.description
                            if new_class.subject:
                                course_body['section'] = new_class.subject
                            
                            course = service.courses().create(body=course_body).execute()
                            
                            # 4. Save the new Classroom ID to our database
                            new_class.google_classroom_id = course.get('id')
                            google_classroom_created = True
                            current_app.logger.info(f"Successfully created Google Classroom (ID: {course.get('id')}) for class {new_class.id}")
                        else:
                            current_app.logger.warning(f"Failed to build Google service for teacher {teacher_user.id}. The teacher may need to re-connect their account.")
                    else:
                        current_app.logger.info(f"Teacher {teacher_staff.id} has not connected their Google account. Google Classroom was not created.")
                else:
                    current_app.logger.info(f"No user account found for teacher {new_class.teacher_id}. Google Classroom was not created.")
            
            except Exception as e:
                current_app.logger.error(f"Error during automatic classroom creation: {e}")
                # Don't fail the entire class creation if Google Classroom fails
            # --- END OF NEW LOGIC ---
            
            db.session.commit()
            
            # Provide appropriate success message based on whether Google Classroom was created
            if google_classroom_created:
                flash(f'Class "{name}" created successfully and linked to Google Classroom!', 'success')
            else:
                flash(f'Class "{name}" created successfully. Note: Google Classroom was not created. The assigned teacher may need to connect their Google account.', 'info')
            
            return redirect(url_for('management.view_class', class_id=new_class.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating class: {str(e)}', 'danger')
            return redirect(url_for('management.classes'))
    
    # GET request - no standalone page; redirect to classes view (create via modal there)
    return redirect(url_for('management.classes'))



# ============================================================
# Route: /class/<int:class_id>/manage
# Function: manage_class
# ============================================================

@bp.route('/class/<int:class_id>/manage')
@login_required
@management_required
def manage_class(class_id):
    """Manage a specific class - teachers, students, etc."""
    from datetime import date, datetime
    
    class_obj = Class.query.get_or_404(class_id)
    
    # Get all students for potential enrollment
    all_students = Student.query.all()
    
    # Get currently enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    # Get available teachers for assignment
    available_teachers = TeacherStaff.query.filter(TeacherStaff.is_deleted == False).all()
    
    # Get today's date for age calculations
    today = date.today()
    
    return render_template('management/manage_class_roster.html', 
                         class_info=class_obj,
                         all_students=all_students,
                         enrolled_students=enrolled_students,
                         available_teachers=available_teachers,
                         today=today,
                         enrollments=enrollments)



# ============================================================
# Route: /class/<int:class_id>/edit', methods=['GET', 'POST']
# Function: edit_class
# ============================================================

@bp.route('/class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@management_required
def edit_class(class_id):
    """Edit a specific class."""
    class_obj = Class.query.get_or_404(class_id)
    
    if request.method == 'POST':
        try:
            class_obj.name = request.form.get('name', '').strip()
            class_obj.subject = request.form.get('subject', '').strip()
            class_obj.teacher_id = request.form.get('teacher_id', type=int)
            class_obj.room_number = request.form.get('room_number', '').strip() or None
            schedule_text = request.form.get('schedule', '').strip() or None
            class_obj.schedule = schedule_text
            class_obj.max_students = request.form.get('max_students', 30, type=int)
            class_obj.description = request.form.get('description', '').strip() or None
            class_obj.is_active = 'is_active' in request.form
            
            # Handle schedule - Parse and create ClassSchedule records
            from models import ClassSchedule
            from datetime import datetime, time
            
            # Delete existing schedules for this class
            existing_schedules = ClassSchedule.query.filter_by(class_id=class_id).all()
            for schedule in existing_schedules:
                db.session.delete(schedule)
            
            # Parse and create new schedules if schedule text is provided
            if schedule_text:
                # Parse schedule format: "Mon 9:00 AM-10:00 AM, Tue 10:00 AM-11:00 AM"
                # Day abbreviations: Mon, Tue, Wed, Thu, Fri, Sat, Sun
                day_mapping = {
                    'mon': 0, 'monday': 0,
                    'tue': 1, 'tuesday': 1,
                    'wed': 2, 'wednesday': 2,
                    'thu': 3, 'thursday': 3,
                    'fri': 4, 'friday': 4,
                    'sat': 5, 'saturday': 5,
                    'sun': 6, 'sunday': 6
                }
                
                # Split by comma to get individual schedule entries
                schedule_entries = [s.strip() for s in schedule_text.split(',')]
                
                for entry in schedule_entries:
                    if not entry:
                        continue
                    
                    try:
                        # Parse format: "Mon 9:00 AM-10:00 AM" or "Mon 9:00 AM"
                        parts = entry.split()
                        if len(parts) < 2:
                            continue
                        
                        day_str = parts[0].lower()
                        day_of_week = day_mapping.get(day_str)
                        
                        if day_of_week is None:
                            continue
                        
                        # Parse time(s)
                        time_str = ' '.join(parts[1:])  # "9:00 AM-10:00 AM" or "9:00 AM"
                        
                        if '-' in time_str:
                            # Has start and end time
                            start_str, end_str = time_str.split('-', 1)
                            start_str = start_str.strip()
                            end_str = end_str.strip()
                        else:
                            # Only start time, assume 1 hour duration
                            start_str = time_str.strip()
                            # Parse start time and add 1 hour for end time
                            try:
                                start_time_obj = datetime.strptime(start_str, '%I:%M %p').time()
                                from datetime import timedelta
                                start_datetime = datetime.combine(datetime.today(), start_time_obj)
                                end_datetime = start_datetime + timedelta(hours=1)
                                end_str = end_datetime.strftime('%I:%M %p')
                            except:
                                continue
                        
                        # Parse time strings to time objects
                        try:
                            start_time = datetime.strptime(start_str, '%I:%M %p').time()
                            end_time = datetime.strptime(end_str, '%I:%M %p').time()
                            
                            # Create ClassSchedule record
                            schedule = ClassSchedule(
                                class_id=class_id,
                                day_of_week=day_of_week,
                                start_time=start_time,
                                end_time=end_time,
                                room=class_obj.room_number
                            )
                            db.session.add(schedule)
                        except ValueError as e:
                            # Skip invalid time format
                            current_app.logger.warning(f"Invalid time format in schedule entry '{entry}': {e}")
                            continue
                    except Exception as e:
                        # Skip entries that can't be parsed
                        current_app.logger.warning(f"Error parsing schedule entry '{entry}': {e}")
                        continue
            
            # Handle grade levels
            grade_level_ids = request.form.getlist('grade_levels')
            if grade_level_ids:
                grade_levels = [int(g) for g in grade_level_ids if g and str(g).isdigit()]
                class_obj.set_grade_levels(grade_levels)
            else:
                class_obj.set_grade_levels([])
            
            # Handle multi-teacher assignments
            # Clear existing relationships (proper way for dynamic relationships)
            class_obj.substitute_teachers = []
            class_obj.additional_teachers = []
            
            # Add substitute teachers
            substitute_teacher_ids = request.form.getlist('substitute_teachers')
            for teacher_id in substitute_teacher_ids:
                if teacher_id:  # Make sure it's not empty
                    teacher = TeacherStaff.query.get(int(teacher_id))
                    if teacher:
                        class_obj.substitute_teachers.append(teacher)
            
            # Add additional teachers
            additional_teacher_ids = request.form.getlist('additional_teachers')
            for teacher_id in additional_teacher_ids:
                if teacher_id:  # Make sure it's not empty
                    teacher = TeacherStaff.query.get(int(teacher_id))
                    if teacher:
                        class_obj.additional_teachers.append(teacher)
            
            db.session.commit()
            flash(f'Class "{class_obj.name}" updated successfully!', 'success')
            return redirect(url_for('management.classes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating class: {str(e)}', 'danger')
            return redirect(url_for('management.edit_class', class_id=class_id))
    
    # GET request - show edit form
    teachers = TeacherStaff.query.filter(TeacherStaff.is_deleted == False).all()
    return render_template('management/edit_class.html', class_info=class_obj, available_teachers=teachers)



# ============================================================
# Route: /class/<int:class_id>/roster', methods=['GET', 'POST']
# Function: class_roster
# ============================================================

@bp.route('/class/<int:class_id>/roster', methods=['GET', 'POST'])
@login_required
@management_required
def class_roster(class_id):
    """View and manage class roster."""
    from datetime import date, datetime
    
    class_obj = Class.query.get_or_404(class_id)
    
    # Handle POST requests for roster management
    if request.method == 'POST':
        try:
            # Handle student enrollment/removal
            action = request.form.get('action')
            
            if action == 'add':
                student_ids = request.form.getlist('student_id')
                if student_ids:
                    added_count = 0
                    for student_id in student_ids:
                        student_id = int(student_id)
                        # Check if student is already enrolled
                        existing_enrollment = Enrollment.query.filter_by(
                            class_id=class_id, student_id=student_id, is_active=True
                        ).first()
                        
                        if not existing_enrollment:
                            # Add student to class
                            enrollment = Enrollment(
                                student_id=student_id,
                                class_id=class_id,
                                is_active=True
                            )
                            db.session.add(enrollment)
                            added_count += 1
                    
                    if added_count > 0:
                        db.session.commit()
                        # Automatically void assignments for late-enrolling students
                        from management_routes.late_enrollment_utils import void_assignments_for_late_enrollment
                        for student_id in student_ids:
                            voided_count = void_assignments_for_late_enrollment(int(student_id), class_id)
                            if voided_count > 0:
                                print(f"Automatically voided {voided_count} assignment(s) for student {student_id} due to late enrollment")
                        flash(f'{added_count} student(s) added to class successfully!', 'success')
                    else:
                        flash('Selected students are already enrolled in this class.', 'warning')
                else:
                    flash('Please select at least one student to add.', 'warning')
                        
            elif action == 'remove':
                student_id = request.form.get('student_id', type=int)
                if student_id:
                    # Deactivate enrollment instead of deleting
                    enrollment = Enrollment.query.filter_by(
                        class_id=class_id, student_id=student_id, is_active=True
                    ).first()
                    
                    if enrollment:
                        enrollment.is_active = False
                        db.session.commit()
                        flash('Student removed from class successfully!', 'success')
                    else:
                        flash('Student not found in this class.', 'warning')
            
            return redirect(url_for('management.class_roster', class_id=class_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating roster: {str(e)}', 'danger')
            return redirect(url_for('management.class_roster', class_id=class_id))
    
    # Get all students for potential enrollment
    all_students = Student.query.all()
    
    # Get currently enrolled students (ACTIVE enrollments only)
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = []
    for enrollment in enrollments:
        student = Student.query.get(enrollment.student_id)
        if student:
            # Convert dob string to date object for age calculation
            if isinstance(student.dob, str):
                try:
                    student.dob = datetime.strptime(student.dob, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        student.dob = datetime.strptime(student.dob, '%m/%d/%Y').date()
                    except ValueError:
                        student.dob = None
            enrolled_students.append(student)
    
    # Get available teachers for assignment
    available_teachers = TeacherStaff.query.filter(TeacherStaff.is_deleted == False).all()
    
    # Get today's date for age calculations
    today = date.today()
    
    return render_template('management/manage_class_roster.html', 
                         class_info=class_obj,
                         all_students=all_students,
                         enrolled_students=enrolled_students,
                         available_teachers=available_teachers,
                         today=today,
                         enrollments=enrollments)


# ============================================================================
# GOOGLE CLASSROOM INTEGRATION FOR MANAGEMENT
# ============================================================================



# ============================================================
# Route: /class/<int:class_id>/create-google-classroom
# Function: create_and_link_classroom
# ============================================================

@bp.route('/class/<int:class_id>/create-google-classroom')
@login_required
@management_required
def create_and_link_classroom(class_id):
    """
    CREATE A NEW GOOGLE CLASSROOM AND LINK IT (Management Version)
    Creates a brand new Google Classroom and links it to the existing class in the system.
    """
    class_to_link = Class.query.get_or_404(class_id)
    
    # Check if admin has connected their Google account
    if not current_user.google_refresh_token:
        flash("You must connect your Google account first.", "warning")
        return redirect(url_for('teacher.settings'))
    
    try:
        from google_classroom_service import get_google_service
        
        service = get_google_service(current_user)
        if not service:
            flash("Could not connect to Google. Please try reconnecting your account.", "danger")
            return redirect(url_for('management.classes'))
        
        # Create the course in Google Classroom
        course = {
            'name': class_to_link.name,
            'section': class_to_link.subject or '',
            'descriptionHeading': f'Class: {class_to_link.name}',
            'description': class_to_link.description or f'Welcome to {class_to_link.name}',
            'room': class_to_link.room_number or '',
            'ownerId': 'me',
            'courseState': 'ACTIVE'
        }
        
        created_course = service.courses().create(body=course).execute()
        
        # Save the Google Classroom ID to our database
        class_to_link.google_classroom_id = created_course.get('id')
        db.session.commit()
        
        flash(f"Successfully created and linked Google Classroom for {class_to_link.name}!", "success")
        return redirect(url_for('management.classes'))
        
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        
        # Check for database constraint errors
        if "UniqueViolation" in error_message or "duplicate key" in error_message or "uq_class_google_classroom_id" in error_message:
            flash(f"Error: A database constraint error occurred. Please ensure the 'uq_class_google_classroom_id' constraint has been dropped from your database.", 'danger')
            current_app.logger.error(f"UniqueViolation during Google Classroom creation: {error_message}")
        else:
            current_app.logger.error(f"Error creating Google Classroom: {e}")
            flash(f"An error occurred while creating the Google Classroom: {str(e)}", "danger")
        return redirect(url_for('management.classes'))




# ============================================================
# Route: /class/<int:class_id>/link-existing-google-classroom
# Function: link_existing_classroom
# ============================================================

@bp.route('/class/<int:class_id>/link-existing-google-classroom')
@login_required
@management_required
def link_existing_classroom(class_id):
    """
    SHOW THE LIST OF EXISTING GOOGLE CLASSROOMS (Management Version)
    Displays a list of the admin's existing Google Classrooms that can be linked.
    """
    class_to_link = Class.query.get_or_404(class_id)
    
    # Check if admin has connected their account
    if not current_user.google_refresh_token:
        flash("You must connect your Google account first to see your existing classes.", "warning")
        return redirect(url_for('teacher.settings'))
    
    try:
        from google_classroom_service import get_google_service
        
        service = get_google_service(current_user)
        if not service:
            flash("Could not connect to Google. Please try reconnecting your account.", "danger")
            return redirect(url_for('management.classes'))
        
        # Fetch all courses that the current user (admin) teaches
        results = service.courses().list(teacherId='me', courseStates=['ACTIVE']).execute()
        google_classrooms = results.get('courses', [])
        
        if not google_classrooms:
            flash("You don't have any active Google Classrooms to link. Try creating a new one instead.", "info")
            return redirect(url_for('management.classes'))
        
        return render_template('management/link_existing_google_classroom.html',
                             class_to_link=class_to_link,
                             google_classrooms=google_classrooms)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching Google Classrooms: {e}")
        flash(f"An error occurred while fetching Google Classrooms: {str(e)}", "danger")
        return redirect(url_for('management.classes'))




# ============================================================
# Route: /class/<int:class_id>/confirm-link-classroom/<google_classroom_id>', methods=['POST']
# Function: confirm_link_classroom
# ============================================================

@bp.route('/class/<int:class_id>/confirm-link-classroom/<google_classroom_id>', methods=['POST'])
@login_required
@management_required
def confirm_link_classroom(class_id, google_classroom_id):
    """
    LINK THE SELECTED GOOGLE CLASSROOM (Management Version)
    Links a selected existing Google Classroom to the class in our system.
    Added 'Teacher' permission check - teachers can link their own classes.
    """
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    class_to_link = Class.query.get_or_404(class_id)
    
    # Permission check (expanded to check if user is the primary teacher)
    if current_user.role not in ['Director', 'School Administrator', 'Tech Support']:
        if current_user.teacher_staff_id != class_to_link.teacher_id:
            flash("Permission denied. Only the primary teacher or an administrator can manage this classroom link.", 'danger')
            return redirect(url_for('management.classes'))

    # Update the class with the new Google Classroom ID
    class_to_link.google_classroom_id = google_classroom_id

    try:
        db.session.commit()  # This line caused the error before the SQL fix
        flash(f"Successfully linked {class_to_link.name} to Google Classroom ID {google_classroom_id}.", 'success')
        return redirect(url_for('management.classes'))
    
    except Exception as e:
        db.session.rollback()
        
        # Check for the specific UniqueViolation error from PostgreSQL
        error_message = str(e)
        if "UniqueViolation" in error_message or "duplicate key" in error_message or "uq_class_google_classroom_id" in error_message:
            flash(f"Error: Google Classroom ID {google_classroom_id} is already linked to another class in the system. The linking function has been fixed to allow this, but a unique constraint remains in your database. Please re-run the necessary SQL command to drop the 'uq_class_google_classroom_id' constraint.", 'danger')
            current_app.logger.error(f"UniqueViolation during class linking: {error_message}")
        else:
            flash(f"An unexpected database error occurred while linking the class. Please check logs.", 'danger')
            current_app.logger.error(f"Unexpected error during class linking: {e}")

        return redirect(url_for('management.classes'))




# ============================================================
# Route: /class/<int:class_id>/unlink-google-classroom
# Function: unlink_classroom
# ============================================================

@bp.route('/class/<int:class_id>/unlink-google-classroom')
@login_required
@management_required
def unlink_classroom(class_id):
    """
    UNLINK ROUTE (Management Version): Remove the Google Classroom link from the class.
    Note: This doesn't delete the Google Classroom, just removes the link in our system.
    """
    class_to_unlink = Class.query.get_or_404(class_id)
    
    if not class_to_unlink.google_classroom_id:
        flash("This class is not linked to a Google Classroom.", "info")
        return redirect(url_for('management.classes'))
    
    class_to_unlink.google_classroom_id = None
    db.session.commit()
    
    flash("Successfully unlinked from Google Classroom. The course still exists in your Google account.", "info")
    return redirect(url_for('management.classes'))


# ============================================================================
# CLASS MANAGEMENT FEATURES (Group Assignments, Deadline Reminders, etc.)
# ============================================================================



# ============================================================
# Route: /class/<int:class_id>/group-assignments
# Function: admin_class_group_assignments
# ============================================================

@bp.route('/class/<int:class_id>/group-assignments')
@login_required
@management_required
def admin_class_group_assignments(class_id):
    """View all group assignments for a specific class - Management view."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Get all group assignments for this class
    try:
        group_assignments = GroupAssignment.query.filter_by(class_id=class_id).order_by(GroupAssignment.due_date.desc()).all()
    except Exception as e:
        flash('Group assignments feature is not yet available.', 'warning')
        group_assignments = []
    
    # Calculate graded status for each assignment
    for assignment in group_assignments:
        # Check if assignment has any grades
        group_grades = GroupGrade.query.filter_by(group_assignment_id=assignment.id, is_voided=False).all()
        
        if group_grades and len(group_grades) > 0:
            # Has grades - check if it's fully graded or partially graded
            # For now, if it has any grades, we'll consider it "Graded"
            # You can refine this logic later to check if all groups are graded
            assignment.graded_status = 'Graded'
        else:
            # No grades - check assignment status
            if assignment.status == 'Inactive':
                assignment.graded_status = 'Inactive'
            else:
                assignment.graded_status = 'Active'
    
    return render_template('management/admin_class_group_assignments.html',
                         class_obj=class_obj,
                         group_assignments=group_assignments,
                         moment=datetime.utcnow())




# ============================================================
# Route: /class/<int:class_id>/deadline-reminders
# Function: admin_class_deadline_reminders
# ============================================================

@bp.route('/class/<int:class_id>/deadline-reminders')
@login_required
@management_required
def admin_class_deadline_reminders(class_id):
    """View deadline reminders for a specific class - Management view."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Get all deadline reminders for this class
    try:
        from datetime import timedelta
        from models import DeadlineReminder
        from sqlalchemy import text
        
        # Try normal query first
        try:
            reminders = DeadlineReminder.query.filter_by(class_id=class_id).order_by(DeadlineReminder.reminder_date.asc()).all()
        except Exception as db_error:
            # If selected_student_ids column doesn't exist, use raw SQL
            error_str = str(db_error).lower()
            if 'selected_student_ids' in error_str or 'no such column' in error_str:
                try:
                    result = db.session.execute(
                        text("""
                            SELECT id, assignment_id, group_assignment_id, class_id, reminder_type, 
                                   reminder_title, reminder_message, reminder_date, reminder_frequency, 
                                   is_active, created_by, created_at, last_sent, next_send
                            FROM deadline_reminder 
                            WHERE class_id = :class_id 
                            ORDER BY reminder_date ASC
                        """),
                        {'class_id': class_id}
                    )
                    # Create simple reminder objects from results
                    reminders = []
                    for row in result:
                        # Create a simple object that mimics DeadlineReminder
                        class SimpleReminder:
                            def __init__(self, row_data):
                                for key, value in row_data.items():
                                    setattr(self, key, value)
                        reminders.append(SimpleReminder(dict(row._mapping)))
                except Exception as sql_error:
                    print(f"Error with raw SQL query: {sql_error}")
                    reminders = []
            else:
                raise db_error
        
        # Get upcoming reminders (next 7 days)
        now = datetime.now()
        upcoming_date = now + timedelta(days=7)
        upcoming_reminders = []
        for r in reminders:
            if hasattr(r, 'reminder_date') and r.reminder_date:
                try:
                    if now <= r.reminder_date <= upcoming_date:
                        upcoming_reminders.append(r)
                except:
                    pass
    except Exception as e:
        print(f"Error loading deadline reminders: {e}")
        import traceback
        traceback.print_exc()
        flash('Deadline reminders feature is not yet available.', 'warning')
        reminders = []
        upcoming_reminders = []
    
    return render_template('management/admin_class_deadline_reminders.html',
                         class_obj=class_obj,
                         reminders=reminders,
                         upcoming_reminders=upcoming_reminders,
                         admin_view=True)




# ============================================================
# Route: /class/<int:class_id>/analytics
# Function: admin_class_analytics
# ============================================================

@bp.route('/class/<int:class_id>/analytics')
@login_required
@management_required
def admin_class_analytics(class_id):
    """View analytics for a specific class - Management view."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Get analytics data
    try:
        groups = StudentGroup.query.filter_by(class_id=class_id).all()
        try:
            group_assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
        except Exception as e:
            current_app.logger.error(f"Error loading group assignments: {str(e)}")
            group_assignments = []
        collaboration_metrics = []
        benchmarks = []
    except Exception as e:
        groups = []
        group_assignments = []
        collaboration_metrics = []
        benchmarks = []
    
    return render_template('management/admin_class_analytics.html',
                         class_obj=class_obj,
                         groups=groups,
                         group_assignments=group_assignments,
                         collaboration_metrics=collaboration_metrics,
                         benchmarks=benchmarks)




# ============================================================
# Route: /class/<int:class_id>/360-feedback
# Function: admin_class_360_feedback
# ============================================================

@bp.route('/class/<int:class_id>/360-feedback')
@login_required
@management_required
def admin_class_360_feedback(class_id):
    """View 360 feedback for a specific class - Management view."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Get feedback sessions
    try:
        feedback_sessions = Feedback360.query.filter_by(class_id=class_id).order_by(Feedback360.created_at.desc()).all()
    except Exception as e:
        feedback_sessions = []
    
    return render_template('management/admin_class_360_feedback.html',
                         class_obj=class_obj,
                         feedback_sessions=feedback_sessions)




# ============================================================
# Route: /class/<int:class_id>/reflection-journals
# Function: admin_class_reflection_journals
# ============================================================

@bp.route('/class/<int:class_id>/reflection-journals')
@login_required
@management_required
def admin_class_reflection_journals(class_id):
    """View reflection journals for a specific class - Management view."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Get reflection journals
    try:
        journals = ReflectionJournal.query.filter_by(class_id=class_id).order_by(ReflectionJournal.created_at.desc()).all()
    except Exception as e:
        journals = []
    
    return render_template('management/admin_class_reflection_journals.html',
                         class_obj=class_obj,
                         journals=journals)




# ============================================================
# Route: /class/<int:class_id>/conflicts
# Function: admin_class_conflicts
# ============================================================

@bp.route('/class/<int:class_id>/conflicts')
@login_required
@management_required
def admin_class_conflicts(class_id):
    """View conflicts for a specific class - Management view."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Get conflicts - GroupConflict doesn't have class_id, so we need to get it through groups
    try:
        # Get all groups for this class
        groups = StudentGroup.query.filter_by(class_id=class_id).all()
        group_ids = [group.id for group in groups]
        
        # Get conflicts for these groups
        if group_ids:
            conflicts = GroupConflict.query.filter(GroupConflict.group_id.in_(group_ids)).order_by(GroupConflict.reported_at.desc()).all()
        else:
            conflicts = []
    except Exception as e:
        print(f"Error loading conflicts: {e}")
        conflicts = []
    
    return render_template('management/admin_class_conflicts.html',
                         class_obj=class_obj,
                         conflicts=conflicts)




# ============================================================
# Route: /class/<int:class_id>/grades
# Function: class_grades
# ============================================================

@bp.route('/class/<int:class_id>/grades')
@login_required
@management_required
def class_grades(class_id):
    """View class grades."""
    from datetime import date
    import json
    
    class_obj = Class.query.get_or_404(class_id)
    
    # Get view mode (table or student_cards)
    view_mode = request.args.get('view', 'table')
    
    # Get enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    # Get individual assignments for this class (exclude voided assignments from grade calculations)
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    
    # Get group assignments for this class (exclude voided assignments from grade calculations)
    try:
        group_assignments = GroupAssignment.query.filter_by(class_id=class_id).order_by(GroupAssignment.due_date.desc()).all()
    except Exception as e:
        current_app.logger.warning(f"Error loading group assignments: {e}")
        group_assignments = []
    
    # Combine both types of assignments for total count with type indicators
    all_assignments = []
    for assignment in assignments:
        assignment.type = 'individual'
        all_assignments.append(assignment)
    for group_assignment in group_assignments:
        group_assignment.type = 'group'
        all_assignments.append(group_assignment)
    
    # Get grades for enrolled students (individual assignments)
    student_grades = {}
    for student in enrolled_students:
        student_grades[student.id] = {}
        for assignment in assignments:
            # Skip voided assignments - they should not be included in grade calculations
            if assignment.status == 'Voided':
                continue
                
            grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()
            if grade:
                try:
                    grade_data = json.loads(grade.grade_data)
                    # Get points earned from grade_data (support both 'points_earned' and 'score' for backward compatibility)
                    points_earned = grade_data.get('points_earned') or grade_data.get('score')
                    # Always use assignment's total_points as source of truth
                    total_points = assignment.total_points if assignment.total_points else 100.0
                    
                    # Calculate percentage from points
                    if points_earned is not None:
                        try:
                            points_float = float(points_earned)
                            percentage = (points_float / total_points * 100) if total_points > 0 else 0
                            # Store percentage for display (rounded to 1 decimal place)
                            display_grade = round(percentage, 1)
                        except (ValueError, TypeError):
                            display_grade = 'N/A'
                    else:
                        display_grade = 'N/A'
                    
                    student_grades[student.id][assignment.id] = {
                        'grade': display_grade,
                        'comments': grade_data.get('comments', ''),
                        'graded_at': grade.graded_at,
                        'type': 'individual',
                        'is_voided': grade.is_voided if hasattr(grade, 'is_voided') else False,
                        'assignment_voided': False  # Assignment is not voided (we skip voided ones above)
                    }
                except (json.JSONDecodeError, TypeError):
                    student_grades[student.id][assignment.id] = {
                        'grade': 'N/A',
                        'comments': 'Error parsing grade data',
                        'graded_at': grade.graded_at,
                        'type': 'individual',
                        'is_voided': grade.is_voided if hasattr(grade, 'is_voided') else False,
                        'assignment_voided': False
                    }
            else:
                student_grades[student.id][assignment.id] = {
                    'grade': 'Not Graded',
                    'comments': '',
                    'graded_at': None,
                    'is_voided': False,
                    'type': 'individual',
                    'assignment_voided': False
                }
    
    # Get group grades for students (group assignments)
    
    for student in enrolled_students:
        for group_assignment in group_assignments:
            # Skip voided group assignments - they should not be included in grade calculations
            if group_assignment.status == 'Voided':
                continue
                
            # Check if this group assignment is for specific groups
            # selected_group_ids is a JSON string of group IDs (null = all groups)
            assignment_group_ids = []
            if group_assignment.selected_group_ids:
                try:
                    raw_group_ids = json.loads(group_assignment.selected_group_ids)
                    # Convert all group IDs to integers to handle string/integer mismatch
                    assignment_group_ids = [int(gid) for gid in raw_group_ids]
                except (json.JSONDecodeError, TypeError, ValueError):
                    assignment_group_ids = []
            
            # Find what group this student is in for this class
            # If assignment targets specific groups, only consider those groups
            # This prevents conflicts when students are in multiple groups
            should_show_assignment = False
            student_group_id = None
            student_group_name = 'N/A'
            
            if not assignment_group_ids:
                # Assignment is for all groups - get any group the student is in
                student_group_member = StudentGroupMember.query.join(StudentGroup).filter(
                    StudentGroup.class_id == class_id,
                    StudentGroupMember.student_id == student.id
                ).order_by(StudentGroupMember.id.desc()).first()
                
                if student_group_member and student_group_member.group:
                    student_group_id = student_group_member.group.id
                    student_group_name = student_group_member.group.name
                    should_show_assignment = True
            else:
                # Assignment is for specific groups - only check if student is in one of those groups
                student_group_member = StudentGroupMember.query.join(StudentGroup).filter(
                    StudentGroup.class_id == class_id,
                    StudentGroupMember.student_id == student.id,
                    StudentGroup.id.in_(assignment_group_ids)
                ).order_by(StudentGroupMember.id.desc()).first()
                
                if student_group_member and student_group_member.group:
                    student_group_id = student_group_member.group.id
                    student_group_name = student_group_member.group.name
                    should_show_assignment = True
            
            if should_show_assignment:
                # Student should see this assignment
                if student_group_id:
                    # Check if this student has a grade for this assignment
                    # GroupGrade records are stored per student, so we look by student_id
                    group_grade = GroupGrade.query.filter_by(
                        student_id=student.id,
                        group_assignment_id=group_assignment.id
                    ).first()
                    
                    if group_grade:
                        try:
                            grade_data = json.loads(group_grade.grade_data) if group_grade.grade_data else {}
                            # Get points earned from grade_data (support both 'points_earned' and 'score' for backward compatibility)
                            points_earned = grade_data.get('points_earned') or grade_data.get('score')
                            # Always use group_assignment's total_points as source of truth
                            total_points = group_assignment.total_points if group_assignment.total_points else 100.0
                            
                            # Calculate percentage from points
                            if points_earned is not None:
                                try:
                                    points_float = float(points_earned)
                                    percentage = (points_float / total_points * 100) if total_points > 0 else 0
                                    # Store percentage for display (rounded to 1 decimal place)
                                    display_grade = round(percentage, 1)
                                except (ValueError, TypeError):
                                    display_grade = 'N/A'
                            else:
                                display_grade = 'N/A'
                            
                            student_grades[student.id][f'group_{group_assignment.id}'] = {
                                'grade': display_grade,
                                'comments': grade_data.get('comments', ''),
                                'graded_at': group_grade.graded_at,
                                'type': 'group',
                                'group_name': student_group_name,
                                'is_voided': group_grade.is_voided if hasattr(group_grade, 'is_voided') else False,
                                'assignment_voided': False  # Assignment is not voided (we skip voided ones above)
                            }
                        except (json.JSONDecodeError, TypeError, AttributeError):
                            student_grades[student.id][f'group_{group_assignment.id}'] = {
                                'grade': 'N/A',
                                'comments': 'Error parsing grade data',
                                'graded_at': None,
                                'type': 'group',
                                'group_name': student_group_name,
                                'is_voided': group_grade.is_voided if hasattr(group_grade, 'is_voided') else False,
                                'assignment_voided': False
                            }
                    else:
                        student_grades[student.id][f'group_{group_assignment.id}'] = {
                            'grade': 'Not Graded',
                            'comments': '',
                            'graded_at': None,
                            'type': 'group',
                            'group_name': student_group_name,
                            'is_voided': False,
                            'assignment_voided': False
                        }
                else:
                    # Student is not in any group but assignment is for all groups
                    student_grades[student.id][f'group_{group_assignment.id}'] = {
                        'grade': 'No Group',
                        'comments': 'Student not assigned to a group',
                        'graded_at': None,
                        'type': 'group',
                        'group_name': 'N/A',
                        'is_voided': False,
                        'assignment_voided': False
                    }
            else:
                # Student should not see this assignment (not in the assigned group)
                # Only show this assignment if it's for all groups (assignment_group_ids is empty)
                if not assignment_group_ids:
                    # Assignment is for all groups but student is not in any group
                    student_grades[student.id][f'group_{group_assignment.id}'] = {
                        'grade': 'No Group',
                        'comments': 'Student not assigned to a group',
                        'graded_at': None,
                        'is_voided': False,
                        'type': 'group',
                        'group_name': 'N/A',
                        'assignment_voided': False
                    }
                else:
                    # Assignment is for specific groups and student is not in any of them
                    # Show "Not Assigned" to indicate this assignment doesn't apply to this student
                    student_grades[student.id][f'group_{group_assignment.id}'] = {
                        'grade': 'Not Assigned',
                        'comments': 'Not assigned to this group',
                        'graded_at': None,
                        'type': 'group',
                        'group_name': 'N/A',
                        'assignment_voided': False
                    }
    
    # Calculate averages for each student (including both individual and group assignments)
    # Only include grades that are applicable to the student (exclude N/A, Not Assigned from group assignments they're not part of)
    # IMPORTANT: Exclude voided grades AND voided assignments from average calculation
    # This matches the logic used in the student dashboard grades view
    student_averages = {}
    for student_id, grades in student_grades.items():
        # Filter out non-applicable grades (N/A, Not Assigned, Not Graded, No Group) and only include numeric grades
        # ALSO exclude voided grades AND voided assignments
        valid_grades = []
        for g in grades.values():
            grade_val = g['grade']
            # Skip voided grades - CRITICAL FIX
            if g.get('is_voided', False):
                continue
            # Skip voided assignments - CRITICAL FIX to match student dashboard behavior
            if g.get('assignment_voided', False):
                continue
            # Skip if the comment indicates the student isn't part of this assignment
            if 'Not assigned to this group' in g.get('comments', ''):
                continue
            # Only include numeric grades
            if grade_val not in ['N/A', 'Not Assigned', 'Not Graded', 'No Group']:
                try:
                    valid_grades.append(float(grade_val))
                except (ValueError, TypeError):
                    pass
        
        if valid_grades:
            student_averages[student_id] = round(sum(valid_grades) / len(valid_grades), 2)
        else:
            student_averages[student_id] = 'N/A'
    
    # For student card view, get recent assignments (last 3)
    if view_mode == 'student_cards':
        recent_assignments_count = 3
        all_assignments_sorted = sorted(all_assignments, key=lambda x: x.due_date if x.due_date else date.min, reverse=True)
        recent_assignments = all_assignments_sorted[:recent_assignments_count]
    else:
        recent_assignments = []
    
    return render_template('management/class_grades.html', 
                         class_info=class_obj,
                         enrolled_students=enrolled_students,
                         assignments=assignments,
                         group_assignments=group_assignments,
                         all_assignments=all_assignments,
                         student_grades=student_grades,
                         student_averages=student_averages,
                         today=date.today(),
                         view_mode=view_mode,
                         recent_assignments=recent_assignments)



# ============================================================
# Route: /class/<int:class_id>/remove', methods=['POST']
# Function: remove_class
# ============================================================

@bp.route('/class/<int:class_id>/remove', methods=['POST'])
@login_required
@management_required
def remove_class(class_id):
    """Remove a class."""
    class_obj = Class.query.get_or_404(class_id)
    
    try:
        class_name = class_obj.name
        
        # First, delete all enrollments associated with this class
        from models import Enrollment
        enrollments = Enrollment.query.filter_by(class_id=class_id).all()
        for enrollment in enrollments:
            db.session.delete(enrollment)
        
        # Delete all student goals associated with this class
        from models import StudentGoal
        student_goals = StudentGoal.query.filter_by(class_id=class_id).all()
        for goal in student_goals:
            db.session.delete(goal)
        
        # Delete all class schedules associated with this class
        from models import ClassSchedule
        schedules = ClassSchedule.query.filter_by(class_id=class_id).all()
        for schedule in schedules:
            db.session.delete(schedule)
        
        # Delete all attendance records associated with this class
        from models import Attendance
        attendance_records = Attendance.query.filter_by(class_id=class_id).all()
        for attendance in attendance_records:
            db.session.delete(attendance)
        
        # Delete all assignment-related data for this class
        from models import Grade, Assignment, Submission, QuizQuestion, QuizProgress, DiscussionThread, AssignmentExtension
        assignments = Assignment.query.filter_by(class_id=class_id).all()
        for assignment in assignments:
            # Delete all grades for this assignment
            grades = Grade.query.filter_by(assignment_id=assignment.id).all()
            for grade in grades:
                db.session.delete(grade)
            
            # Delete all assignment submissions
            submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
            for submission in submissions:
                db.session.delete(submission)
            
            # Delete all quiz questions
            quiz_questions = QuizQuestion.query.filter_by(assignment_id=assignment.id).all()
            for question in quiz_questions:
                db.session.delete(question)
            
            # Delete all quiz progress
            quiz_progress = QuizProgress.query.filter_by(assignment_id=assignment.id).all()
            for progress in quiz_progress:
                db.session.delete(progress)
            
            # Delete all discussion threads
            discussion_threads = DiscussionThread.query.filter_by(assignment_id=assignment.id).all()
            for thread in discussion_threads:
                db.session.delete(thread)
            
            # Delete all assignment extensions
            extensions = AssignmentExtension.query.filter_by(assignment_id=assignment.id).all()
            for extension in extensions:
                db.session.delete(extension)
            
            # Then delete the assignment
            db.session.delete(assignment)
        
        # Finally, delete the class itself
        db.session.delete(class_obj)
        db.session.commit()
        flash(f'Class "{class_name}" and all associated data removed successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing class: {str(e)}', 'danger')
    
    return redirect(url_for('management.classes'))



# ============================================================
# Route: /assignments/class/<int:class_id>
# Function: class_assignments
# ============================================================

@bp.route('/assignments/class/<int:class_id>')
@login_required
@management_required
def class_assignments(class_id):
    """View assignments for a specific class"""
    from datetime import datetime
    import json
    
    # Get the class
    class_obj = Class.query.get_or_404(class_id)
    
    # Get assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    
    # Get current date for status updates
    today = datetime.now().date()
    
    # Update assignment statuses
    update_assignment_statuses()
    
    # Get teacher_staff_id for template use
    teacher_staff_id = None
    if current_user.role == 'School Administrator':
        if current_user.teacher_staff_id:
            teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
            if teacher_staff:
                teacher_staff_id = teacher_staff.id
    
    return render_template('management/class_assignments_detail.html',
                         class_obj=class_obj,
                         assignments=assignments,
                         teacher_staff_id=teacher_staff_id,
                         today=today,
                         active_tab='assignments')



# ============================================================
# Route: /attendance/take/<int:class_id>', methods=['GET', 'POST']
# Function: take_class_attendance
# ============================================================

@bp.route('/attendance/take/<int:class_id>', methods=['GET', 'POST'])
@login_required
@management_required
def take_class_attendance(class_id):
    """Take attendance for a specific class (management view)"""
    try:
        from datetime import datetime
        
        class_obj = Class.query.get_or_404(class_id)
        
        # Check if class is active (has an active school year)
        if not hasattr(class_obj, 'school_year_id') or not class_obj.school_year_id:
            flash("This class is not associated with an active school year.", "warning")
            return redirect(url_for('management.classes'))
        
        # Check if class is archived or inactive
        if hasattr(class_obj, 'is_active') and not class_obj.is_active:
            flash("This class is archived or inactive. Cannot take attendance.", "warning")
            return redirect(url_for('management.classes'))

        # Get only students enrolled in this specific class
        enrolled_students = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_id,
            Enrollment.is_active == True
        ).order_by(Student.last_name, Student.first_name).all()
        
        if not enrolled_students:
            flash("No students are currently enrolled in this class.", "warning")
            return redirect(url_for('management.view_class', class_id=class_id))
        
        students = enrolled_students
        
        statuses = [
            "Present",
            "Late",
            "Unexcused Absence",
            "Excused Absence",
            "Suspended"
        ]

        # Get date from form (POST) or query params (GET)
        attendance_date_str = request.form.get('date') or request.args.get('date') or request.form.get('attendance_date')
        if not attendance_date_str:
            attendance_date_str = datetime.now().strftime('%Y-%m-%d')
        
        try:
            attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD format.", "danger")
            return redirect(url_for('management.take_class_attendance', class_id=class_id))
        
        # Check if date is not in the future
        if attendance_date > datetime.now().date():
            flash("Cannot take attendance for future dates.", "warning")
            attendance_date_str = datetime.now().strftime('%Y-%m-%d')
            attendance_date = datetime.now().date()

        # Load existing records for this class/date
        existing_records = {rec.student_id: rec for rec in Attendance.query.filter_by(class_id=class_id, date=attendance_date).all()}
        
        # Load school-day attendance records for the same date
        school_day_records = {}
        if attendance_date:
            school_day_attendance = SchoolDayAttendance.query.filter_by(date=attendance_date).all()
            school_day_records = {record.student_id: record for record in school_day_attendance}
        
        # Calculate attendance statistics
        total_students = len(students)
        present_count = sum(1 for record in existing_records.values() if record.status == "Present")
        late_count = sum(1 for record in existing_records.values() if record.status == "Late")
        absent_count = sum(1 for record in existing_records.values() if record.status in ["Unexcused Absence", "Excused Absence"])
        suspended_count = sum(1 for record in existing_records.values() if record.status == "Suspended")
        
        attendance_stats = {
            'total': total_students,
            'present': present_count,
            'late': late_count,
            'absent': absent_count,
            'suspended': suspended_count,
            'present_percentage': round((present_count / total_students * 100) if total_students > 0 else 0, 1)
        }

        if request.method == 'POST':
            attendance_saved = False
            valid_statuses = ["Present", "Late", "Unexcused Absence", "Excused Absence", "Suspended"]
            
            # Get current user's teacher staff record if they are management
            teacher = None
            if current_user.role in ['Director', 'School Administrator']:
                if current_user.teacher_staff_id:
                    teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
            
            for student in students:
                status = request.form.get(f'status_{student.id}')
                notes = request.form.get(f'notes_{student.id}')
                
                if not status:
                    continue
                
                # Convert lowercase status to proper format (template sends lowercase)
                status_map = {
                    'present': 'Present',
                    'late': 'Late',
                    'unexcused absence': 'Unexcused Absence',
                    'excused absence': 'Excused Absence',
                    'suspended': 'Suspended'
                }
                status = status_map.get(status.lower(), status)
                    
                # Validate status
                if status not in valid_statuses:
                    flash(f"Invalid attendance status for {student.first_name} {student.last_name}.", "warning")
                    continue
                
                # Validate that the student is still enrolled in this class
                enrollment = Enrollment.query.filter_by(
                    student_id=student.id, 
                    class_id=class_id, 
                    is_active=True
                ).first()
                
                if not enrollment:
                    flash(f'Student {student.first_name} {student.last_name} is no longer enrolled in this class.', 'warning')
                    continue
                
                # Check if record exists
                record = Attendance.query.filter_by(student_id=student.id, class_id=class_id, date=attendance_date).first()
                if record:
                    record.status = status
                    record.notes = notes
                    record.teacher_id = teacher.id if teacher else None
                else:
                    record = Attendance(
                        student_id=student.id,
                        class_id=class_id,
                        date=attendance_date,
                        status=status,
                        notes=notes,
                        teacher_id=teacher.id if teacher else None
                    )
                    db.session.add(record)
                attendance_saved = True
            
            if attendance_saved:
                try:
                    db.session.commit()
                    flash('Attendance recorded successfully.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash('Error saving attendance. Please try again.', 'danger')
                    current_app.logger.error(f"Error saving attendance: {e}")
            else:
                flash('No attendance data was submitted.', 'warning')
            
            # Redirect back to unified attendance with the date parameter to preserve context
            # Check if we came from unified attendance (has referrer or class_date param)
            referrer = request.referrer
            if referrer and 'unified-attendance' in referrer:
                # Extract class_date from referrer or use the attendance date
                return redirect(url_for('management.unified_attendance', class_date=attendance_date_str))
            else:
                # Default redirect to view_class
                return redirect(url_for('management.view_class', class_id=class_id))

        return render_template(
            'shared/take_attendance.html',
            class_item=class_obj,
            students=students,
            attendance_date_str=attendance_date_str,
            statuses=statuses,
            existing_records=existing_records,
            school_day_records=school_day_records,
            attendance_stats=attendance_stats
        )
    
    except Exception as e:
        current_app.logger.error(f"Error in take_class_attendance route: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f"Error loading attendance page: {str(e)}", "danger")
        return redirect(url_for('management.classes'))



# ============================================================
# Route: /class-grades-view/<int:class_id>
# Function: class_grades_view
# ============================================================

@bp.route('/class-grades-view/<int:class_id>')
@login_required
@management_required
def class_grades_view(class_id):
    """View class grades - redirect to the main class_grades view"""
    return redirect(url_for('management.class_grades', class_id=class_id))



# ============================================================
# Route: /view-class/<int:class_id>
# Function: view_class
# ============================================================

@bp.route('/view-class/<int:class_id>')
@login_required
@management_required
def view_class(class_id):
    """View detailed class information"""
    class_info = Class.query.get_or_404(class_id)
    
    # Get teacher information
    teacher = None
    if class_info.teacher_id:
        teacher = TeacherStaff.query.get(class_info.teacher_id)
    
    # Get enrolled students from enrollment system
    enrolled_students = db.session.query(Student).join(Enrollment).filter(
        Enrollment.class_id == class_id, 
        Enrollment.is_active == True
    ).order_by(Student.last_name, Student.first_name).all()
    
    # Get individual assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    
    # Get group assignments for this class
    try:
        group_assignments = GroupAssignment.query.filter_by(class_id=class_id).order_by(GroupAssignment.due_date.desc()).all()
    except Exception as e:
        current_app.logger.error(f"Error loading group assignments: {str(e)}")
        group_assignments = []
    
    # Combine both types with type indicator
    all_assignments = []
    for assignment in assignments:
        assignment.assignment_type = 'individual'
        assignment.graded_status = calculate_assignment_graded_status(assignment)
        all_assignments.append(assignment)
    
    for group_assignment in group_assignments:
        group_assignment.assignment_type = 'group'
        group_assignment.graded_status = calculate_group_assignment_graded_status(group_assignment)
        all_assignments.append(group_assignment)
    
    # Sort by due date
    all_assignments.sort(key=lambda x: x.due_date if x.due_date else datetime.max.date(), reverse=True)
    
    # Get recent attendance records for this class (last 7 days)
    from datetime import timedelta
    recent_attendance = Attendance.query.filter(
        Attendance.class_id == class_id,
        Attendance.date >= datetime.now().date() - timedelta(days=7)
    ).order_by(Attendance.date.desc()).all()
    
    # Get current date for assignment status comparison
    today = datetime.now().date()
    
    # Check if current user is also the teacher
    is_current_user_teacher = False
    if teacher and current_user.teacher_staff_id == teacher.id:
        is_current_user_teacher = True
    
    return render_template('management/view_class.html', 
                         class_info=class_info,
                         teacher=teacher,
                         enrolled_students=enrolled_students,
                         assignments=assignments,
                         group_assignments=group_assignments,
                         all_assignments=all_assignments,
                         recent_attendance=recent_attendance,
                         today=today,
                         is_current_user_teacher=is_current_user_teacher,
                         role_prefix=None)






# ============================================================
# Route: /manage-class-roster/<int:class_id>', methods=['GET', 'POST']
# Function: manage_class_roster
# ============================================================

@bp.route('/manage-class-roster/<int:class_id>', methods=['GET', 'POST'])
@login_required
@management_required
def manage_class_roster(class_id):
    """Manage class roster - add/remove students"""
    class_info = Class.query.get_or_404(class_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            # Handle multiple student selection
            student_ids = request.form.getlist('student_id')
            
            if not student_ids:
                flash('Please select at least one student to add.', 'warning')
            else:
                added_count = 0
                for student_id in student_ids:
                    try:
                        student_id = int(student_id)
                        # Check if student is already enrolled
                        existing_enrollment = Enrollment.query.filter_by(
                            student_id=student_id, 
                            class_id=class_id, 
                            is_active=True
                        ).first()
                        
                        if existing_enrollment:
                            flash(f'Student is already enrolled in this class.', 'warning')
                            continue
                        
                        # Create new enrollment
                        enrollment = Enrollment(
                            student_id=student_id,
                            class_id=class_id
                        )
                        db.session.add(enrollment)
                        added_count += 1
                        
                    except (ValueError, TypeError):
                        flash(f'Invalid student ID: {student_id}', 'danger')
                        continue
                
                if added_count > 0:
                    try:
                        db.session.commit()
                        # Automatically void assignments for late-enrolling students
                        from management_routes.late_enrollment_utils import void_assignments_for_late_enrollment
                        for student_id in student_ids:
                            try:
                                voided_count = void_assignments_for_late_enrollment(int(student_id), class_id)
                                if voided_count > 0:
                                    print(f"Automatically voided {voided_count} assignment(s) for student {student_id} due to late enrollment")
                            except Exception as e:
                                print(f"Error voiding assignments for student {student_id}: {e}")
                        flash(f'Successfully enrolled {added_count} student(s) in the class.', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Error enrolling students: {str(e)}', 'danger')
                else:
                    flash('No students were enrolled.', 'warning')
                    
        elif action == 'remove':
            student_id = request.form.get('student_id', type=int)
            
            if student_id:
                # Find and deactivate the enrollment
                enrollment = Enrollment.query.filter_by(
                    student_id=student_id, 
                    class_id=class_id, 
                    is_active=True
                ).first()
                
                if enrollment:
                    enrollment.is_active = False
                    enrollment.dropped_at = datetime.utcnow()
                    try:
                        db.session.commit()
                        flash('Student removed from class successfully.', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Error removing student: {str(e)}', 'danger')
                else:
                    flash('Student is not enrolled in this class.', 'warning')
            else:
                flash('No student selected for removal.', 'warning')
        
        return redirect(url_for('management.manage_class_roster', class_id=class_id))
    
    # Get all students for potential enrollment
    all_students = Student.query.all()
    
    # Convert dob string to date object for each student to allow for age calculation
    for student in all_students:
        if isinstance(student.dob, str):
            try:
                # First, try to parse 'YYYY-MM-DD' format
                student.dob = datetime.strptime(student.dob, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Fallback to 'MM/DD/YYYY' format
                    student.dob = datetime.strptime(student.dob, '%m/%d/%Y').date()
                except ValueError:
                    # If parsing fails, set dob to None so it will be handled gracefully in the template
                    student.dob = None
    
    # Get currently enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = []
    for enrollment in enrollments:
        student = Student.query.get(enrollment.student_id)
        if student:
            # Convert dob string to date object for age calculation
            if isinstance(student.dob, str):
                try:
                    # First, try to parse 'YYYY-MM-DD' format
                    student.dob = datetime.strptime(student.dob, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        # Fallback to 'MM/DD/YYYY' format
                        student.dob = datetime.strptime(student.dob, '%m/%d/%Y').date()
                    except ValueError:
                        # If parsing fails, set dob to None so it will be handled gracefully in the template
                        student.dob = None
            enrolled_students.append(student)
    
    # Get all teachers for the summary display
    available_teachers = TeacherStaff.query.filter(TeacherStaff.is_deleted == False).all()
    
    return render_template('management/manage_class_roster.html', 
                         class_info=class_info,
                         all_students=all_students,
                         enrolled_students=enrolled_students,
                         available_teachers=available_teachers,
                         today=datetime.now().date())



# ============================================================
# Route: /class/<int:class_id>/groups
# Function: admin_class_groups
# ============================================================

@bp.route('/class/<int:class_id>/groups')
@login_required
@management_required
def admin_class_groups(class_id):
    """View and manage groups for a class (Administrator access)."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Get all groups for this class
        groups = StudentGroup.query.filter_by(class_id=class_id).all()
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        enrolled_students = [enrollment.student for enrollment in enrollments]
        
        # Get group members for each group and add member_count to group objects
        group_data = []
        for group in groups:
            members = StudentGroupMember.query.filter_by(group_id=group.id).all()
            member_students = [member.student for member in members]
            # Add member_count as an attribute to the group object for template access
            group.member_count = len(member_students)
            group_data.append({
                'group': group,
                'members': member_students,
                'member_count': len(member_students)
            })
        
        return render_template('teachers/teacher_class_groups.html',
                             class_obj=class_obj,
                             groups=groups,
                             group_data=group_data,
                             enrolled_students=enrolled_students,
                             role_prefix=True)
    
    except Exception as e:
        print(f"Error loading class groups: {e}")
        flash('Error loading class groups. Please try again.', 'error')
        return redirect(url_for('management.classes'))



# ============================================================
# Route: /class/<int:class_id>/groups/auto-create', methods=['GET', 'POST']
# Function: admin_auto_create_groups
# ============================================================

@bp.route('/class/<int:class_id>/groups/auto-create', methods=['GET', 'POST'])
@login_required
@management_required
def admin_auto_create_groups(class_id):
    """Auto-create groups for a class (Administrator access)."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        enrolled_students = [enrollment.student for enrollment in enrollments]
        
        if request.method == 'POST':
            # Handle auto-create logic here
            flash('Auto-create groups functionality coming soon!', 'info')
            return redirect(url_for('management.admin_class_groups', class_id=class_id))
        
        return render_template('teachers/teacher_auto_create_groups.html',
                             class_obj=class_obj,
                             enrolled_students=enrolled_students,
                             role_prefix=True)
    except Exception as e:
        print(f"Error in auto-create groups: {e}")
        flash('Error accessing auto-create groups.', 'error')
        return redirect(url_for('management.admin_class_groups', class_id=class_id))



# ============================================================
# Route: /class/<int:class_id>/group-templates
# Function: admin_class_group_templates
# ============================================================

@bp.route('/class/<int:class_id>/group-templates')
@login_required
@management_required
def admin_class_group_templates(class_id):
    """View group templates for a class (Administrator access)."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Get group templates for this class
        templates = []  # Add template query here
        
        return render_template('teachers/teacher_class_group_templates.html',
                             class_obj=class_obj,
                             templates=templates,
                             role_prefix=True)
    except Exception as e:
        print(f"Error accessing group templates: {e}")
        flash('Error accessing group templates.', 'error')
        return redirect(url_for('management.admin_class_groups', class_id=class_id))



# ============================================================
# Route: /class/<int:class_id>/groups/analytics
# Function: admin_group_analytics
# ============================================================

@bp.route('/class/<int:class_id>/groups/analytics')
@login_required
@management_required
def admin_group_analytics(class_id):
    """View group analytics for a class (Administrator access)."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Get groups for this class
        groups = StudentGroup.query.filter_by(class_id=class_id).all()
        
        return render_template('teachers/teacher_group_analytics.html',
                             class_obj=class_obj,
                             groups=groups,
                             role_prefix=True)
    except Exception as e:
        print(f"Error accessing group analytics: {e}")
        flash('Error accessing group analytics.', 'error')
        return redirect(url_for('management.admin_class_groups', class_id=class_id))



# ============================================================
# Route: /class/<int:class_id>/group-rotations
# Function: admin_class_group_rotations
# ============================================================

@bp.route('/class/<int:class_id>/group-rotations')
@login_required
@management_required
def admin_class_group_rotations(class_id):
    """View group rotations for a class (Administrator access)."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Get group rotations for this class
        rotations = []  # Add rotation query here
        
        return render_template('teachers/teacher_class_group_rotations.html',
                             class_obj=class_obj,
                             rotations=rotations,
                             role_prefix=True)
    except Exception as e:
        print(f"Error accessing group rotations: {e}")
        flash('Error accessing group rotations.', 'error')
        return redirect(url_for('management.admin_class_groups', class_id=class_id))



# ============================================================
# Route: /class/<int:class_id>/group-assignment/type-selector
# Function: admin_group_assignment_type_selector
# ============================================================

@bp.route('/class/<int:class_id>/group-assignment/type-selector')
@login_required
@management_required
def admin_group_assignment_type_selector(class_id):
    """Group assignment type selector for management."""
    class_obj = Class.query.get_or_404(class_id)
    
    return render_template('shared/group_assignment_type_selector.html',
                         class_obj=class_obj,
                         admin_view=True)



# ============================================================
# Route: /class/<int:class_id>/group-assignment/create/pdf', methods=['GET', 'POST']
# Function: admin_create_group_pdf_assignment
# ============================================================

@bp.route('/class/<int:class_id>/group-assignment/create/pdf', methods=['GET', 'POST'])
@login_required
@management_required
def admin_create_group_pdf_assignment(class_id):
    """Create a new PDF group assignment - Management view."""
    from werkzeug.utils import secure_filename
    import time
    import os
    import json
    
    class_obj = Class.query.get_or_404(class_id)
    
    # Get current school year and academic periods
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    academic_periods = []
    if current_school_year:
        academic_periods = AcademicPeriod.query.filter_by(school_year_id=current_school_year.id, is_active=True).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        open_date_str = request.form.get('open_date', '').strip()
        close_date_str = request.form.get('close_date', '').strip()
        quarter = request.form.get('quarter', '')
        semester = request.form.get('semester', '')
        academic_period_id = request.form.get('academic_period_id')
        assignment_status = request.form.get('assignment_status', 'Active').strip()
        assignment_category = request.form.get('assignment_category', '').strip()
        group_size_min = request.form.get('group_size_min', 2)
        group_size_max = request.form.get('group_size_max', 4)
        allow_individual = 'allow_individual' in request.form
        collaboration_type = request.form.get('collaboration_type', 'group')
        
        # Advanced grading options
        allow_extra_credit = request.form.get('allow_extra_credit') == 'on'
        max_extra_credit_points = float(request.form.get('max_extra_credit_points', 0) or 0)
        late_penalty_enabled = request.form.get('late_penalty_enabled') == 'on'
        late_penalty_per_day = float(request.form.get('late_penalty_per_day', 0) or 0)
        late_penalty_max_days = int(request.form.get('late_penalty_max_days', 0) or 0)
        category_weight = float(request.form.get('category_weight', 0) or 0)
        
        grade_scale_preset = request.form.get('grade_scale_preset', '').strip()
        grade_scale = None
        if grade_scale_preset == 'standard':
            grade_scale = json.dumps({"A": 90, "B": 80, "C": 70, "D": 60, "F": 0, "use_plus_minus": False})
        elif grade_scale_preset == 'strict':
            grade_scale = json.dumps({"A": 93, "B": 85, "C": 77, "D": 70, "F": 0, "use_plus_minus": False})
        elif grade_scale_preset == 'lenient':
            grade_scale = json.dumps({"A": 88, "B": 78, "C": 68, "D": 58, "F": 0, "use_plus_minus": False})
        
        if not title or not due_date_str or not quarter:
            flash('Title, due date, and quarter are required.', 'danger')
            return render_template('shared/create_group_pdf_assignment.html', 
                                 class_obj=class_obj, 
                                 academic_periods=academic_periods,
                                 admin_view=True)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            open_date = datetime.strptime(open_date_str, '%Y-%m-%dT%H:%M') if open_date_str else None
            close_date = datetime.strptime(close_date_str, '%Y-%m-%dT%H:%M') if close_date_str else None
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('shared/create_group_pdf_assignment.html', 
                                 class_obj=class_obj, 
                                 academic_periods=academic_periods,
                                 admin_view=True)
        
        # Handle file upload
        attachment_filename = None
        attachment_original_filename = None
        attachment_file_path = None
        attachment_file_size = None
        attachment_mime_type = None
        
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = str(int(time.time()))
                attachment_filename = f"group_assignment_{class_id}_{timestamp}_{filename}"
                attachment_original_filename = file.filename
                
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(current_app.static_folder, 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                attachment_file_path = os.path.join(upload_dir, attachment_filename)
                file.save(attachment_file_path)
                attachment_file_size = os.path.getsize(attachment_file_path)
                attachment_mime_type = file.content_type
        
        # Handle group selection
        group_selection = request.form.get('group_selection', 'all')
        selected_groups = request.form.getlist('selected_groups')
        selected_group_ids = None
        
        if group_selection == 'specific' and selected_groups:
            selected_group_ids = json.dumps([int(group_id) for group_id in selected_groups])
        
        # Get assignment context from form or query parameter
        assignment_context = request.form.get('assignment_context', 'homework')
        
        # Get total points from form (default to 100 if not provided)
        total_points = request.form.get('total_points', type=float)
        if total_points is None or total_points <= 0:
            total_points = 100.0
        
        # Create the group assignment
        group_assignment = GroupAssignment(
            title=title,
            description=description,
            class_id=class_id,
            due_date=due_date,
            open_date=open_date,
            close_date=close_date,
            quarter=quarter,
            semester=semester if semester else None,
            academic_period_id=int(academic_period_id) if academic_period_id else None,
            school_year_id=current_school_year.id if current_school_year else None,
            assignment_type='pdf',
            assignment_category=assignment_category if assignment_category else None,
            category_weight=category_weight,
            allow_extra_credit=allow_extra_credit,
            max_extra_credit_points=max_extra_credit_points,
            late_penalty_enabled=late_penalty_enabled,
            late_penalty_per_day=late_penalty_per_day,
            late_penalty_max_days=late_penalty_max_days,
            grade_scale=grade_scale,
            group_size_min=int(group_size_min),
            group_size_max=int(group_size_max),
            allow_individual=allow_individual,
            collaboration_type=collaboration_type,
            selected_group_ids=selected_group_ids,
            assignment_context=assignment_context,
            total_points=total_points,
            created_by=current_user.id,
            attachment_filename=attachment_filename,
            attachment_original_filename=attachment_original_filename,
            attachment_file_path=attachment_file_path,
            attachment_file_size=attachment_file_size,
            attachment_mime_type=attachment_mime_type,
            status=assignment_status
        )
        
        db.session.add(group_assignment)
        db.session.commit()
        
        flash(f'Group PDF assignment "{title}" created successfully!', 'success')
        return redirect(url_for('management.admin_class_group_assignments', class_id=class_id))
    
    return render_template('shared/create_group_pdf_assignment.html',
                         class_obj=class_obj,
                         academic_periods=academic_periods,
                         admin_view=True)



# ============================================================
# Route: /class/<int:class_id>/group-assignment/create/quiz', methods=['GET', 'POST']
# Function: admin_create_group_quiz_assignment
# ============================================================

@bp.route('/class/<int:class_id>/group-assignment/create/quiz', methods=['GET', 'POST'])
@login_required
@management_required
def admin_create_group_quiz_assignment(class_id):
    """Create a new quiz group assignment - Management view."""
    import json
    
    class_obj = Class.query.get_or_404(class_id)
    
    # Get current school year and academic periods
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    academic_periods = []
    if current_school_year:
        academic_periods = AcademicPeriod.query.filter_by(school_year_id=current_school_year.id, is_active=True).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter', '')
        semester = request.form.get('semester', '')
        academic_period_id = request.form.get('academic_period_id')
        group_size_min = request.form.get('group_size_min', 2)
        group_size_max = request.form.get('group_size_max', 4)
        allow_individual = 'allow_individual' in request.form
        collaboration_type = request.form.get('collaboration_type', 'group')
        
        # Quiz-specific settings
        time_limit = int(request.form.get('time_limit', 30))
        passing_score = float(request.form.get('passing_score', 70))
        shuffle_questions = 'shuffle_questions' in request.form
        show_correct_answers = 'show_correct_answers' in request.form
        allow_save_and_continue = 'allow_save_and_continue' in request.form
        
        # Handle group selection
        group_selection = request.form.get('group_selection', 'all')
        selected_groups = request.form.getlist('selected_groups')
        selected_group_ids = None
        
        if group_selection == 'specific' and selected_groups:
            selected_group_ids = json.dumps([int(group_id) for group_id in selected_groups])
        
        if not title or not due_date_str or not quarter:
            flash('Title, due date, and quarter are required.', 'danger')
            return render_template('shared/create_group_quiz_assignment.html', 
                                 class_obj=class_obj, 
                                 academic_periods=academic_periods,
                                 admin_view=True)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid due date format.', 'danger')
            return render_template('shared/create_group_quiz_assignment.html', 
                                 class_obj=class_obj, 
                                 academic_periods=academic_periods,
                                 admin_view=True)
        
        # Get assignment context from form or query parameter
        assignment_context = request.form.get('assignment_context', 'homework')
        
        # Create the group assignment
        group_assignment = GroupAssignment(
            title=title,
            description=description,
            class_id=class_id,
            due_date=due_date,
            quarter=quarter,
            semester=semester if semester else None,
            academic_period_id=int(academic_period_id) if academic_period_id else None,
            school_year_id=current_school_year.id if current_school_year else None,
            assignment_type='quiz',
            group_size_min=int(group_size_min),
            group_size_max=int(group_size_max),
            allow_individual=allow_individual,
            collaboration_type=collaboration_type,
            selected_group_ids=selected_group_ids,
            assignment_context=assignment_context,
            created_by=current_user.id,
            allow_save_and_continue=allow_save_and_continue,
            max_save_attempts=10,
            save_timeout_minutes=30,
            status='Active'
        )
        
        db.session.add(group_assignment)
        db.session.flush()  # Get the assignment ID
        
        # Save quiz questions
        question_count = 0
        for key, value in request.form.items():
            if key.startswith('question_text_'):
                question_id = key.split('_')[2]
                question_text = value
                question_type = request.form.get(f'question_type_{question_id}')
                points = float(request.form.get(f'question_points_{question_id}', 1.0))
                
                # Create the question
                question = GroupQuizQuestion(
                    group_assignment_id=group_assignment.id,
                    question_text=question_text,
                    question_type=question_type,
                    points=points,
                    order=question_count
                )
                db.session.add(question)
                db.session.flush()  # Get the question ID
                
                # Save options for multiple choice and true/false
                if question_type in ['multiple_choice', 'true_false']:
                    option_count = 0
                    # Iterate through all form items to find options for the current question
                    for option_key, option_value in request.form.items():
                        if option_key.startswith(f'option_text_{question_id}[]'):
                            option_text = option_value
                            # Find the correct answer for this question
                            correct_answer = request.form.get(f'correct_answer_{question_id}')
                            # Compare option_count as string with correct_answer
                            is_correct = str(option_count) == correct_answer
                            
                            option = GroupQuizOption(
                                question_id=question.id,
                                option_text=option_text,
                                is_correct=is_correct,
                                order=option_count
                            )
                            db.session.add(option)
                            option_count += 1
                
                question_count += 1
        
        db.session.commit()
        flash(f'Group quiz assignment "{title}" created successfully!', 'success')
        return redirect(url_for('management.admin_class_group_assignments', class_id=class_id))
    
    return render_template('shared/create_group_quiz_assignment.html',
                         class_obj=class_obj,
                         academic_periods=academic_periods,
                         admin_view=True)



# ============================================================
# Route: /class/<int:class_id>/group-assignment/create/discussion', methods=['GET', 'POST']
# Function: admin_create_group_discussion_assignment
# ============================================================

@bp.route('/class/<int:class_id>/group-assignment/create/discussion', methods=['GET', 'POST'])
@login_required
@management_required
def admin_create_group_discussion_assignment(class_id):
    """Create a new discussion group assignment - Management view."""
    import json
    
    class_obj = Class.query.get_or_404(class_id)
    
    # Get current school year and academic periods
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    academic_periods = []
    if current_school_year:
        academic_periods = AcademicPeriod.query.filter_by(school_year_id=current_school_year.id, is_active=True).all()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter', '')
        semester = request.form.get('semester', '')
        academic_period_id = request.form.get('academic_period_id')
        group_size_min = request.form.get('group_size_min', 2)
        group_size_max = request.form.get('group_size_max', 4)
        allow_individual = 'allow_individual' in request.form
        collaboration_type = request.form.get('collaboration_type', 'group')
        
        # Discussion-specific settings
        min_posts = int(request.form.get('min_posts', 2))
        min_words = int(request.form.get('min_words', 100))
        max_posts = int(request.form.get('max_posts', 10))
        allow_replies = 'allow_replies' in request.form
        require_citations = 'require_citations' in request.form
        anonymous_posts = 'anonymous_posts' in request.form
        moderate_posts = 'moderate_posts' in request.form
        
        # Handle group selection
        group_selection = request.form.get('group_selection', 'all')
        selected_groups = request.form.getlist('selected_groups')
        selected_group_ids = None
        
        if group_selection == 'specific' and selected_groups:
            selected_group_ids = json.dumps([int(group_id) for group_id in selected_groups])
        
        if not title or not due_date_str or not quarter:
            flash('Title, due date, and quarter are required.', 'danger')
            return render_template('shared/create_group_discussion_assignment.html', 
                                 class_obj=class_obj, 
                                 academic_periods=academic_periods,
                                 admin_view=True)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid due date format.', 'danger')
            return render_template('shared/create_group_discussion_assignment.html', 
                                 class_obj=class_obj, 
                                 academic_periods=academic_periods,
                                 admin_view=True)
        
        # Get assignment context from form or query parameter
        assignment_context = request.form.get('assignment_context', 'homework')
        
        # Create the group assignment
        group_assignment = GroupAssignment(
            title=title,
            description=description,
            class_id=class_id,
            due_date=due_date,
            quarter=quarter,
            semester=semester if semester else None,
            academic_period_id=int(academic_period_id) if academic_period_id else None,
            school_year_id=current_school_year.id if current_school_year else None,
            assignment_type='discussion',
            group_size_min=int(group_size_min),
            group_size_max=int(group_size_max),
            allow_individual=allow_individual,
            collaboration_type=collaboration_type,
            selected_group_ids=selected_group_ids,
            assignment_context=assignment_context,
            created_by=current_user.id,
            status='Active'
        )
        
        db.session.add(group_assignment)
        db.session.flush()  # Get the assignment ID
        
        # Save discussion prompts
        prompt_count = 0
        for key, value in request.form.items():
            if key.startswith('prompt_text_'):
                prompt_id = key.split('_')[2]
                prompt_text = value
                prompt_type = request.form.get(f'prompt_type_{prompt_id}')
                response_length = request.form.get(f'response_length_{prompt_id}')
                
                # For now, we'll store prompts in the description or create a separate table later
                # This is a simplified implementation
                if prompt_count == 0:
                    group_assignment.description += f"\n\nDiscussion Prompts:\n"
                group_assignment.description += f"\n{prompt_count + 1}. {prompt_text} (Type: {prompt_type}, Length: {response_length})"
                prompt_count += 1
        
        db.session.commit()
        flash(f'Group discussion assignment "{title}" created successfully!', 'success')
        return redirect(url_for('management.admin_class_group_assignments', class_id=class_id))
    
    return render_template('shared/create_group_discussion_assignment.html',
                         class_obj=class_obj,
                         academic_periods=academic_periods,
                         admin_view=True)


