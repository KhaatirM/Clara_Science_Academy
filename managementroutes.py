# Core Flask imports
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user

# Database and model imports - organized by category
from models import (
    # Core database
    db,
    # User and staff models
    Student, TeacherStaff, User,
    # Academic structure
    Class, SchoolYear, AcademicPeriod, Enrollment,
    # Assignment system
    Assignment, AssignmentExtension, Submission, Grade, ReportCard,
    # Quiz system
    QuizQuestion, QuizOption, QuizAnswer,
    # Communication system
    Announcement, Message, MessageGroup, MessageGroupMember, ScheduledAnnouncement, Notification,
    # Attendance system
    Attendance, SchoolDayAttendance,
    # Calendar and scheduling
    CalendarEvent, TeacherWorkDay, SchoolBreak,
    # Discussion system
    DiscussionThread, DiscussionPost
)

# Authentication and decorators
from decorators import management_required

# Application imports
from app import calculate_and_get_grade_for_student, get_grade_for_student, create_notification

# Standard library imports
import os
import json
import time
import re
from datetime import datetime, timedelta, date

# Werkzeug utilities
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

# SQLAlchemy
from sqlalchemy import text
# from add_academic_periods import add_academic_periods_for_year  # Function removed during cleanup

def add_academic_periods_for_year(school_year_id):
    """Create default academic periods for a school year"""
    from models import AcademicPeriod, SchoolYear
    from datetime import datetime, date
    
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

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_assignment_statuses():
    """Update assignment statuses - past due 'Active' assignments become 'Inactive'"""
    from datetime import datetime
    
    try:
        # Get all active assignments that are past due
        today = datetime.now().date()
        past_due_assignments = Assignment.query.filter(
            Assignment.status == 'Active',
            db.func.date(Assignment.due_date) < today
        ).all()
        
        # Update their status to 'Inactive'
        for assignment in past_due_assignments:
            assignment.status = 'Inactive'
        
        if past_due_assignments:
            db.session.commit()
            print(f"Updated {len(past_due_assignments)} assignments from Active to Inactive")
            
    except Exception as e:
        print(f"Error updating assignment statuses: {e}")
        db.session.rollback()

def get_current_quarter():
    """Get the current quarter based on AcademicPeriod dates"""
    try:
        from datetime import date
        
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
    # Get all grades for the student
    grades = Grade.query.filter_by(student_id=student_id).all()
    
    if not grades:
        return 0.0  # No grades yet
    
    total_points = 0
    total_assignments = 0
    
    for grade in grades:
        try:
            # Parse the grade data (stored as JSON)
            grade_data = json.loads(grade.grade_data)
            score = grade_data.get('score', 0)
            
            # Convert percentage to GPA (assuming 90+ = 4.0, 80-89 = 3.0, etc.)
            if score >= 90:
                gpa_points = 4.0
            elif score >= 80:
                gpa_points = 3.0
            elif score >= 70:
                gpa_points = 2.0
            elif score >= 60:
                gpa_points = 1.0
            else:
                gpa_points = 0.0
            
            total_points += gpa_points
            total_assignments += 1
            
        except (json.JSONDecodeError, KeyError, ValueError):
            # Skip invalid grade data
            continue
    
    if total_assignments == 0:
        return 0.0
    
    return round(total_points / total_assignments, 2)

management_blueprint = Blueprint('management', __name__)

@management_blueprint.route('/dashboard')
@login_required
@management_required
def management_dashboard():
    from datetime import datetime, timedelta
    
    # Basic stats
    stats = {
        'students': Student.query.count(),
        'teachers': TeacherStaff.query.count(),
        'classes': Class.query.count(),
        'assignments': Assignment.query.count()
    }
    
    # Calculate monthly stats
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # New students this month (using ID as proxy since no created_at field)
    # This is a simplified approach - in a real system, you'd want a created_at field
    total_students = Student.query.count()
    # For now, we'll use a placeholder since we can't track creation dates
    # In a real implementation, you'd add a created_at field to the Student model
    new_students = 0
    
    # Alternative: Track new enrollments this month
    try:
        new_enrollments = Enrollment.query.filter(Enrollment.enrolled_at >= month_start).count()
    except AttributeError:
        new_enrollments = 0
    
    # Assignments due this week
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    due_assignments = Assignment.query.filter(
        Assignment.due_date >= week_start,
        Assignment.due_date < week_end
    ).count()
    
    # Calculate attendance rate (simplified)
    total_attendance_records = Attendance.query.count()
    present_records = Attendance.query.filter_by(status='Present').count()
    attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
    
    # Calculate average grade (simplified)
    grades = Grade.query.all()
    if grades:
        total_score = 0
        valid_grades = 0
        for grade in grades:
            try:
                grade_data = json.loads(grade.grade_data)
                if 'score' in grade_data and isinstance(grade_data['score'], (int, float)):
                    total_score += grade_data['score']
                    valid_grades += 1
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        
        average_grade = round(total_score / valid_grades, 1) if valid_grades > 0 else 0
    else:
        average_grade = 0
    
    monthly_stats = {
        'new_students': new_enrollments,  # Using new enrollments as proxy for new students
        'attendance_rate': attendance_rate,
        'average_grade': average_grade
    }
    
    weekly_stats = {
        'due_assignments': due_assignments
    }
    
    return render_template('management/role_dashboard.html', 
                         stats=stats,
                         monthly_stats=monthly_stats,
                         weekly_stats=weekly_stats,
                         section='home',
                         active_tab='home')

# Routes for managing students, teachers, classes etc.
# Example: Add Student
@management_blueprint.route('/add-student', methods=['GET', 'POST'])
@login_required
@management_required
def add_student():
    """Add a new student"""
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('student_first_name', '').strip()
        last_name = request.form.get('student_last_name', '').strip()
        dob = request.form.get('dob', '').strip()
        grade_level_str = request.form.get('grade_level', '').strip()
        
        # Address fields
        street = request.form.get('street_address', '').strip()
        apt_unit = request.form.get('apt_unit_suite', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        zip_code = request.form.get('zip_code', '').strip()
        
        # Parent 1 information
        parent1_first_name = request.form.get('parent1_first_name', '').strip()
        parent1_last_name = request.form.get('parent1_last_name', '').strip()
        parent1_email = request.form.get('parent1_email', '').strip()
        parent1_phone = request.form.get('parent1_phone', '').strip()
        parent1_relationship = request.form.get('parent1_relationship', '').strip()
        
        # Parent 2 information
        parent2_first_name = request.form.get('parent2_first_name', '').strip()
        parent2_last_name = request.form.get('parent2_last_name', '').strip()
        parent2_email = request.form.get('parent2_email', '').strip()
        parent2_phone = request.form.get('parent2_phone', '').strip()
        parent2_relationship = request.form.get('parent2_relationship', '').strip()
        
        # Emergency contact
        emergency_first_name = request.form.get('emergency_first_name', '').strip()
        emergency_last_name = request.form.get('emergency_last_name', '').strip()
        emergency_email = request.form.get('emergency_email', '').strip()
        emergency_phone = request.form.get('emergency_phone', '').strip()
        emergency_relationship = request.form.get('emergency_relationship', '').strip()
        
        # Additional fields
        previous_school = request.form.get('previous_school', '').strip()
        email = request.form.get('email', '').strip()
        medical_concerns = request.form.get('medical_concerns', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Handle image upload
        photo_filename = None
        if 'student_image' in request.files:
            file = request.files['student_image']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Generate unique filename
                    import uuid
                    file_extension = file.filename.rsplit('.', 1)[1].lower()
                    photo_filename = f"student_{uuid.uuid4().hex}.{file_extension}"
                    
                    # Save file
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, photo_filename)
                    file.save(file_path)
                else:
                    flash('Invalid file type. Please upload an image file (jpg, jpeg, png, gif).', 'danger')
                    return redirect(request.url)
        
        # Handle transcript upload
        transcript_filename = None
        if 'transcript' in request.files:
            file = request.files['transcript']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Generate unique filename
                    import uuid
                    file_extension = file.filename.rsplit('.', 1)[1].lower()
                    transcript_filename = f"transcript_{uuid.uuid4().hex}.{file_extension}"
                    
                    # Save file
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, transcript_filename)
                    file.save(file_path)
                else:
                    flash('Invalid file type for transcript. Please upload a valid document.', 'danger')
                    return redirect(request.url)
        
        # Convert grade level string to integer
        grade_level = None
        if grade_level_str:
            grade_map = {
                "Kindergarten": 0, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
                "6th": 6, "7th": 7, "8th": 8, "9th": 9, "10th": 10, "11th": 11, "12th": 12
            }
            grade_level = grade_map.get(grade_level_str)
        
        # Validate required fields
        if not all([first_name, last_name, dob, grade_level]):
            flash('First name, last name, date of birth, and grade level are required.', 'danger')
            return redirect(request.url)
        
        # Generate username (first initial + last name + random number)
        import random
        base_username = f"{first_name[0].lower()}{last_name.lower()}"
        username = base_username
        counter = 1
        
        # Ensure unique username
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Generate password (first name + last 4 digits of year)
        year = dob.split('-')[0] if '-' in dob else str(random.randint(2000, 2010))
        password = f"{first_name.lower()}{year[-4:]}"
        
        try:
            # Create student record
            student = Student()
            student.first_name = first_name
            student.last_name = last_name
            student.dob = dob
            student.grade_level = grade_level
            student.photo_filename = photo_filename
            student.transcript_filename = transcript_filename
            
            # Address fields
            student.street = street
            student.apt_unit = apt_unit
            student.city = city
            student.state = state
            student.zip_code = zip_code
            
            # Additional fields
            student.previous_school = previous_school
            student.email = email
            student.medical_concerns = medical_concerns
            student.notes = notes
            
            # Parent 1 information
            student.parent1_first_name = parent1_first_name
            student.parent1_last_name = parent1_last_name
            student.parent1_email = parent1_email
            student.parent1_phone = parent1_phone
            student.parent1_relationship = parent1_relationship
            
            # Parent 2 information
            student.parent2_first_name = parent2_first_name
            student.parent2_last_name = parent2_last_name
            student.parent2_email = parent2_email
            student.parent2_phone = parent2_phone
            student.parent2_relationship = parent2_relationship
            
            # Emergency contact
            student.emergency_first_name = emergency_first_name
            student.emergency_last_name = emergency_last_name
            student.emergency_email = emergency_email
            student.emergency_phone = emergency_phone
            student.emergency_relationship = emergency_relationship

            # Auto-generate Student ID based on state and DOB (call after all fields are set)
            student.student_id = student.generate_student_id()
            
            db.session.add(student)
            db.session.flush()  # Get the student ID
            
            # Create user account
            user = User()
            user.username = username
            user.password_hash = generate_password_hash(password)
            user.role = 'Student'
            user.student_id = student.id
            user.is_temporary_password = True  # New users must change password
            user.password_changed_at = None
            
            db.session.add(user)
            db.session.commit()
            
            # Show success message with credentials
            flash(f'Student added successfully! Username: {username}, Password: {password}. Student will be required to change password on first login.', 'success')
            return redirect(url_for('management.students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('students/add_student.html')

@management_blueprint.route('/add-teacher-staff', methods=['GET', 'POST'])
@login_required
@management_required
def add_teacher_staff():
    """Add a new teacher or staff member"""
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        middle_initial = request.form.get('middle_initial', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        dob = request.form.get('dob', '').strip()
        staff_ssn = request.form.get('staff_ssn', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Professional information
        assigned_role = request.form.get('assigned_role', 'Teacher').strip()
        hire_date = request.form.get('hire_date', '').strip()
        # Handle multiple department selections
        departments = request.form.getlist('department')
        department = ', '.join(departments) if departments else ''
        position = request.form.get('position', '').strip()
        subject = request.form.get('subject', '').strip()
        employment_type = request.form.get('employment_type', '').strip()
        
        # Handle multiple grades taught selections
        grades_taught = request.form.getlist('grades_taught')
        grades_taught_json = json.dumps(grades_taught) if grades_taught else ''
        
        # Auto-assign role and department for Tech users
        if current_user.role in ['Tech', 'IT Support']:
            assigned_role = 'IT Support'
            department = 'Administration'
        
        # Address fields
        street = request.form.get('street_address', '').strip()
        apt_unit = request.form.get('apt_unit_suite', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        zip_code = request.form.get('zip_code', '').strip()
        
        # Emergency contact fields
        emergency_first_name = request.form.get('emergency_contact_name', '').strip()
        emergency_last_name = request.form.get('emergency_contact_last_name', '').strip()
        emergency_email = request.form.get('emergency_contact_email', '').strip()
        emergency_phone = request.form.get('emergency_contact_phone', '').strip()
        emergency_relationship = request.form.get('emergency_contact_relationship', '').strip()
        
        # Validate required fields
        if not all([first_name, last_name, email]):
            flash('First name, last name, and email are required.', 'danger')
            return redirect(request.url)
        
        # Validate email format
        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address.', 'danger')
            return redirect(request.url)
        
        # Check if email already exists
        if TeacherStaff.query.filter_by(email=email).first():
            flash('A teacher/staff member with this email already exists.', 'danger')
            return redirect(request.url)
        
        # Generate username (first initial + last name + random number)
        import random
        base_username = f"{first_name[0].lower()}{last_name.lower()}"
        username = base_username
        counter = 1
        
        # Ensure unique username
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Generate password (first name + last 4 digits of year)
        year = str(random.randint(2000, 2010))
        password = f"{first_name.lower()}{year[-4:]}"
        
        try:
            # Create teacher/staff record
            teacher_staff = TeacherStaff()
            teacher_staff.first_name = first_name
            teacher_staff.middle_initial = middle_initial
            teacher_staff.last_name = last_name
            teacher_staff.email = email
            teacher_staff.dob = dob
            teacher_staff.staff_ssn = staff_ssn
            teacher_staff.phone = phone
            
            # Professional information
            teacher_staff.assigned_role = assigned_role
            teacher_staff.hire_date = hire_date
            teacher_staff.department = department
            teacher_staff.position = position
            teacher_staff.subject = subject
            teacher_staff.employment_type = employment_type
            teacher_staff.grades_taught = grades_taught_json
            
            # Address fields
            teacher_staff.street = street
            teacher_staff.apt_unit = apt_unit
            teacher_staff.city = city
            teacher_staff.state = state
            teacher_staff.zip_code = zip_code
            
            # Emergency contact fields
            teacher_staff.emergency_first_name = emergency_first_name
            teacher_staff.emergency_last_name = emergency_last_name
            teacher_staff.emergency_email = emergency_email
            teacher_staff.emergency_phone = emergency_phone
            teacher_staff.emergency_relationship = emergency_relationship
            
            db.session.add(teacher_staff)
            db.session.flush()  # Get the teacher_staff ID
            
            # Generate staff ID
            teacher_staff.staff_id = teacher_staff.generate_staff_id()
            
            # Create user account
            user = User()
            user.username = username
            user.password_hash = generate_password_hash(password)
            user.role = assigned_role
            user.teacher_staff_id = teacher_staff.id
            user.is_temporary_password = True  # New users must change password
            user.password_changed_at = None
            
            db.session.add(user)
            db.session.commit()
            
            # Show success message with credentials
            flash(f'{assigned_role} added successfully! Username: {username}, Password: {password}, Staff ID: {teacher_staff.staff_id}. User will be required to change password on first login.', 'success')
            return redirect(url_for('management.teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding {assigned_role.lower()}: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('management/add_teacher_staff.html')

@management_blueprint.route('/edit-teacher-staff/<int:staff_id>')
@login_required
@management_required
def edit_teacher_staff(staff_id):
    """Edit a teacher or staff member"""
    teacher_staff = TeacherStaff.query.get_or_404(staff_id)
    return render_template('management/add_teacher_staff.html', teacher_staff=teacher_staff, editing=True)

@management_blueprint.route('/remove-teacher-staff/<int:staff_id>', methods=['POST'])
@login_required
@management_required
def remove_teacher_staff(staff_id):
    """Remove a teacher or staff member"""
    teacher_staff = TeacherStaff.query.get_or_404(staff_id)
    db.session.delete(teacher_staff)
    db.session.commit()
    flash('Teacher/Staff member removed successfully.', 'success')
    return redirect(url_for('management.teachers'))

# Report Card Generation
@management_blueprint.route('/report/card/generate', methods=['GET', 'POST'])
@login_required
@management_required
def generate_report_card_form():
    students = Student.query.order_by(Student.last_name, Student.first_name).all()
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        school_year_id = request.form.get('school_year_id')
        quarter = request.form.get('quarter')
        
        if not all([student_id, school_year_id, quarter]):
            flash("Please select a student, school year, and quarter.", 'danger')
            return redirect(request.url)

        # Type assertion - we know these are not None after validation
        assert student_id is not None
        assert school_year_id is not None
        assert quarter is not None

        # Validate that the values can be converted to integers
        try:
            student_id_int = int(student_id)
            school_year_id_int = int(school_year_id)
            quarter_int = int(quarter)
        except ValueError:
            flash("Invalid student, school year, or quarter selection.", 'danger')
            return redirect(request.url)

        # The calculation function also saves the report card
        calculate_and_get_grade_for_student(student_id_int, school_year_id_int, quarter_int)
        
        flash('Report card data generated successfully.', 'success')
        
        report_card = ReportCard.query.filter_by(
            student_id=student_id,
            school_year_id=school_year_id,
            quarter=quarter
        ).first()
        
        if report_card:
            return redirect(url_for('management.view_report_card', report_card_id=report_card.id))
        else:
            flash('Could not find the generated report card.', 'danger')

    return render_template('management/report_card_generate_form.html', students=students, school_years=school_years)

@management_blueprint.route('/report/card/view/<int:report_card_id>')
@login_required
@management_required
def view_report_card(report_card_id):
    report_card = ReportCard.query.get_or_404(report_card_id)
    grades = json.loads(report_card.grades_details) if report_card.grades_details else {}
    # attendance = json.loads(report_card.attendance_details) if report_card.attendance_details else {}
    
    # Dummy attendance data for now
    attendance = {"Present": 45, "Absent": 2, "Tardy": 1}

    return render_template('management/report_card_detail.html', report_card=report_card, grades=grades, attendance=attendance)

# @management_blueprint.route('/report/card/pdf/<int:report_card_id>')
# @login_required
# @management_required
# def generate_report_card_pdf(report_card_id):
#     # PDF generation temporarily disabled due to import issues
#     flash('PDF generation is temporarily unavailable. Please check back later.', 'warning')
#     return redirect(url_for('management.view_report_card', report_card_id=report_card_id))

@management_blueprint.route('/students')
@login_required
@management_required
def students():
    # Get search parameters
    search_query = request.args.get('search', '').strip()
    search_type = request.args.get('search_type', 'all')
    grade_filter = request.args.get('grade_level', '')
    status_filter = request.args.get('status', '')
    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'asc')
    
    # Build the query
    query = Student.query
    
    # Apply search filter if query exists
    if search_query:
        if search_type == 'all' or search_type == '':
            # Search across all fields
            search_filter = db.or_(
                Student.first_name.ilike(f'%{search_query}%'),
                Student.last_name.ilike(f'%{search_query}%'),
                Student.email.ilike(f'%{search_query}%'),
                Student.student_id.ilike(f'%{search_query}%'),
                Student.parent1_first_name.ilike(f'%{search_query}%'),
                Student.parent1_last_name.ilike(f'%{search_query}%'),
                Student.parent1_email.ilike(f'%{search_query}%'),
                Student.parent1_phone.ilike(f'%{search_query}%'),
                Student.parent2_first_name.ilike(f'%{search_query}%'),
                Student.parent2_last_name.ilike(f'%{search_query}%'),
                Student.parent2_email.ilike(f'%{search_query}%'),
                Student.parent2_phone.ilike(f'%{search_query}%'),
                Student.emergency_first_name.ilike(f'%{search_query}%'),
                Student.emergency_last_name.ilike(f'%{search_query}%'),
                Student.emergency_phone.ilike(f'%{search_query}%'),
                Student.city.ilike(f'%{search_query}%'),
                Student.state.ilike(f'%{search_query}%'),
                Student.previous_school.ilike(f'%{search_query}%')
            )
        elif search_type == 'name':
            search_filter = db.or_(
                Student.first_name.ilike(f'%{search_query}%'),
                Student.last_name.ilike(f'%{search_query}%')
            )
        elif search_type == 'contact':
            search_filter = db.or_(
                Student.email.ilike(f'%{search_query}%'),
                Student.parent1_email.ilike(f'%{search_query}%'),
                Student.parent2_email.ilike(f'%{search_query}%'),
                Student.emergency_email.ilike(f'%{search_query}%')
            )
        elif search_type == 'phone':
            search_filter = db.or_(
                Student.parent1_phone.ilike(f'%{search_query}%'),
                Student.parent2_phone.ilike(f'%{search_query}%'),
                Student.emergency_phone.ilike(f'%{search_query}%')
            )
        elif search_type == 'address':
            search_filter = db.or_(
                Student.street.ilike(f'%{search_query}%'),
                Student.city.ilike(f'%{search_query}%'),
                Student.state.ilike(f'%{search_query}%'),
                Student.zip_code.ilike(f'%{search_query}%')
            )
        elif search_type == 'parents':
            search_filter = db.or_(
                Student.parent1_first_name.ilike(f'%{search_query}%'),
                Student.parent1_last_name.ilike(f'%{search_query}%'),
                Student.parent2_first_name.ilike(f'%{search_query}%'),
                Student.parent2_last_name.ilike(f'%{search_query}%')
            )
        else:
            # Default to all fields
            search_filter = db.or_(
                Student.first_name.ilike(f'%{search_query}%'),
                Student.last_name.ilike(f'%{search_query}%'),
                Student.email.ilike(f'%{search_query}%'),
                Student.student_id.ilike(f'%{search_query}%')
            )
        query = query.filter(search_filter)
    
    # Apply grade level filter
    if grade_filter:
        query = query.filter(Student.grade_level == int(grade_filter))
    
    # Apply status filter (account status)
    if status_filter:
        if status_filter == 'has_account':
            query = query.filter(Student.user.isnot(None))
        elif status_filter == 'no_account':
            query = query.filter(Student.user.is_(None))
    
    # Apply sorting
    if sort_by == 'name':
        if sort_order == 'desc':
            query = query.order_by(Student.last_name.desc(), Student.first_name.desc())
        else:
            query = query.order_by(Student.last_name, Student.first_name)
    elif sort_by == 'grade':
        if sort_order == 'desc':
            query = query.order_by(Student.grade_level.desc(), Student.last_name, Student.first_name)
        else:
            query = query.order_by(Student.grade_level, Student.last_name, Student.first_name)
    elif sort_by == 'id':
        if sort_order == 'desc':
            query = query.order_by(Student.student_id.desc())
        else:
            query = query.order_by(Student.student_id)
    elif sort_by == 'gpa':
        if sort_order == 'desc':
            query = query.order_by(Student.gpa.desc(), Student.last_name, Student.first_name)
        else:
            query = query.order_by(Student.gpa, Student.last_name, Student.first_name)
    else:
        # Default sorting
        query = query.order_by(Student.last_name, Student.first_name)
    
    # Get all students
    students = query.all()
    
    # Calculate additional stats for display
    total_students = len(students)
    students_with_accounts = len([s for s in students if s.user])
    students_without_accounts = total_students - students_with_accounts
    
    return render_template('management/role_dashboard.html', 
                         students=students,
                         search_query=search_query,
                         search_type=search_type,
                         grade_filter=grade_filter,
                         status_filter=status_filter,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_students=total_students,
                         students_with_accounts=students_with_accounts,
                         students_without_accounts=students_without_accounts,
                         section='students',
                         active_tab='students')

@management_blueprint.route('/teachers')
@login_required
@management_required
def teachers():
    # Get search parameters
    search_query = request.args.get('search', '').strip()
    search_type = request.args.get('search_type', 'all')
    department_filter = request.args.get('department', '')
    role_filter = request.args.get('role', '')
    employment_filter = request.args.get('employment', '')
    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'asc')
    
    # Build the query
    query = TeacherStaff.query
    
    # Apply search filter if query exists
    if search_query:
        if search_type == 'all':
            search_filter = db.or_(
                TeacherStaff.first_name.ilike(f'%{search_query}%'),
                TeacherStaff.last_name.ilike(f'%{search_query}%'),
                TeacherStaff.middle_initial.ilike(f'%{search_query}%'),
                TeacherStaff.email.ilike(f'%{search_query}%'),
                TeacherStaff.staff_id.ilike(f'%{search_query}%'),
                TeacherStaff.assigned_role.ilike(f'%{search_query}%'),
                TeacherStaff.department.ilike(f'%{search_query}%'),
                TeacherStaff.position.ilike(f'%{search_query}%'),
                TeacherStaff.subject.ilike(f'%{search_query}%'),
                TeacherStaff.employment_type.ilike(f'%{search_query}%'),
                TeacherStaff.phone.ilike(f'%{search_query}%'),
                TeacherStaff.street.ilike(f'%{search_query}%'),
                TeacherStaff.apt_unit.ilike(f'%{search_query}%'),
                TeacherStaff.city.ilike(f'%{search_query}%'),
                TeacherStaff.state.ilike(f'%{search_query}%'),
                TeacherStaff.zip_code.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_first_name.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_last_name.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_phone.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_email.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_relationship.ilike(f'%{search_query}%')
            )
        elif search_type == 'name':
            search_filter = db.or_(
                TeacherStaff.first_name.ilike(f'%{search_query}%'),
                TeacherStaff.last_name.ilike(f'%{search_query}%'),
                TeacherStaff.middle_initial.ilike(f'%{search_query}%')
            )
        elif search_type == 'contact':
            search_filter = db.or_(
                TeacherStaff.email.ilike(f'%{search_query}%'),
                TeacherStaff.phone.ilike(f'%{search_query}%')
            )
        elif search_type == 'role':
            search_filter = db.or_(
                TeacherStaff.assigned_role.ilike(f'%{search_query}%'),
                TeacherStaff.position.ilike(f'%{search_query}%')
            )
        elif search_type == 'department':
            search_filter = TeacherStaff.department.ilike(f'%{search_query}%')
        elif search_type == 'subject':
            search_filter = TeacherStaff.subject.ilike(f'%{search_query}%')
        elif search_type == 'address':
            search_filter = db.or_(
                TeacherStaff.street.ilike(f'%{search_query}%'),
                TeacherStaff.apt_unit.ilike(f'%{search_query}%'),
                TeacherStaff.city.ilike(f'%{search_query}%'),
                TeacherStaff.state.ilike(f'%{search_query}%'),
                TeacherStaff.zip_code.ilike(f'%{search_query}%')
            )
        elif search_type == 'emergency':
            search_filter = db.or_(
                TeacherStaff.emergency_first_name.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_last_name.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_phone.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_email.ilike(f'%{search_query}%'),
                TeacherStaff.emergency_relationship.ilike(f'%{search_query}%')
            )
        elif search_type == 'staff_id':
            search_filter = TeacherStaff.staff_id.ilike(f'%{search_query}%')
        elif search_type == 'employment':
            search_filter = TeacherStaff.employment_type.ilike(f'%{search_query}%')
        else:
            search_filter = db.or_(
                TeacherStaff.first_name.ilike(f'%{search_query}%'),
                TeacherStaff.last_name.ilike(f'%{search_query}%'),
                TeacherStaff.email.ilike(f'%{search_query}%'),
                TeacherStaff.assigned_role.ilike(f'%{search_query}%')
            )
        query = query.filter(search_filter)
    
    # Apply department filter
    if department_filter:
        query = query.filter(TeacherStaff.department.ilike(f'%{department_filter}%'))
    
    # Apply role filter
    if role_filter:
        query = query.filter(TeacherStaff.assigned_role.ilike(f'%{role_filter}%'))
    
    # Apply employment type filter
    if employment_filter:
        query = query.filter(TeacherStaff.employment_type == employment_filter)
    
    # Apply sorting
    if sort_by == 'name':
        if sort_order == 'desc':
            query = query.order_by(TeacherStaff.last_name.desc(), TeacherStaff.first_name.desc())
        else:
            query = query.order_by(TeacherStaff.last_name, TeacherStaff.first_name)
    elif sort_by == 'role':
        if sort_order == 'desc':
            query = query.order_by(TeacherStaff.assigned_role.desc())
        else:
            query = query.order_by(TeacherStaff.assigned_role)
    elif sort_by == 'department':
        if sort_order == 'desc':
            query = query.order_by(TeacherStaff.department.desc())
        else:
            query = query.order_by(TeacherStaff.department)
    elif sort_by == 'hire_date':
        if sort_order == 'desc':
            query = query.order_by(TeacherStaff.hire_date.desc())
        else:
            query = query.order_by(TeacherStaff.hire_date)
    else:
        query = query.order_by(TeacherStaff.last_name, TeacherStaff.first_name)
    
    teachers = query.all()
    
    # Calculate additional stats for display
    total_teachers = len(teachers)
    teachers_with_accounts = len([t for t in teachers if t.user])
    teachers_without_accounts = total_teachers - teachers_with_accounts
    
    return render_template('management/role_dashboard.html', 
                         teachers=teachers,
                         search_query=search_query,
                         search_type=search_type,
                         department_filter=department_filter,
                         role_filter=role_filter,
                         employment_filter=employment_filter,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_teachers=total_teachers,
                         teachers_with_accounts=teachers_with_accounts,
                         teachers_without_accounts=teachers_without_accounts,
                         section='teachers',
                         active_tab='teachers')

@management_blueprint.route('/classes')
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

@management_blueprint.route('/api/teachers')
@login_required
@management_required
def api_teachers():
    """API endpoint to get teachers for dropdowns."""
    teachers = TeacherStaff.query.all()
    return jsonify([{
        'id': teacher.id,
        'first_name': teacher.first_name,
        'last_name': teacher.last_name,
        'role': teacher.user.role if teacher.user else 'No Role'
    } for teacher in teachers])

@management_blueprint.route('/add-class', methods=['GET', 'POST'])
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
                return redirect(url_for('management.add_class'))
            
            # Get current school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash('Cannot create class: No active school year.', 'danger')
                return redirect(url_for('management.add_class'))
            
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
            
            db.session.commit()
            
            flash(f'Class "{name}" created successfully!', 'success')
            return redirect(url_for('management.classes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating class: {str(e)}', 'danger')
            return redirect(url_for('management.add_class'))
    
    # GET request - show form
    teachers = TeacherStaff.query.all()
    return render_template('management/add_class.html', available_teachers=teachers)

@management_blueprint.route('/class/<int:class_id>/manage')
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
    available_teachers = TeacherStaff.query.all()
    
    # Get today's date for age calculations
    today = date.today()
    
    return render_template('management/manage_class_roster.html', 
                         class_info=class_obj,
                         all_students=all_students,
                         enrolled_students=enrolled_students,
                         available_teachers=available_teachers,
                         today=today,
                         enrollments=enrollments)

@management_blueprint.route('/class/<int:class_id>/edit', methods=['GET', 'POST'])
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
            class_obj.schedule = request.form.get('schedule', '').strip() or None
            class_obj.max_students = request.form.get('max_students', 30, type=int)
            class_obj.description = request.form.get('description', '').strip() or None
            class_obj.is_active = 'is_active' in request.form
            
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
    teachers = TeacherStaff.query.all()
    return render_template('management/edit_class.html', class_info=class_obj, available_teachers=teachers)

@management_blueprint.route('/class/<int:class_id>/roster', methods=['GET', 'POST'])
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
    available_teachers = TeacherStaff.query.all()
    
    # Get today's date for age calculations
    today = date.today()
    
    return render_template('management/manage_class_roster.html', 
                         class_info=class_obj,
                         all_students=all_students,
                         enrolled_students=enrolled_students,
                         available_teachers=available_teachers,
                         today=today,
                         enrollments=enrollments)

@management_blueprint.route('/class/<int:class_id>/grades')
@login_required
@management_required
def class_grades(class_id):
    """View class grades."""
    from datetime import date
    import json
    
    class_obj = Class.query.get_or_404(class_id)
    
    # Get enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    # Get assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    
    # Get grades for enrolled students
    student_grades = {}
    for student in enrolled_students:
        student_grades[student.id] = {}
        for assignment in assignments:
            grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()
            if grade:
                try:
                    grade_data = json.loads(grade.grade_data)
                    student_grades[student.id][assignment.id] = {
                        'grade': grade_data.get('score', 'N/A'),
                        'comments': grade_data.get('comments', ''),
                        'graded_at': grade.graded_at
                    }
                except (json.JSONDecodeError, TypeError):
                    student_grades[student.id][assignment.id] = {
                        'grade': 'N/A',
                        'comments': 'Error parsing grade data',
                        'graded_at': grade.graded_at
                    }
            else:
                student_grades[student.id][assignment.id] = {
                    'grade': 'Not Graded',
                    'comments': '',
                    'graded_at': None
                }
    
    # Calculate averages for each student
    student_averages = {}
    for student_id, grades in student_grades.items():
        valid_grades = [float(g['grade']) for g in grades.values() 
                       if g['grade'] not in ['N/A', 'Not Graded'] and str(g['grade']).replace('.', '').isdigit()]
        if valid_grades:
            student_averages[student_id] = round(sum(valid_grades) / len(valid_grades), 2)
        else:
            student_averages[student_id] = 'N/A'
    
    return render_template('management/class_grades.html', 
                         class_info=class_obj,
                         enrolled_students=enrolled_students,
                         assignments=assignments,
                         student_grades=student_grades,
                         student_averages=student_averages,
                         today=date.today())

@management_blueprint.route('/class/<int:class_id>/remove', methods=['POST'])
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

@management_blueprint.route('/assignment/type-selector')
@login_required
@management_required
def assignment_type_selector():
    """Assignment type selection page for management"""
    return render_template('shared/assignment_type_selector.html')

@management_blueprint.route('/assignment/create/quiz', methods=['GET', 'POST'])
@login_required
@management_required
def create_quiz_assignment():
    """Create a quiz assignment - management version"""
    if request.method == 'POST':
        # Handle quiz assignment creation
        title = request.form.get('title')
        class_id = request.form.get('class_id', type=int)
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, class_id, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('management.create_quiz_assignment'))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('management.create_quiz_assignment'))
            
            # Get save and continue settings
            allow_save_and_continue = request.form.get('allow_save_and_continue') == 'on'
            max_save_attempts = int(request.form.get('max_save_attempts', 10))
            save_timeout_minutes = int(request.form.get('save_timeout_minutes', 30))
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                quarter=str(quarter),
                class_id=class_id,
                school_year_id=current_school_year.id,
                status='Active',
                assignment_type='quiz',
                allow_save_and_continue=allow_save_and_continue,
                max_save_attempts=max_save_attempts,
                save_timeout_minutes=save_timeout_minutes
            )
            
            db.session.add(new_assignment)
            db.session.flush()  # Get the assignment ID
            
            # Save quiz questions
            question_count = 0
            for key, value in request.form.items():
                if key.startswith('question_text_'):
                    question_id = key.split('_')[2]
                    question_text = value
                    question_type = request.form.get(f'question_type_{question_id}')
                    points = float(request.form.get(f'points_{question_id}', 1.0))
                    
                    # Create the question
                    question = QuizQuestion(
                        assignment_id=new_assignment.id,
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
                        for option_key, option_value in request.form.items():
                            if option_key.startswith(f'option_text_{question_id}_'):
                                option_text = option_value
                                option_id = option_key.split('_')[3]
                                is_correct = request.form.get(f'correct_answer_{question_id}') == option_id
                                
                                option = QuizOption(
                                    question_id=question.id,
                                    option_text=option_text,
                                    is_correct=is_correct,
                                    order=option_count
                                )
                                db.session.add(option)
                                option_count += 1
                    
                    question_count += 1
            
            db.session.commit()
            flash('Quiz assignment created successfully!', 'success')
            return redirect(url_for('management.assignments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating quiz assignment: {str(e)}', 'danger')
    
    # GET request - show form
    classes = Class.query.all()
    current_quarter = get_current_quarter()
    return render_template('shared/create_quiz_assignment.html', classes=classes, current_quarter=current_quarter)

@management_blueprint.route('/assignment/create/discussion', methods=['GET', 'POST'])
@login_required
@management_required
def create_discussion_assignment():
    """Create a discussion assignment - management version"""
    if request.method == 'POST':
        # Handle discussion assignment creation
        title = request.form.get('title')
        class_id = request.form.get('class_id', type=int)
        discussion_topic = request.form.get('discussion_topic')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, class_id, discussion_topic, due_date_str, quarter]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('management.create_discussion_assignment'))
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Get the active school year
            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash("Cannot create assignment: No active school year.", "danger")
                return redirect(url_for('management.create_discussion_assignment'))
            
            # Create the assignment
            new_assignment = Assignment(
                title=title,
                description=f"{discussion_topic}\n\n{description}",
                due_date=due_date,
                quarter=str(quarter),
                class_id=class_id,
                school_year_id=current_school_year.id,
                status='Active',
                assignment_type='discussion'
            )
            
            db.session.add(new_assignment)
            db.session.commit()
            
            # TODO: Save discussion settings, rubric, and prompts
            # This would require additional models for discussion settings, rubric criteria, etc.
            
            flash('Discussion assignment created successfully!', 'success')
            return redirect(url_for('management.assignments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating discussion assignment: {str(e)}', 'danger')
    
    # GET request - show form
    classes = Class.query.all()
    current_quarter = get_current_quarter()
    return render_template('shared/create_discussion_assignment.html', classes=classes, current_quarter=current_quarter)

@management_blueprint.route('/assignments')
@login_required
@management_required
def assignments():
    """Class-based assignments view for School Administrators and Directors"""
    from datetime import datetime
    
    # Get all classes
    all_classes = Class.query.all()
    
    # Get current user's role and permissions
    user_role = current_user.role
    user_id = current_user.id
    
    # Determine which classes the user can access
    if user_role == 'Director':
        # Directors can see all classes
        accessible_classes = all_classes
    elif user_role == 'School Administrator':
        # School Administrators can see all classes for assignment management
        accessible_classes = all_classes
    else:
        # Fallback - should not happen due to @management_required decorator
        accessible_classes = []
    
    # Get assignment counts for each class
    class_assignments = {}
    for class_obj in accessible_classes:
        assignment_count = Assignment.query.filter_by(class_id=class_obj.id).count()
        class_assignments[class_obj.id] = assignment_count
    
    return render_template('management/class_based_assignments.html',
                         classes=accessible_classes,
                         class_assignments=class_assignments,
                         user_role=user_role,
                         active_tab='assignments')

@management_blueprint.route('/assignments/class/<int:class_id>')
@login_required
@management_required
def class_assignments(class_id):
    """View assignments for a specific class"""
    from datetime import datetime
    
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

@management_blueprint.route('/assignments/legacy')
@login_required
@management_required
def assignments_legacy():
    """Management assignment view - similar to teacher assignments with filtering and sorting"""
    from datetime import datetime
    
    # Get all classes
    all_classes = Class.query.all()
    
    # Get current user's role and permissions
    user_role = current_user.role
    user_id = current_user.id
    
    # Determine which classes the user can access
    if user_role == 'Director':
        # Directors can see all classes
        accessible_classes = all_classes
        assignments_query = Assignment.query
    elif user_role == 'School Administrator':
        # School Administrators can see classes they teach + all assignments for viewing
        # First, find the TeacherStaff record for this user
        teacher_staff = None
        if current_user.teacher_staff_id:
            teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
        
        if teacher_staff:
            teacher_classes = Class.query.filter_by(teacher_id=teacher_staff.id).all()
            # If no classes assigned, assign them to the first available class for testing
            if not teacher_classes and all_classes:
                first_class = all_classes[0]
                first_class.teacher_id = teacher_staff.id
                db.session.commit()
                teacher_classes = [first_class]
        else:
            teacher_classes = []
        accessible_classes = teacher_classes
        
        # For assignments, they can see all assignments but only edit their own class assignments
        assignments_query = Assignment.query
    else:
        # Fallback - should not happen due to @management_required decorator
        accessible_classes = []
        assignments_query = Assignment.query.none()
    
    # Get filter parameters
    selected_class_id = request.args.get('class_id', '')
    selected_status = request.args.get('status', '')
    sort_by = request.args.get('sort', 'due_date')
    sort_order = request.args.get('order', 'desc')
    
    # Ensure selected_class_id is a string for template comparison
    selected_class_id = str(selected_class_id) if selected_class_id else ''
    
    # Build assignments query
    assignments_query = assignments_query.join(Class, Assignment.class_id == Class.id)
    
    # Apply filters
    if selected_class_id:
        assignments_query = assignments_query.filter(Assignment.class_id == selected_class_id)
    
    if selected_status:
        assignments_query = assignments_query.filter(Assignment.status == selected_status)
    
    # Apply sorting
    if sort_by == 'due_date':
        if sort_order == 'asc':
            assignments_query = assignments_query.order_by(Assignment.due_date.asc())
        else:
            assignments_query = assignments_query.order_by(Assignment.due_date.desc())
    elif sort_by == 'title':
        if sort_order == 'asc':
            assignments_query = assignments_query.order_by(Assignment.title.asc())
        else:
            assignments_query = assignments_query.order_by(Assignment.title.desc())
    elif sort_by == 'class':
        if sort_order == 'asc':
            assignments_query = assignments_query.order_by(Class.name.asc())
        else:
            assignments_query = assignments_query.order_by(Class.name.desc())
    
    # Get assignments
    assignments = assignments_query.all()
    
    # Get current date for status updates
    today = datetime.now().date()
    
    # Update assignment statuses (past due assignments become inactive)
    update_assignment_statuses()
    
    # Get teacher_staff_id for template use
    teacher_staff_id = None
    if user_role == 'School Administrator':
        if current_user.teacher_staff_id:
            teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
            if teacher_staff:
                teacher_staff_id = teacher_staff.id
    
    return render_template('management/management_assignments.html',
                         assignments=assignments,
                         classes=all_classes,
                         accessible_classes=accessible_classes,
                         user_role=user_role,
                         teacher_staff_id=teacher_staff_id,
                         today=today,
                         selected_class_id=selected_class_id,
                         selected_status=selected_status,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         active_tab='assignments')

@management_blueprint.route('/unified-attendance', methods=['GET', 'POST'])
@login_required
@management_required
def unified_attendance():
    """Unified attendance management combining school day, class period, and reports"""
    from datetime import datetime, date
    
    # Handle School Day Attendance POST requests
    if request.method == 'POST' and 'attendance_date' in request.form:
        attendance_date_str = request.form.get('attendance_date')
        if not attendance_date_str:
            flash('Please select a date.', 'danger')
            return redirect(url_for('management.unified_attendance'))
        
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
        
        # Get all students
        students = Student.query.all()
        
        # Process attendance records
        updated_count = 0
        created_count = 0
        
        for student in students:
            student_id = student.id
            status = request.form.get(f'status-{student_id}')
            notes = request.form.get(f'notes-{student_id}', '').strip()
            
            if status:
                # Check if record already exists
                existing_record = SchoolDayAttendance.query.filter_by(
                    student_id=student_id,
                    date=attendance_date
                ).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.status = status
                    existing_record.notes = notes
                    existing_record.recorded_by = current_user.id
                    existing_record.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new record
                    new_record = SchoolDayAttendance(
                        student_id=student_id,
                        date=attendance_date,
                        status=status,
                        notes=notes,
                        recorded_by=current_user.id
                    )
                    db.session.add(new_record)
                    created_count += 1
        
        try:
            db.session.commit()
            if created_count > 0 and updated_count > 0:
                flash(f'Successfully recorded attendance for {created_count} students and updated {updated_count} existing records.', 'success')
            elif created_count > 0:
                flash(f'Successfully recorded attendance for {created_count} students.', 'success')
            elif updated_count > 0:
                flash(f'Successfully updated attendance for {updated_count} students.', 'success')
            else:
                flash('No attendance changes were made.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving attendance: {str(e)}', 'danger')
        
        return redirect(url_for('management.unified_attendance', date=attendance_date_str))
    
    # GET request - show unified attendance form
    
    # School Day Attendance Data
    selected_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = datetime.now().date()
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    
    # Get all students
    students = Student.query.order_by(Student.last_name, Student.first_name).all()
    
    # Get existing attendance records for the selected date
    existing_records = {}
    if selected_date:
        records = SchoolDayAttendance.query.filter_by(date=selected_date).all()
        existing_records = {record.student_id: record for record in records}
    
    # Calculate school day statistics
    total_students = len(students)
    present_count = sum(1 for record in existing_records.values() if record.status == 'Present')
    absent_count = sum(1 for record in existing_records.values() if record.status == 'Absent')
    late_count = sum(1 for record in existing_records.values() if record.status == 'Late')
    excused_count = sum(1 for record in existing_records.values() if record.status == 'Excused Absence')
    
    attendance_stats = {
        'total': total_students,
        'present': present_count,
        'absent': absent_count,
        'late': late_count,
        'excused': excused_count
    }
    
    # Class Period Attendance Data
    classes = Class.query.all()
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # Calculate attendance stats for each class
    for class_obj in classes:
        # Get student count
        class_obj.student_count = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_obj.id,
            Enrollment.is_active == True
        ).count()
        
        # Check if attendance was taken today
        today_attendance = Attendance.query.filter_by(
            class_id=class_obj.id,
            date=datetime.now().date()
        ).count()
        class_obj.attendance_taken_today = today_attendance > 0
        
        # Get today's attendance stats
        if class_obj.attendance_taken_today:
            present_count = Attendance.query.filter_by(
                class_id=class_obj.id,
                date=datetime.now().date(),
                status='Present'
            ).count()
            absent_count = Attendance.query.filter(
                Attendance.class_id == class_obj.id,
                Attendance.date == datetime.now().date(),
                Attendance.status.in_(['Unexcused Absence', 'Excused Absence'])
            ).count()
            class_obj.today_present = present_count
            class_obj.today_absent = absent_count
        else:
            class_obj.today_present = 0
            class_obj.today_absent = 0
    
    # Calculate overall stats
    today_attendance_count = sum(1 for c in classes if c.attendance_taken_today)
    pending_classes_count = len(classes) - today_attendance_count
    
    # Calculate overall attendance rate
    total_attendance_records = Attendance.query.filter_by(date=datetime.now().date()).count()
    present_records = Attendance.query.filter_by(date=datetime.now().date(), status='Present').count()
    overall_attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
    
    # Attendance Reports Data
    all_students = Student.query.all()
    all_classes = Class.query.all()
    all_statuses = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']

    # Query and filter attendance records
    query = Attendance.query
    # (Filters can be added here in the future)
    records = query.all()

    # Calculate summary stats from the database
    summary_stats = {
        'total_records': len(records),
        'present': query.filter_by(status='Present').count(),
        'late': query.filter_by(status='Late').count(),
        'unexcused_absence': query.filter_by(status='Unexcused Absence').count(),
        'excused_absence': query.filter_by(status='Excused Absence').count(),
        'suspended': query.filter_by(status='Suspended').count()
    }
    
    return render_template('shared/unified_attendance.html',
                         students=students,
                         selected_date=selected_date,
                         selected_date_str=selected_date_str,
                         existing_records=existing_records,
                         attendance_stats=attendance_stats,
                         classes=classes,
                         today_date=today_date,
                         today_attendance_count=today_attendance_count,
                         pending_classes_count=pending_classes_count,
                         overall_attendance_rate=overall_attendance_rate,
                         all_students=all_students,
                         all_classes=all_classes,
                         all_statuses=all_statuses,
                         summary_stats=summary_stats,
                         records=records,
                         active_tab='attendance')

@management_blueprint.route('/mark-all-present/<int:class_id>', methods=['POST'])
@login_required
@management_required
def mark_all_present(class_id):
    """Mark all students as present for a specific class on a given date"""
    from datetime import datetime
    
    try:
        # Get the class
        class_obj = Class.query.get_or_404(class_id)
        
        # Get the date from form data or use today
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            attendance_date = datetime.now().date()
        
        # Get all enrolled students for this class
        enrolled_students = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_id,
            Enrollment.is_active == True
        ).all()
        
        if not enrolled_students:
            flash(f'No students enrolled in {class_obj.name}.', 'warning')
            return redirect(url_for('management.unified_attendance'))
        
        # Process each student
        updated_count = 0
        created_count = 0
        
        for student in enrolled_students:
            # Check if attendance record already exists
            existing_record = Attendance.query.filter_by(
                student_id=student.id,
                class_id=class_id,
                date=attendance_date
            ).first()
            
            if existing_record:
                # Update existing record to Present
                existing_record.status = 'Present'
                existing_record.notes = 'Marked all present'
                updated_count += 1
            else:
                # Create new record
                new_record = Attendance(
                    student_id=student.id,
                    class_id=class_id,
                    date=attendance_date,
                    status='Present',
                    notes='Marked all present',
                    teacher_id=class_obj.teacher_id
                )
                db.session.add(new_record)
                created_count += 1
        
        # Commit changes
        db.session.commit()
        
        if created_count > 0 and updated_count > 0:
            flash(f'Successfully marked {created_count + updated_count} students as present for {class_obj.name}.', 'success')
        elif created_count > 0:
            flash(f'Successfully marked {created_count} students as present for {class_obj.name}.', 'success')
        elif updated_count > 0:
            flash(f'Successfully updated {updated_count} students to present for {class_obj.name}.', 'success')
        else:
            flash(f'No students to mark present for {class_obj.name}.', 'info')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error marking students as present: {str(e)}', 'danger')
    
    # Redirect back to unified attendance
    return redirect(url_for('management.unified_attendance'))

@management_blueprint.route('/school-day-attendance', methods=['GET', 'POST'])
@login_required
@management_required
def school_day_attendance():
    """Manage school-day attendance for all students"""
    from datetime import datetime, date
    
    if request.method == 'POST':
        attendance_date_str = request.form.get('attendance_date')
        if not attendance_date_str:
            flash('Please select a date.', 'danger')
            return redirect(url_for('management.school_day_attendance'))
        
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
        
        # Get all students
        students = Student.query.all()
        
        # Process attendance records
        updated_count = 0
        created_count = 0
        
        for student in students:
            student_id = student.id
            status = request.form.get(f'status_{student_id}')
            notes = request.form.get(f'notes_{student_id}', '').strip()
            
            if status:
                # Check if record already exists
                existing_record = SchoolDayAttendance.query.filter_by(
                    student_id=student_id,
                    date=attendance_date
                ).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.status = status
                    existing_record.notes = notes
                    existing_record.recorded_by = current_user.id
                    existing_record.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new record
                    new_record = SchoolDayAttendance(
                        student_id=student_id,
                        date=attendance_date,
                        status=status,
                        notes=notes,
                        recorded_by=current_user.id
                    )
                    db.session.add(new_record)
                    created_count += 1
        
        try:
            db.session.commit()
            if created_count > 0 and updated_count > 0:
                flash(f'Successfully recorded attendance for {created_count} students and updated {updated_count} existing records.', 'success')
            elif created_count > 0:
                flash(f'Successfully recorded attendance for {created_count} students.', 'success')
            elif updated_count > 0:
                flash(f'Successfully updated attendance for {updated_count} students.', 'success')
            else:
                flash('No attendance changes were made.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving attendance: {str(e)}', 'danger')
        
        return redirect(url_for('management.school_day_attendance', date=attendance_date_str))
    
    # GET request - show attendance form
    selected_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = datetime.now().date()
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    
    # Get all students
    students = Student.query.order_by(Student.last_name, Student.first_name).all()
    
    # Get existing attendance records for the selected date
    existing_records = {}
    if selected_date:
        records = SchoolDayAttendance.query.filter_by(date=selected_date).all()
        existing_records = {record.student_id: record for record in records}
    
    # Calculate statistics
    total_students = len(students)
    present_count = sum(1 for record in existing_records.values() if record.status == 'Present')
    absent_count = sum(1 for record in existing_records.values() if record.status == 'Absent')
    late_count = sum(1 for record in existing_records.values() if record.status == 'Late')
    excused_count = sum(1 for record in existing_records.values() if record.status == 'Excused Absence')
    
    attendance_stats = {
        'total': total_students,
        'present': present_count,
        'absent': absent_count,
        'late': late_count,
        'excused': excused_count
    }
    
    return render_template('shared/school_day_attendance.html',
                         students=students,
                         selected_date=selected_date,
                         selected_date_str=selected_date_str,
                         existing_records=existing_records,
                         attendance_stats=attendance_stats)

@management_blueprint.route('/attendance')
@login_required
@management_required
def attendance():
    """Management attendance hub with improved interface."""
    # Get all classes
    classes = Class.query.all()
    
    # Get today's date
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # Calculate attendance stats for each class
    for class_obj in classes:
        # Get student count
        class_obj.student_count = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_obj.id,
            Enrollment.is_active == True
        ).count()
        
        # Check if attendance was taken today
        today_attendance = Attendance.query.filter_by(
            class_id=class_obj.id,
            date=datetime.now().date()
        ).count()
        class_obj.attendance_taken_today = today_attendance > 0
        
        # Get today's attendance stats
        if class_obj.attendance_taken_today:
            present_count = Attendance.query.filter_by(
                class_id=class_obj.id,
                date=datetime.now().date(),
                status='Present'
            ).count()
            absent_count = Attendance.query.filter(
                Attendance.class_id == class_obj.id,
                Attendance.date == datetime.now().date(),
                Attendance.status.in_(['Unexcused Absence', 'Excused Absence'])
            ).count()
            class_obj.today_present = present_count
            class_obj.today_absent = absent_count
        else:
            class_obj.today_present = 0
            class_obj.today_absent = 0
    
    # Calculate overall stats
    today_attendance_count = sum(1 for c in classes if c.attendance_taken_today)
    pending_classes_count = len(classes) - today_attendance_count
    
    # Calculate overall attendance rate
    total_attendance_records = Attendance.query.filter_by(date=datetime.now().date()).count()
    present_records = Attendance.query.filter_by(date=datetime.now().date(), status='Present').count()
    overall_attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
    
    return render_template('shared/attendance_hub_simple.html',
                         classes=classes,
                         today_date=today_date,
                         today_attendance_count=today_attendance_count,
                         pending_classes_count=pending_classes_count,
                         overall_attendance_rate=overall_attendance_rate,
                         section='attendance',
                         active_tab='attendance')

@management_blueprint.route('/attendance/reports')
@login_required
@management_required
def attendance_reports():
    all_students = Student.query.all()
    all_classes = Class.query.all()
    all_statuses = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']

    # Query and filter attendance records
    query = Attendance.query
    # (Filters can be added here in the future)
    records = query.all()

    # Calculate summary stats from the database
    summary_stats = {
        'total_records': len(records),
        'present': query.filter_by(status='Present').count(),
        'late': query.filter_by(status='Late').count(),
        'unexcused_absence': query.filter_by(status='Unexcused Absence').count(),
        'excused_absence': query.filter_by(status='Excused Absence').count(),
        'suspended': query.filter_by(status='Suspended').count()
    }

    return render_template('shared/attendance_report_view.html',
                         all_students=all_students,
                         all_classes=all_classes,
                         all_statuses=all_statuses,
                         selected_student_ids=[],
                         selected_class_ids=[],
                         selected_status='',
                         selected_start_date='',
                         selected_end_date='',
                         summary_stats=summary_stats,
                         records=records,
                         section='attendance_reports',
                         active_tab='attendance_reports')

@management_blueprint.route('/report-cards')
@login_required
@management_required
def report_cards():
    report_cards = ReportCard.query.all()
    school_years = SchoolYear.query.all()
    students = Student.query.all()
    classes = Class.query.all()
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    
    return render_template('management/role_dashboard.html', 
                         report_cards=report_cards,
                         school_years=school_years,
                         students=students,
                         classes=classes,
                         quarters=quarters,
                         section='report_cards',
                         active_tab='report_cards')

@management_blueprint.route('/admissions')
@login_required
@management_required
def admissions():
    return render_template('management/role_dashboard.html',
                         section='admissions',
                         active_tab='admissions')

@management_blueprint.route('/calendar')
@login_required
@management_required
def calendar():
    """School calendar view"""
    from datetime import datetime, timedelta
    import calendar as cal
    
    # Get current month/year from query params or use current date
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    # Calculate previous and next month
    current_date = datetime(year, month, 1)
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)
    
    # Create calendar data
    cal_obj = cal.monthcalendar(year, month)
    month_name = datetime(year, month, 1).strftime('%B')
    
    # Get academic dates for this month
    academic_dates = get_academic_dates_for_calendar(year, month)
    
    # Simple calendar data structure
    calendar_data = {
        'month_name': month_name,
        'year': year,
        'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'weeks': []
    }
    
    # Convert calendar to our format
    for week in cal_obj:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'day_num': '', 'is_current_month': False, 'is_today': False, 'events': []})
            else:
                is_today = (day == datetime.now().day and month == datetime.now().month and year == datetime.now().year)
                
                # Get events for this day
                day_events = []
                for academic_date in academic_dates:
                    if academic_date['day'] == day:
                        day_events.append({
                            'title': academic_date['title'],
                            'category': academic_date['category']
                        })
                
                week_data.append({'day_num': day, 'is_current_month': True, 'is_today': is_today, 'events': day_events})
        calendar_data['weeks'].append(week_data)
    
    # Get school years for the academic calendar management tab
    school_years = SchoolYear.query.order_by(SchoolYear.start_date.desc()).all()
    
    # Get active school year and add academic periods and calendar events data
    active_school_year = SchoolYear.query.filter_by(is_active=True).first()
    
    # Add academic periods to each school year
    for year in school_years:
        year.academic_periods = AcademicPeriod.query.filter_by(school_year_id=year.id, is_active=True).all()
        year.calendar_events = CalendarEvent.query.filter_by(school_year_id=year.id).all()
        if year.start_date and year.end_date:
            year.total_days = (year.end_date - year.start_date).days
    
    return render_template('management/role_calendar.html', 
                         calendar_data=calendar_data,
                         prev_month=prev_month,
                         next_month=next_month,
                         school_years=school_years,
                         active_school_year=active_school_year,
                         month_name=month_name,
                         year=year,
                         section='calendar',
                         active_tab='calendar')

@management_blueprint.route('/calendar/add-event', methods=['POST'])
@login_required
@management_required
def add_calendar_event():
    """Add a new calendar event"""
    flash('Calendar event functionality will be implemented soon!', 'info')
    return redirect(url_for('management.calendar'))

@management_blueprint.route('/calendar/delete-event/<int:event_id>', methods=['POST'])
@login_required
@management_required
def delete_calendar_event(event_id):
    """Delete a calendar event"""
    flash('Calendar event deletion will be implemented soon!', 'info')
    return redirect(url_for('management.calendar'))


# Teacher Work Day Management Routes
@management_blueprint.route('/calendar/teacher-work-days')
@login_required
@management_required
def teacher_work_days():
    """View and manage teacher work days"""
    # Get active school year
    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        flash('No active school year found.', 'warning')
        return redirect(url_for('management.calendar'))
    
    # Get all teacher work days for the active school year
    work_days = TeacherWorkDay.query.filter_by(school_year_id=active_year.id).order_by(TeacherWorkDay.date).all()
    
    return render_template('management/management_teacher_work_days.html',
                         work_days=work_days,
                         school_year=active_year,
                         section='calendar',
                         active_tab='calendar')


@management_blueprint.route('/calendar/teacher-work-days/add', methods=['POST'])
@login_required
@management_required
def add_teacher_work_days():
    """Add multiple teacher work days"""
    try:
        dates_str = request.form.get('dates', '').strip()
        title = request.form.get('title', '').strip()
        attendance_requirement = request.form.get('attendance_requirement', 'Mandatory')
        description = request.form.get('description', '').strip()
        
        if not dates_str or not title:
            flash('Dates and title are required.', 'danger')
            return redirect(url_for('management.teacher_work_days'))
        
        # Get active school year
        active_year = SchoolYear.query.filter_by(is_active=True).first()
        if not active_year:
            flash('No active school year found.', 'danger')
            return redirect(url_for('management.teacher_work_days'))
        
        # Parse dates (comma-separated)
        dates = [date.strip() for date in dates_str.split(',')]
        added_count = 0
        
        for date_str in dates:
            try:
                # Parse date (assuming format: MM/DD/YYYY or YYYY-MM-DD)
                if '/' in date_str:
                    # MM/DD/YYYY format
                    month, day, year = date_str.strip().split('/')
                    date_obj = datetime.strptime(f"{year}-{month.zfill(2)}-{day.zfill(2)}", "%Y-%m-%d").date()
                else:
                    # YYYY-MM-DD format
                    date_obj = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
                
                # Check if work day already exists for this date
                existing = TeacherWorkDay.query.filter_by(
                    school_year_id=active_year.id,
                    date=date_obj
                ).first()
                
                if not existing:
                    work_day = TeacherWorkDay(
                        school_year_id=active_year.id,
                        date=date_obj,
                        title=title,
                        attendance_requirement=attendance_requirement,
                        description=description
                    )
                    db.session.add(work_day)
                    added_count += 1
                
            except ValueError:
                flash(f'Invalid date format: {date_str}. Use MM/DD/YYYY or YYYY-MM-DD format.', 'warning')
                continue
        
        db.session.commit()
        flash(f'Successfully added {added_count} teacher work day(s).', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding teacher work days: {str(e)}', 'danger')
    
    return redirect(url_for('management.teacher_work_days'))


@management_blueprint.route('/calendar/teacher-work-days/delete/<int:work_day_id>', methods=['POST'])
@login_required
@management_required
def delete_teacher_work_day(work_day_id):
    """Delete a teacher work day"""
    try:
        work_day = TeacherWorkDay.query.get_or_404(work_day_id)
        db.session.delete(work_day)
        db.session.commit()
        flash('Teacher work day deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting teacher work day: {str(e)}', 'danger')
    
    return redirect(url_for('management.teacher_work_days'))


# School Break Management Routes
@management_blueprint.route('/calendar/school-breaks')
@login_required
@management_required
def school_breaks():
    """View and manage school breaks"""
    # Get active school year
    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        flash('No active school year found.', 'warning')
        return redirect(url_for('management.calendar'))
    
    # Get all school breaks for the active school year
    breaks = SchoolBreak.query.filter_by(school_year_id=active_year.id).order_by(SchoolBreak.start_date).all()
    
    return render_template('management/management_school_breaks.html',
                         breaks=breaks,
                         school_year=active_year,
                         section='calendar',
                         active_tab='calendar')


@management_blueprint.route('/calendar/school-breaks/add', methods=['POST'])
@login_required
@management_required
def add_school_break():
    """Add a school break"""
    try:
        name = request.form.get('name', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        break_type = request.form.get('break_type', 'Vacation')
        description = request.form.get('description', '').strip()
        
        if not all([name, start_date_str, end_date_str]):
            flash('Name, start date, and end date are required.', 'danger')
            return redirect(url_for('management.school_breaks'))
        
        # Get active school year
        active_year = SchoolYear.query.filter_by(is_active=True).first()
        if not active_year:
            flash('No active school year found.', 'danger')
            return redirect(url_for('management.school_breaks'))
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        if start_date > end_date:
            flash('Start date must be before or equal to end date.', 'danger')
            return redirect(url_for('management.school_breaks'))
        
        # Check if break already exists for this date range
        existing = SchoolBreak.query.filter(
            SchoolBreak.school_year_id == active_year.id,
            SchoolBreak.start_date <= end_date,
            SchoolBreak.end_date >= start_date
        ).first()
        
        if not existing:
            school_break = SchoolBreak(
                school_year_id=active_year.id,
                name=name,
                start_date=start_date,
                end_date=end_date,
                break_type=break_type,
                description=description
            )
            db.session.add(school_break)
            db.session.commit()
            flash('School break added successfully.', 'success')
        else:
            flash('A break already exists for this date range.', 'warning')
        
    except ValueError:
        flash('Invalid date format. Use YYYY-MM-DD format.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding school break: {str(e)}', 'danger')
    
    return redirect(url_for('management.school_breaks'))


@management_blueprint.route('/calendar/school-breaks/delete/<int:break_id>', methods=['POST'])
@login_required
@management_required
def delete_school_break(break_id):
    """Delete a school break"""
    try:
        school_break = SchoolBreak.query.get_or_404(break_id)
        db.session.delete(school_break)
        db.session.commit()
        flash('School break deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting school break: {str(e)}', 'danger')
    
    return redirect(url_for('management.school_breaks'))


@management_blueprint.route('/communications')
@login_required
@management_required
def communications():
    """Communications tab - Under Development."""
    return render_template('shared/under_development.html',
                         section='communications',
                         active_tab='communications')


@management_blueprint.route('/communications/messages')
@login_required
@management_required
def management_messages():
    """View all messages for management."""
    # Get all messages for the admin
    messages = Message.query.filter(
        (Message.recipient_id == current_user.id) |
        (Message.sender_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    
    return render_template('management/management_messages.html',
                         messages=messages,
                         section='communications',
                         active_tab='messages')


@management_blueprint.route('/communications/messages/send', methods=['GET', 'POST'])
@login_required
@management_required
def management_send_message():
    """Send a new message."""
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id', type=int)
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        
        if not recipient_id or not subject or not content:
            flash('Recipient, subject, and content are required.', 'error')
            return redirect(url_for('management.management_send_message'))
        
        # Create message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            message_type='direct'
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Create notification for recipient
        notification = Notification(
            user_id=recipient_id,
            type='new_message',
            title=f'New message from {current_user.username}',
            message=subject,
            message_id=message.id
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('management.management_messages'))
    
    # Get all users for recipient selection
    users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('management/management_send_message.html',
                         users=users,
                         section='communications',
                         active_tab='messages')


@management_blueprint.route('/communications/messages/<int:message_id>')
@login_required
@management_required
def management_view_message(message_id):
    """View a specific message."""
    message = Message.query.get_or_404(message_id)
    
    # Ensure the user is the sender or recipient
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        abort(403)
    
    # Mark as read if user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('management/management_view_message.html',
                         message=message,
                         section='communications',
                         active_tab='messages')


@management_blueprint.route('/communications/messages/<int:message_id>/reply', methods=['POST'])
@login_required
@management_required
def management_reply_to_message(message_id):
    """Reply to a message."""
    original_message = Message.query.get_or_404(message_id)
    
    # Ensure the user is the sender or recipient
    if original_message.sender_id != current_user.id and original_message.recipient_id != current_user.id:
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Reply content is required.', 'error')
        return redirect(url_for('management.management_view_message', message_id=message_id))
    
    # Determine recipient (reply to the other person in the conversation)
    recipient_id = original_message.sender_id if original_message.recipient_id == current_user.id else original_message.recipient_id
    
    # Create reply message
    reply = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        subject=f'Re: {original_message.subject}',
        content=content,
        message_type='direct',
        parent_message_id=message_id
    )
    
    db.session.add(reply)
    db.session.commit()
    
    # Create notification for recipient
    notification = Notification(
        user_id=recipient_id,
        type='new_message',
        title=f'Reply from {current_user.username}',
        message=content[:100] + '...' if len(content) > 100 else content,
        message_id=reply.id
    )
    db.session.add(notification)
    db.session.commit()
    
    flash('Reply sent successfully!', 'success')
    return redirect(url_for('management.management_view_message', message_id=message_id))


@management_blueprint.route('/communications/groups')
@login_required
@management_required
def management_groups():
    """View and manage message groups."""
    # Get all groups
    groups = MessageGroup.query.filter_by(is_active=True).all()
    
    # Get user's group memberships
    memberships = MessageGroupMember.query.filter_by(user_id=current_user.id).all()
    
    return render_template('management/management_groups.html',
                         groups=groups,
                         memberships=memberships,
                         section='communications',
                         active_tab='groups')


@management_blueprint.route('/communications/groups/create', methods=['GET', 'POST'])
@login_required
@management_required
def management_create_group():
    """Create a new message group."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        member_ids = request.form.getlist('members')
        
        if not name:
            flash('Group name is required.', 'error')
            return redirect(url_for('management.management_create_group'))
        
        # Create group
        group = MessageGroup(
            name=name,
            description=description,
            created_by=current_user.id,
            is_active=True
        )
        db.session.add(group)
        db.session.flush()
        
        # Add creator as member
        creator_member = MessageGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            role='admin'
        )
        db.session.add(creator_member)
        
        # Add other members
        for member_id in member_ids:
            if int(member_id) != current_user.id:
                member = MessageGroupMember(
                    group_id=group.id,
                    user_id=int(member_id),
                    role='member'
                )
                db.session.add(member)
        
        db.session.commit()
        
        flash('Group created successfully!', 'success')
        return redirect(url_for('management.management_groups'))
    
    # Get all users for member selection
    users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('management/management_create_group.html',
                         users=users,
                         section='communications',
                         active_tab='groups')


@management_blueprint.route('/communications/groups/<int:group_id>')
@login_required
@management_required
def management_view_group(group_id):
    """View a specific group and its messages."""
    group = MessageGroup.query.get_or_404(group_id)
    
    # Check if user is member of this group
    membership = MessageGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        abort(403)
    
    # Get group messages
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.created_at.desc()).all()
    
    # Get group members
    members = MessageGroupMember.query.filter_by(group_id=group_id).all()
    
    return render_template('management/management_view_group.html',
                         group=group,
                         messages=messages,
                         members=members,
                         membership=membership,
                         section='communications',
                         active_tab='groups')


@management_blueprint.route('/communications/groups/<int:group_id>/send', methods=['POST'])
@login_required
@management_required
def management_send_group_message(group_id):
    """Send a message to a group."""
    group = MessageGroup.query.get_or_404(group_id)
    
    # Check if user is member of this group
    membership = MessageGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Message content is required.', 'error')
        return redirect(url_for('management.management_view_group', group_id=group_id))
    
    # Create group message
    message = Message(
        sender_id=current_user.id,
        content=content,
        message_type='group',
        group_id=group_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Create notifications for all group members except sender
    members = MessageGroupMember.query.filter_by(group_id=group_id).all()
    for member in members:
        if member.user_id != current_user.id and not member.is_muted:
            notification = Notification(
                user_id=member.user_id,
                type='group_message',
                title=f'New message in {group.name}',
                message=content[:100] + '...' if len(content) > 100 else content,
                message_id=message.id
            )
            db.session.add(notification)
    
    db.session.commit()
    
    flash('Message sent to group!', 'success')
    return redirect(url_for('management.management_view_group', group_id=group_id))


@management_blueprint.route('/communications/announcements/create', methods=['GET', 'POST'])
@login_required
@management_required
def management_create_announcement():
    """Create a new announcement."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        is_important = request.form.get('is_important', type=bool)
        requires_confirmation = request.form.get('requires_confirmation', type=bool)
        rich_content = request.form.get('rich_content', '')
        
        if not title or not message:
            flash('Title and message are required.', 'error')
            return redirect(url_for('management.management_create_announcement'))
        
        # Create announcement
        announcement = Announcement(
            title=title,
            message=message,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id,
            is_important=is_important,
            requires_confirmation=requires_confirmation,
            rich_content=rich_content
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement created successfully!', 'success')
        return redirect(url_for('management.communications'))
    
    classes = Class.query.all()
    
    return render_template('management/management_create_announcement.html',
                         classes=classes,
                         section='communications',
                         active_tab='announcements')


@management_blueprint.route('/communications/announcements/schedule', methods=['GET', 'POST'])
@login_required
@management_required
def management_schedule_announcement():
    """Schedule an announcement for future delivery."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        scheduled_for = request.form.get('scheduled_for')
        
        if not title or not message or not scheduled_for:
            flash('Title, message, and scheduled time are required.', 'error')
            return redirect(url_for('management.management_schedule_announcement'))
        
        try:
            scheduled_datetime = datetime.strptime(scheduled_for, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'error')
            return redirect(url_for('management.management_schedule_announcement'))
        
        # Create scheduled announcement
        scheduled = ScheduledAnnouncement(
            title=title,
            message=message,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id,
            scheduled_for=scheduled_datetime
        )
        
        db.session.add(scheduled)
        db.session.commit()
        
        flash('Announcement scheduled successfully!', 'success')
        return redirect(url_for('management.communications'))
    
    classes = Class.query.all()
    
    return render_template('management/management_schedule_announcement.html',
                         classes=classes,
                         section='communications',
                         active_tab='announcements')


@management_blueprint.route('/communications/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
@management_required
def management_mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    
    flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('management.communications'))


@management_blueprint.route('/communications/messages/mark-read/<int:message_id>', methods=['POST'])
@login_required
@management_required
def management_mark_message_read(message_id):
    """Mark a message as read."""
    message = Message.query.get_or_404(message_id)
    
    # Ensure the message belongs to the current user
    if message.recipient_id != current_user.id:
        abort(403)
    
    message.is_read = True
    message.read_at = datetime.utcnow()
    db.session.commit()
    
    flash('Message marked as read.', 'success')
    return redirect(request.referrer or url_for('management.management_messages'))


@management_blueprint.route('/billing')
@login_required
@management_required
def billing():
    """Billing and financials management"""
    # Dummy data for now
    students = Student.query.all()
    invoices = []  # Will be populated when billing models are created
    pending_invoices = []
    
    return render_template('management/role_dashboard.html',
                         students=students,
                         invoices=invoices,
                         pending_invoices=pending_invoices,
                         total_revenue=0,
                         total_payments=0,
                         outstanding_balance=0,
                         active_invoices=0,
                         section='billing',
                         active_tab='billing')


@management_blueprint.route('/billing/add-invoice', methods=['POST'])
@login_required
@management_required
def add_invoice():
    """Add a new invoice"""
    flash('Invoice creation functionality will be implemented soon!', 'info')
    return redirect(url_for('management.billing'))


@management_blueprint.route('/billing/record-payment', methods=['POST'])
@login_required
@management_required
def record_payment():
    """Record a payment"""
    flash('Payment recording functionality will be implemented soon!', 'info')
    return redirect(url_for('management.billing'))


@management_blueprint.route('/settings')
@login_required
@management_required
def settings():
    return render_template('management/role_dashboard.html',
                         section='settings',
                         active_tab='settings')







@management_blueprint.route('/class-grades-view/<int:class_id>')
@login_required
@management_required
def class_grades_view(class_id):
    """View class grades"""
    return render_template('students/class_grades_view.html', class_id=class_id)




@management_blueprint.route('/add-assignment', methods=['GET', 'POST'])
@login_required
@management_required
def add_assignment():
    """Add a new assignment"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        class_id = request.form.get('class_id', type=int)
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        status = request.form.get('status', 'Active')
        
        if not all([title, class_id, due_date_str, quarter]):
            flash("Title, Class, Due Date, and Quarter are required.", "danger")
            return redirect(request.url)
        
        # Validate status
        valid_statuses = ['Active', 'Inactive', 'Voided']
        if status not in valid_statuses:
            flash('Invalid assignment status.', 'danger')
            return redirect(request.url)

        # Type assertion for due_date_str
        assert due_date_str is not None
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        
        current_school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_school_year:
            flash("Cannot create assignment: No active school year.", "danger")
            return redirect(request.url)

        # Type assertion for quarter
        assert quarter is not None
        
        # Create assignment using attribute assignment
        new_assignment = Assignment()
        new_assignment.title = title
        new_assignment.description = description
        new_assignment.due_date = due_date
        new_assignment.class_id = class_id
        new_assignment.school_year_id = current_school_year.id
        new_assignment.quarter = str(quarter)
        new_assignment.status = status
        
        # Handle file upload
        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Type assertion for filename
                    assert file.filename is not None
                    filename = secure_filename(file.filename)
                    # Create a unique filename to avoid collisions
                    unique_filename = f"assignment_{class_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    try:
                        file.save(filepath)
                        
                        # Save file information to assignment
                        new_assignment.attachment_filename = unique_filename
                        new_assignment.attachment_original_filename = filename
                        new_assignment.attachment_file_path = filepath
                        new_assignment.attachment_file_size = os.path.getsize(filepath)
                        new_assignment.attachment_mime_type = file.content_type
                        
                    except Exception as e:
                        flash(f'Error saving file: {str(e)}', 'danger')
                        return redirect(request.url)
                else:
                    flash(f'File type not allowed. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
                    return redirect(request.url)
        
        db.session.add(new_assignment)
        db.session.commit()
        
        flash('Assignment created successfully.', 'success')
        return redirect(url_for('management.assignments'))

    # For GET request, get all classes for the dropdown and current quarter
    classes = Class.query.all()
    current_quarter = get_current_quarter()
    return render_template('shared/add_assignment.html', classes=classes, current_quarter=current_quarter)


@management_blueprint.route('/grade/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@management_required
def grade_assignment(assignment_id):
    """Grade an assignment - Directors and School Administrators can grade assignments for classes they teach"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Authorization check - Directors and School Administrators can grade any assignment
    if current_user.role not in ['Director', 'School Administrator']:
        flash("You are not authorized to grade assignments.", "danger")
        return redirect(url_for('management.assignments'))
    
    # Get only students enrolled in this specific class
    enrolled_students = db.session.query(Student).join(Enrollment).filter(
        Enrollment.class_id == class_obj.id,
        Enrollment.is_active == True
    ).order_by(Student.last_name, Student.first_name).all()
    
    if not enrolled_students:
        flash("No students are currently enrolled in this class.", "warning")
        return redirect(url_for('management.assignments'))
    
    students = enrolled_students
    
    if request.method == 'POST':
        for student in students:
            score = request.form.get(f'score_{student.id}')
            comment = request.form.get(f'comment_{student.id}')
            
            if score is not None:
                try:
                    score_val = float(score) if score else 0.0
                    grade_data = json.dumps({'score': score_val, 'comment': comment})
                    
                    grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment_id).first()
                    if grade:
                        grade.grade_data = grade_data
                    else:
                        # Create grade using attribute assignment
                        grade = Grade()
                        grade.student_id = student.id
                        grade.assignment_id = assignment_id
                        grade.grade_data = grade_data
                        db.session.add(grade)
                    
                    # Create notification for the student
                    if student.user:
                        from app import create_notification
                        create_notification(
                            user_id=student.user.id,
                            notification_type='grade',
                            title=f'Grade posted for {assignment.title}',
                            message=f'Your grade for "{assignment.title}" has been posted. Score: {score_val}%',
                            link=url_for('student.student_grades')
                        )
                        
                except ValueError:
                    flash(f"Invalid score format for student {student.id}.", "warning")
                    continue # Skip this student and continue with others
        
        db.session.commit()
        flash('Grades updated successfully.', 'success')
        return redirect(url_for('management.grade_assignment', assignment_id=assignment_id))

    # Get existing grades for this assignment
    grades = {g.student_id: json.loads(g.grade_data) for g in Grade.query.filter_by(assignment_id=assignment_id).all()}
    submissions = {s.student_id: s for s in Submission.query.filter_by(assignment_id=assignment_id).all()}
    
    return render_template('teachers/teacher_grade_assignment.html', 
                         assignment=assignment, 
                         class_obj=class_obj,
                         students=students, 
                         grades=grades, 
                         submissions=submissions,
                         role_prefix=None)


@management_blueprint.route('/view-assignment/<int:assignment_id>')
@login_required
@management_required
def view_assignment(assignment_id):
    """View assignment details"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Get class information
    class_info = Class.query.get(assignment.class_id) if assignment.class_id else None
    teacher = None
    if class_info and class_info.teacher_id:
        teacher = TeacherStaff.query.get(class_info.teacher_id)
    
    # Get submissions count (if any)
    submissions_count = 0  # This would be implemented when submission system is added
    
    # Get current date for status calculations
    today = datetime.now().date()
    
    return render_template('shared/view_assignment.html', 
                         assignment=assignment,
                         class_info=class_info,
                         teacher=teacher,
                         submissions_count=submissions_count,
                         today=today)


@management_blueprint.route('/edit-assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@management_required
def edit_assignment(assignment_id):
    """Edit an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Authorization check - Directors and School Administrators can edit any assignment
    if current_user.role not in ['Director', 'School Administrator']:
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('management.assignments'))
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        status = request.form.get('status', 'Active')
        
        if not all([title, due_date_str, quarter]):
            flash('Title, Due Date, and Quarter are required.', 'danger')
            return redirect(request.url)
        
        # Validate status
        valid_statuses = ['Active', 'Inactive', 'Voided']
        if status not in valid_statuses:
            flash('Invalid assignment status.', 'danger')
            return redirect(request.url)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Update assignment
            assignment.title = title
            assignment.description = description
            assignment.due_date = due_date
            assignment.quarter = int(quarter)
            assignment.status = status
            
            # Handle file upload
            if 'assignment_file' in request.files:
                file = request.files['assignment_file']
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"assignment_{assignment.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        try:
                            file.save(filepath)
                            
                            # Update file information
                            assignment.attachment_filename = unique_filename
                            assignment.attachment_original_filename = filename
                        except Exception as e:
                            flash(f'Error saving file: {str(e)}', 'danger')
                            return redirect(request.url)
            
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('management.assignments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating assignment: {str(e)}', 'danger')
            return redirect(request.url)
    
    # For GET request, get all classes for the dropdown
    classes = Class.query.all()
    school_years = SchoolYear.query.all()
    
    return render_template('shared/edit_assignment.html', 
                         assignment=assignment,
                         classes=classes,
                         school_years=school_years)


@management_blueprint.route('/assignment/remove/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def remove_assignment_alt(assignment_id):
    """Remove an assignment - alternative route"""
    return remove_assignment(assignment_id)

@management_blueprint.route('/remove-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Authorization check - Directors and School Administrators can remove any assignment
    if current_user.role not in ['Director', 'School Administrator']:
        flash("You are not authorized to remove this assignment.", "danger")
        return redirect(url_for('management.assignments'))
    
    try:
        # Delete the assignment file if it exists
        if assignment.attachment_filename:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], assignment.attachment_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Delete the assignment from database
        db.session.delete(assignment)
        db.session.commit()
        
        flash('Assignment removed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing assignment: {str(e)}', 'danger')
    
    return redirect(url_for('management.assignments'))


@management_blueprint.route('/assignment/change-status/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def change_assignment_status(assignment_id):
    """Change assignment status"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Authorization check - Directors and School Administrators can change any assignment status
    if current_user.role not in ['Director', 'School Administrator']:
        return jsonify({'success': False, 'message': 'You are not authorized to change assignment status.'})
    
    new_status = request.form.get('status')
    
    # Validate status
    valid_statuses = ['Active', 'Inactive', 'Voided']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': 'Invalid status selected.'})
    
    try:
        assignment.status = new_status
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Assignment status changed to {new_status} successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error changing assignment status: {str(e)}'})

@management_blueprint.route('/class/<int:class_id>/students')
@login_required
@management_required
def get_class_students(class_id):
    """Get students for a specific class"""
    try:
        # Get students enrolled in this class
        students = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_id,
            Enrollment.is_active == True
        ).order_by(Student.last_name, Student.first_name).all()
        
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name
            })
        
        return jsonify({'success': True, 'students': students_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@management_blueprint.route('/assignment/grant-extensions', methods=['POST'])
@login_required
@management_required
def grant_extensions():
    """Grant extensions to students for an assignment"""
    try:
        assignment_id = request.form.get('assignment_id', type=int)
        class_id = request.form.get('class_id', type=int)
        extended_due_date_str = request.form.get('extended_due_date')
        reason = request.form.get('reason', '')
        student_ids = request.form.getlist('student_ids')
        
        if not all([assignment_id, class_id, extended_due_date_str, student_ids]):
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Parse the extended due date
        extended_due_date = datetime.strptime(extended_due_date_str, '%Y-%m-%dT%H:%M')
        
        # Get the assignment
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Authorization check - Directors and School Administrators can grant extensions for any assignment
        if current_user.role not in ['Director', 'School Administrator']:
            return jsonify({'success': False, 'message': 'You are not authorized to grant extensions.'})
        
        # Get the current user (who is granting the extensions)
        granter_id = current_user.id
        
        granted_count = 0
        
        for student_id in student_ids:
            try:
                student_id = int(student_id)
                
                # Deactivate any existing active extensions for this student and assignment
                existing_extensions = AssignmentExtension.query.filter_by(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    is_active=True
                ).all()
                
                for ext in existing_extensions:
                    ext.is_active = False
                
                # Create new extension
                extension = AssignmentExtension(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    extended_due_date=extended_due_date,
                    reason=reason,
                    granted_by=granter_id,
                    is_active=True
                )
                
                db.session.add(extension)
                granted_count += 1
                
            except (ValueError, TypeError):
                continue  # Skip invalid student IDs
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully granted extensions to {granted_count} student(s).',
            'granted_count': granted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@management_blueprint.route('/view-student/<int:student_id>')
@login_required
@management_required
def view_student(student_id):
    """View detailed student information"""
    student = Student.query.get_or_404(student_id)
    
    # Calculate age from DOB
    age = None
    if student.dob:
        try:
            dob_date = datetime.strptime(student.dob, '%Y-%m-%d')
            age = (datetime.now() - dob_date).days // 365
        except:
            pass
    
    # Get assigned classes
    assigned_classes = []
    if hasattr(student, 'enrollments'):
        for enrollment in student.enrollments:
            assigned_classes.append({
                'name': enrollment.class_info.name,
                'subject': enrollment.class_info.subject
            })
    
    # Get GPA from student record (updated by scheduler)
    gpa = student.gpa if student.gpa is not None else 0.0
    
    return jsonify({
        'id': student.id,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'dob': student.dob,
        'age': age,
        'grade_level': student.grade_level,
        'student_id': student.student_id,
        'email': student.email,
        'gpa': gpa,
        'assigned_classes': assigned_classes,
        'photo_filename': student.photo_filename,
        
        # Parent 1 information
        'parent1_first_name': student.parent1_first_name,
        'parent1_last_name': student.parent1_last_name,
        'parent1_email': student.parent1_email,
        'parent1_phone': student.parent1_phone,
        'parent1_relationship': student.parent1_relationship,
        
        # Parent 2 information
        'parent2_first_name': student.parent2_first_name,
        'parent2_last_name': student.parent2_last_name,
        'parent2_email': student.parent2_email,
        'parent2_phone': student.parent2_phone,
        'parent2_relationship': student.parent2_relationship,
        
        # Emergency contact
        'emergency_first_name': student.emergency_first_name,
        'emergency_last_name': student.emergency_last_name,
        'emergency_email': student.emergency_email,
        'emergency_phone': student.emergency_phone,
        'emergency_relationship': student.emergency_relationship,
        
        # Address
        'street': student.street,
        'apt_unit': student.apt_unit,
        'city': student.city,
        'state': student.state,
        'zip_code': student.zip_code
    })


@management_blueprint.route('/edit-student/<int:student_id>', methods=['POST'])
@login_required
@management_required
def edit_student(student_id):
    """Edit student information via AJAX modal"""
    student = Student.query.get_or_404(student_id)
    try:
        # Basic info
        student.dob = request.form.get('dob', student.dob)
        student.grade_level = request.form.get('grade_level', student.grade_level)
        # State ID is disabled, so we don't update it
        
        # Parent 1 information
        student.parent1_first_name = request.form.get('parent1_first_name', student.parent1_first_name)
        student.parent1_last_name = request.form.get('parent1_last_name', student.parent1_last_name)
        student.parent1_email = request.form.get('parent1_email', student.parent1_email)
        student.parent1_phone = request.form.get('parent1_phone', student.parent1_phone)
        student.parent1_relationship = request.form.get('parent1_relationship', student.parent1_relationship)
        
        # Parent 2 information
        student.parent2_first_name = request.form.get('parent2_first_name', student.parent2_first_name)
        student.parent2_last_name = request.form.get('parent2_last_name', student.parent2_last_name)
        student.parent2_email = request.form.get('parent2_email', student.parent2_email)
        student.parent2_phone = request.form.get('parent2_phone', student.parent2_phone)
        student.parent2_relationship = request.form.get('parent2_relationship', student.parent2_relationship)
        
        # Emergency contact
        student.emergency_first_name = request.form.get('emergency_first_name', student.emergency_first_name)
        student.emergency_last_name = request.form.get('emergency_last_name', student.emergency_last_name)
        student.emergency_email = request.form.get('emergency_email', student.emergency_email)
        student.emergency_phone = request.form.get('emergency_phone', student.emergency_phone)
        student.emergency_relationship = request.form.get('emergency_relationship', student.emergency_relationship)
        
        # Address
        student.street = request.form.get('street', student.street)
        student.apt_unit = request.form.get('apt_unit', student.apt_unit)
        student.city = request.form.get('city', student.city)
        student.state = request.form.get('state', student.state)
        student.zip_code = request.form.get('zip_code', student.zip_code)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Student updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@management_blueprint.route('/view-teacher/<int:teacher_id>')
@login_required
@management_required
def view_teacher(teacher_id):
    """View detailed teacher/staff information"""
    teacher = TeacherStaff.query.get_or_404(teacher_id)
    
    # Get assigned classes
    assigned_classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    # Count students in all assigned classes (placeholder)
    total_students = 0
    for class_info in assigned_classes:
        # This would need to be implemented based on enrollment system
        total_students += 0  # Placeholder
    
    # Get role from user account
    role = teacher.user.role if teacher.user else "No Account"
    
    # Format emergency contact information
    emergency_contact = "Not available"
    if teacher.emergency_first_name and teacher.emergency_last_name:
        emergency_contact = f"{teacher.emergency_first_name} {teacher.emergency_last_name}"
        if teacher.emergency_relationship:
            emergency_contact += f" ({teacher.emergency_relationship})"
        if teacher.emergency_phone:
            emergency_contact += f" - {teacher.emergency_phone}"
        if teacher.emergency_email:
            emergency_contact += f" - {teacher.emergency_email}"
    
    # Format address information
    address = "Not available"
    if teacher.street:
        address_parts = [teacher.street]
        if teacher.apt_unit:
            address_parts.append(teacher.apt_unit)
        if teacher.city and teacher.state:
            address_parts.append(f"{teacher.city}, {teacher.state}")
        elif teacher.city:
            address_parts.append(teacher.city)
        elif teacher.state:
            address_parts.append(teacher.state)
        if teacher.zip_code:
            address_parts.append(teacher.zip_code)
        address = ", ".join(address_parts)
    
    return jsonify({
        'id': teacher.id,
        'first_name': teacher.first_name,
        'last_name': teacher.last_name,
        'staff_id': teacher.staff_id,
        'age': None,  # Not available for teachers
        'dob': None,  # Not available for teachers
        'role': role,
        'email': teacher.email,
        'username': teacher.user.username if teacher.user else None,
        'department': teacher.department,
        'position': teacher.position,
        'hire_date': teacher.hire_date,
        'phone': teacher.phone,
        'address': address,
        'emergency_contact': emergency_contact,
        'assigned_classes': [{'id': c.id, 'name': c.name, 'subject': c.subject} for c in assigned_classes],
        'total_students': total_students
    })

@management_blueprint.route('/edit-teacher/<int:teacher_id>', methods=['POST'])
@login_required
@management_required
def edit_teacher(teacher_id):
    """Edit teacher/staff information via AJAX modal"""
    teacher = TeacherStaff.query.get_or_404(teacher_id)
    try:
        # Basic information
        teacher.first_name = request.form.get('first_name', teacher.first_name)
        teacher.middle_initial = request.form.get('middle_initial', teacher.middle_initial)
        teacher.last_name = request.form.get('last_name', teacher.last_name)
        teacher.email = request.form.get('email', teacher.email)
        teacher.dob = request.form.get('dob', teacher.dob)
        teacher.staff_ssn = request.form.get('staff_ssn', teacher.staff_ssn)
        teacher.phone = request.form.get('phone', teacher.phone)
        
        # Professional information
        teacher.assigned_role = request.form.get('assigned_role', teacher.assigned_role)
        teacher.hire_date = request.form.get('hire_date', teacher.hire_date)
        teacher.position = request.form.get('position', teacher.position)
        teacher.subject = request.form.get('subject', teacher.subject)
        teacher.employment_type = request.form.get('employment_type', teacher.employment_type)
        
        # Handle multiple department selections
        departments = request.form.getlist('department')
        teacher.department = ', '.join(departments) if departments else teacher.department
        
        # Handle multiple grades taught selections
        grades_taught = request.form.getlist('grades_taught')
        teacher.grades_taught = json.dumps(grades_taught) if grades_taught else teacher.grades_taught
        
        # Auto-assign role and department for Tech users
        if current_user.role in ['Tech', 'IT Support']:
            teacher.department = 'Administration'
            teacher.assigned_role = 'IT Support'
        
        # Address information
        teacher.street = request.form.get('street_address', teacher.street)
        teacher.apt_unit = request.form.get('apt_unit_suite', teacher.apt_unit)
        teacher.city = request.form.get('city', teacher.city)
        teacher.state = request.form.get('state', teacher.state)
        teacher.zip_code = request.form.get('zip_code', teacher.zip_code)
        
        # Emergency contact information
        teacher.emergency_first_name = request.form.get('emergency_contact_name', teacher.emergency_first_name)
        teacher.emergency_last_name = request.form.get('emergency_contact_last_name', teacher.emergency_last_name)
        teacher.emergency_email = request.form.get('emergency_contact_email', teacher.emergency_email)
        teacher.emergency_phone = request.form.get('emergency_contact_phone', teacher.emergency_phone)
        teacher.emergency_relationship = request.form.get('emergency_contact_relationship', teacher.emergency_relationship)
        
        # Update user role if user account exists
        if teacher.user:
            # Auto-assign role for Tech users
            if current_user.role in ['Tech', 'IT Support']:
                teacher.user.role = 'IT Support'
            else:
                teacher.user.role = request.form.get('assigned_role', teacher.user.role)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Teacher/Staff updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@management_blueprint.route('/school-years', methods=['GET', 'POST'])
@login_required
@management_required
def school_years():
    """Manage school years."""
    if request.method == 'POST':
        name = request.form.get('name')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        is_active = request.form.get('is_active') == 'true'
        auto_generate_quarters = request.form.get('auto_generate_quarters') == 'true'

        if not all([name, start_date_str, end_date_str]):
            flash('All fields are required to create a school year.', 'danger')
            return redirect(url_for('management.school_years'))

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('management.school_years'))

        # If this new year is set to active, deactivate all others
        if is_active:
            SchoolYear.query.update({SchoolYear.is_active: False})
        
        new_year = SchoolYear(name=name, start_date=start_date, end_date=end_date, is_active=is_active)
        db.session.add(new_year)
        db.session.flush()  # Get the ID without committing
        
        # Auto-generate academic periods if requested
        if auto_generate_quarters:
            try:
                add_academic_periods_for_year(new_year.id)
                flash(f'School year "{name}" created successfully with academic periods!', 'success')
            except Exception as e:
                flash(f'School year "{name}" created but there was an error generating academic periods: {str(e)}', 'warning')
        else:
            flash(f'School year "{name}" created successfully!', 'success')
        
        db.session.commit()
        return redirect(url_for('management.school_years'))

    school_years = SchoolYear.query.order_by(SchoolYear.start_date.desc()).all()
    active_school_year = SchoolYear.query.filter_by(is_active=True).first()
    
    # Add academic periods to each school year
    for year in school_years:
        year.academic_periods = AcademicPeriod.query.filter_by(school_year_id=year.id, is_active=True).all()
        year.calendar_events = CalendarEvent.query.filter_by(school_year_id=year.id).all()
        if year.start_date and year.end_date:
            year.total_days = (year.end_date - year.start_date).days
    
    return render_template('management/management_school_years.html', 
                         school_years=school_years,
                         active_school_year=active_school_year)


@management_blueprint.route('/school-year/set-active/<int:year_id>', methods=['POST'])
@login_required
@management_required
def set_active_school_year(year_id):
    """Sets a specific school year as active and deactivates all others."""
    year_to_activate = SchoolYear.query.get_or_404(year_id)
    
    # Deactivate all other years
    SchoolYear.query.filter(SchoolYear.id != year_id).update({SchoolYear.is_active: False})
    
    # Activate the selected year
    year_to_activate.is_active = True
    
    db.session.commit()
    flash(f'School year "{year_to_activate.name}" is now the active year.', 'success')
    return redirect(url_for('management.school_years'))


@management_blueprint.route('/school-year/edit-active', methods=['POST'])
@login_required
@management_required
def edit_active_school_year():
    """Edit the active school year's dates with automatic academic period synchronization."""
    active_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_school_year:
        flash('No active school year found.', 'danger')
        return redirect(url_for('management.calendar'))
    
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    if not all([start_date_str, end_date_str]):
        flash('Both start and end dates are required.', 'danger')
        return redirect(url_for('management.calendar'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_date >= end_date:
            flash('End date must be after start date.', 'danger')
            return redirect(url_for('management.calendar'))
        
        # Update school year dates
        active_school_year.start_date = start_date
        active_school_year.end_date = end_date
        
        # Get academic periods for this school year
        from models import AcademicPeriod
        academic_periods = AcademicPeriod.query.filter_by(school_year_id=active_school_year.id).all()
        
        # Create a mapping of period names to period objects
        period_map = {period.name: period for period in academic_periods}
        
        # Calculate new quarter dates based on school year duration
        year_duration = (end_date - start_date).days
        quarter_duration = year_duration // 4
        
        # Update Q1 and S1 start dates (linked to school year start)
        if 'Quarter 1' in period_map:
            period_map['Quarter 1'].start_date = start_date
            period_map['Quarter 1'].end_date = start_date + timedelta(days=quarter_duration - 1)
        
        if 'Semester 1' in period_map:
            period_map['Semester 1'].start_date = start_date
        
        # Update Q2 end date and S1 end date (linked together)
        if 'Quarter 2' in period_map:
            q2_start = start_date + timedelta(days=quarter_duration)
            q2_end = q2_start + timedelta(days=quarter_duration - 1)
            period_map['Quarter 2'].start_date = q2_start
            period_map['Quarter 2'].end_date = q2_end
            
            if 'Semester 1' in period_map:
                period_map['Semester 1'].end_date = q2_end
        
        # Update Q3 start date and S2 start date (linked together)
        if 'Quarter 3' in period_map:
            q3_start = start_date + timedelta(days=quarter_duration * 2)
            q3_end = q3_start + timedelta(days=quarter_duration - 1)
            period_map['Quarter 3'].start_date = q3_start
            period_map['Quarter 3'].end_date = q3_end
            
            if 'Semester 2' in period_map:
                period_map['Semester 2'].start_date = q3_start
        
        # Update Q4 end date and S2 end date (linked to school year end)
        if 'Quarter 4' in period_map:
            q4_start = start_date + timedelta(days=quarter_duration * 3)
            period_map['Quarter 4'].start_date = q4_start
            period_map['Quarter 4'].end_date = end_date
        
        if 'Semester 2' in period_map:
            period_map['Semester 2'].end_date = end_date
        
        # Commit all changes
        db.session.commit()
        
        flash(f'Active school year "{active_school_year.name}" dates updated successfully with automatic academic period synchronization!', 'success')
        
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating active school year: {str(e)}', 'danger')
    
    return redirect(url_for('management.calendar'))


@management_blueprint.route('/school-year/edit/<int:year_id>', methods=['POST'])
@login_required
@management_required
def edit_school_year(year_id):
    """Edit a school year's start and end dates with automatic academic period synchronization."""
    school_year = SchoolYear.query.get_or_404(year_id)
    
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    if not all([start_date_str, end_date_str]):
        flash('Both start and end dates are required.', 'danger')
        return redirect(url_for('management.school_years'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_date >= end_date:
            flash('End date must be after start date.', 'danger')
            return redirect(url_for('management.school_years'))
        
        # Store old dates for comparison
        old_start_date = school_year.start_date
        old_end_date = school_year.end_date
        
        # Update school year dates
        school_year.start_date = start_date
        school_year.end_date = end_date
        
        # Get academic periods for this school year
        from models import AcademicPeriod
        academic_periods = AcademicPeriod.query.filter_by(school_year_id=school_year.id).all()
        
        # Create a mapping of period names to period objects
        period_map = {period.name: period for period in academic_periods}
        
        # Calculate new quarter dates based on school year duration
        year_duration = (end_date - start_date).days
        quarter_duration = year_duration // 4
        
        # Update Q1 and S1 start dates (linked to school year start)
        if 'Quarter 1' in period_map:
            period_map['Quarter 1'].start_date = start_date
            period_map['Quarter 1'].end_date = start_date + timedelta(days=quarter_duration - 1)
        
        if 'Semester 1' in period_map:
            period_map['Semester 1'].start_date = start_date
        
        # Update Q2 end date and S1 end date (linked together)
        if 'Quarter 2' in period_map:
            q2_start = start_date + timedelta(days=quarter_duration)
            q2_end = q2_start + timedelta(days=quarter_duration - 1)
            period_map['Quarter 2'].start_date = q2_start
            period_map['Quarter 2'].end_date = q2_end
            
            if 'Semester 1' in period_map:
                period_map['Semester 1'].end_date = q2_end
        
        # Update Q3 start date and S2 start date (linked together)
        if 'Quarter 3' in period_map:
            q3_start = start_date + timedelta(days=quarter_duration * 2)
            q3_end = q3_start + timedelta(days=quarter_duration - 1)
            period_map['Quarter 3'].start_date = q3_start
            period_map['Quarter 3'].end_date = q3_end
            
            if 'Semester 2' in period_map:
                period_map['Semester 2'].start_date = q3_start
        
        # Update Q4 end date and S2 end date (linked to school year end)
        if 'Quarter 4' in period_map:
            q4_start = start_date + timedelta(days=quarter_duration * 3)
            period_map['Quarter 4'].start_date = q4_start
            period_map['Quarter 4'].end_date = end_date
        
        if 'Semester 2' in period_map:
            period_map['Semester 2'].end_date = end_date
        
        # Commit all changes
        db.session.commit()
        
        flash(f'School year "{school_year.name}" dates updated successfully with automatic academic period synchronization!', 'success')
        
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating school year: {str(e)}', 'danger')
    
    return redirect(url_for('management.school_years'))


@management_blueprint.route('/academic-period/edit/<int:period_id>', methods=['POST'])
@login_required
@management_required
def edit_academic_period(period_id):
    """Edit an academic period's dates with automatic synchronization of linked periods."""
    period = AcademicPeriod.query.get_or_404(period_id)
    
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    if not all([start_date_str, end_date_str]):
        flash('Both start and end dates are required.', 'danger')
        return redirect(url_for('management.school_years'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if start_date >= end_date:
            flash('End date must be after start date.', 'danger')
            return redirect(url_for('management.school_years'))
        
        # Store old dates for comparison
        old_start_date = period.start_date
        old_end_date = period.end_date
        
        # Update the current period
        period.start_date = start_date
        period.end_date = end_date
        
        # Get all academic periods for this school year
        academic_periods = AcademicPeriod.query.filter_by(school_year_id=period.school_year_id).all()
        period_map = {p.name: p for p in academic_periods}
        
        # Handle synchronization based on period type
        if period.name == 'Quarter 1':
            # Q1 start date changes → update S1 start date and school year start date
            if 'Semester 1' in period_map:
                period_map['Semester 1'].start_date = start_date
            
            # Update school year start date if it's different
            school_year = SchoolYear.query.get(period.school_year_id)
            if school_year and school_year.start_date != start_date:
                school_year.start_date = start_date
        
        elif period.name == 'Quarter 2':
            # Q2 end date changes → update S1 end date
            if 'Semester 1' in period_map:
                period_map['Semester 1'].end_date = end_date
        
        elif period.name == 'Quarter 3':
            # Q3 start date changes → update S2 start date
            if 'Semester 2' in period_map:
                period_map['Semester 2'].start_date = start_date
        
        elif period.name == 'Quarter 4':
            # Q4 end date changes → update S2 end date and school year end date
            if 'Semester 2' in period_map:
                period_map['Semester 2'].end_date = end_date
            
            # Update school year end date if it's different
            school_year = SchoolYear.query.get(period.school_year_id)
            if school_year and school_year.end_date != end_date:
                school_year.end_date = end_date
        
        elif period.name == 'Semester 1':
            # S1 start date changes → update Q1 start date and school year start date
            if 'Quarter 1' in period_map:
                period_map['Quarter 1'].start_date = start_date
            
            # Update school year start date if it's different
            school_year = SchoolYear.query.get(period.school_year_id)
            if school_year and school_year.start_date != start_date:
                school_year.start_date = start_date
            
            # S1 end date changes → update Q2 end date
            if 'Quarter 2' in period_map:
                period_map['Quarter 2'].end_date = end_date
        
        elif period.name == 'Semester 2':
            # S2 start date changes → update Q3 start date
            if 'Quarter 3' in period_map:
                period_map['Quarter 3'].start_date = start_date
            
            # S2 end date changes → update Q4 end date and school year end date
            if 'Quarter 4' in period_map:
                period_map['Quarter 4'].end_date = end_date
            
            # Update school year end date if it's different
            school_year = SchoolYear.query.get(period.school_year_id)
            if school_year and school_year.end_date != end_date:
                school_year.end_date = end_date
        
        # Commit all changes
        db.session.commit()
        
        flash(f'{period.name} dates updated successfully with automatic synchronization!', 'success')
        
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating academic period: {str(e)}', 'danger')
    
    return redirect(url_for('management.school_years'))


@management_blueprint.route('/academic-periods/generate/<int:year_id>', methods=['POST'])
@login_required
@management_required
def generate_academic_periods(year_id):
    """Generate or regenerate academic periods for a school year with proper linking."""
    school_year = SchoolYear.query.get_or_404(year_id)
    
    try:
        # Remove existing academic periods for this year
        AcademicPeriod.query.filter_by(school_year_id=year_id).delete()
        
        # Generate new academic periods with proper linking
        add_academic_periods_for_year(year_id)
        
        flash(f'Academic periods for {school_year.name} have been regenerated successfully with proper linking!', 'success')
        
    except Exception as e:
        flash(f'Error generating academic periods: {str(e)}', 'danger')
    
    return redirect(url_for('management.school_years'))


@management_blueprint.route('/academic-period/add/<int:year_id>', methods=['POST'])
@login_required
@management_required
def add_academic_period(year_id):
    """Add a new academic period to a school year."""
    school_year = SchoolYear.query.get_or_404(year_id)
    
    # Get form data
    name = request.form.get('name')
    period_type = request.form.get('period_type')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    # Validate required fields
    if not all([name, period_type, start_date_str, end_date_str]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('management.calendar'))
    
    # Validate period type
    if period_type not in ['quarter', 'semester']:
        flash('Invalid period type. Must be quarter or semester.', 'danger')
        return redirect(url_for('management.calendar'))
    
    try:
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Validate date logic
        if start_date >= end_date:
            flash('End date must be after start date.', 'danger')
            return redirect(url_for('management.calendar'))
        
        # Check if dates fall within school year
        if start_date < school_year.start_date or end_date > school_year.end_date:
            flash('Academic period dates must fall within the school year.', 'danger')
            return redirect(url_for('management.calendar'))
        
        # Check for overlapping periods of the same type
        overlapping_periods = AcademicPeriod.query.filter(
            AcademicPeriod.school_year_id == year_id,
            AcademicPeriod.period_type == period_type,
            AcademicPeriod.start_date <= end_date,
            AcademicPeriod.end_date >= start_date
        ).all()
        
        if overlapping_periods:
            flash(f'A {period_type} already exists for the selected date range.', 'danger')
            return redirect(url_for('management.calendar'))
        
        # Create new academic period
        new_period = AcademicPeriod(
            name=name,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            school_year_id=year_id
        )
        
        db.session.add(new_period)
        db.session.commit()
        
        flash(f'Academic period "{name}" added successfully!', 'success')
        
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding academic period: {str(e)}', 'danger')
    
    return redirect(url_for('management.calendar'))


def get_academic_dates_for_calendar(year, month):
    """Get academic dates (quarters, semesters, holidays) for a specific month/year."""
    from datetime import date
    
    academic_dates = []
    
    # Get the active school year
    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        return academic_dates
    
    # Get academic periods for this month
    start_of_month = date(year, month, 1)
    if month == 12:
        end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get academic periods that overlap with this month
    academic_periods = AcademicPeriod.query.filter(
        AcademicPeriod.school_year_id == active_year.id,
        AcademicPeriod.start_date <= end_of_month,
        AcademicPeriod.end_date >= start_of_month
    ).all()
    
    for period in academic_periods:
        # Add start date event
        if period.start_date.month == month:
            academic_dates.append({
                'day': period.start_date.day,
                'title': f"{period.name} Start",
                'category': f"{period.period_type.title()}",
                'type': 'academic_period_start'
            })
        
        # Add end date event
        if period.end_date.month == month:
            academic_dates.append({
                'day': period.end_date.day,
                'title': f"{period.name} End",
                'category': f"{period.period_type.title()}",
                'type': 'academic_period_end'
            })
    
    # Get calendar events for this month
    calendar_events = CalendarEvent.query.filter(
        CalendarEvent.school_year_id == active_year.id,
        CalendarEvent.start_date <= end_of_month,
        CalendarEvent.end_date >= start_of_month
    ).all()
    
    for event in calendar_events:
        if event.start_date.month == month:
            academic_dates.append({
                'day': event.start_date.day,
                'title': event.name,
                'category': event.event_type.replace('_', ' ').title(),
                'type': 'calendar_event'
            })
    
    # Get teacher work days for this month
    teacher_work_days = TeacherWorkDay.query.filter(
        TeacherWorkDay.school_year_id == active_year.id,
        TeacherWorkDay.date >= start_of_month,
        TeacherWorkDay.date <= end_of_month
    ).all()
    
    for work_day in teacher_work_days:
        if work_day.date.month == month:
            # Shorten the title for better display
            short_title = work_day.title
            if "Professional Development" in short_title:
                short_title = "PD Day"
            elif "First Day" in short_title:
                short_title = "First Day"
            
            academic_dates.append({
                'day': work_day.date.day,
                'title': short_title,
                'category': 'Teacher Work Day',
                'type': 'teacher_work_day'
            })
    
    # Get school breaks for this month
    school_breaks = SchoolBreak.query.filter(
        SchoolBreak.school_year_id == active_year.id,
        SchoolBreak.start_date <= end_of_month,
        SchoolBreak.end_date >= start_of_month
    ).all()
    
    for school_break in school_breaks:
        # Check if any part of the break falls in this month
        if (school_break.start_date.month == month or 
            school_break.end_date.month == month or
            (school_break.start_date.month < month and school_break.end_date.month > month)):
            
            # For multi-day breaks, show start and end dates
            if school_break.start_date.month == month:
                # Shorten break names for better display
                short_name = school_break.name
                if "Thanksgiving" in short_name:
                    short_name = "Thanksgiving"
                elif "Winter" in short_name:
                    short_name = "Winter"
                elif "Spring" in short_name:
                    short_name = "Spring"
                
                academic_dates.append({
                    'day': school_break.start_date.day,
                    'title': f"{short_name} Start",
                    'category': school_break.break_type,
                    'type': 'school_break_start'
                })
            
            if school_break.end_date.month == month:
                # Shorten break names for better display
                short_name = school_break.name
                if "Thanksgiving" in short_name:
                    short_name = "Thanksgiving"
                elif "Winter" in short_name:
                    short_name = "Winter"
                elif "Spring" in short_name:
                    short_name = "Spring"
                
                academic_dates.append({
                    'day': school_break.end_date.day,
                    'title': f"{short_name} End",
                    'category': school_break.break_type,
                    'type': 'school_break_end'
                })
    
    return academic_dates


@management_blueprint.route('/upload-calendar-pdf', methods=['POST'])
@login_required
@management_required
def upload_calendar_pdf():
    """Upload and process a school calendar PDF."""
    # PDF processing temporarily disabled due to import issues
    flash('PDF processing is temporarily unavailable. Please check back later.', 'warning')
    return redirect(url_for('management.calendar'))


# def process_calendar_pdf(filepath):
#     """Process a PDF calendar to extract important dates."""
#     # PDF processing temporarily disabled due to import issues
#     return {}

# def extract_school_year_dates(text_content, text_lower):
#     """Extract school year start and end dates."""
#     # PDF processing temporarily disabled due to import issues
#     return {'school_year_start': None, 'school_year_end': None}

# def extract_academic_periods(text_content, text_lower):
#     """Extract quarter and semester dates."""
#     # PDF processing temporarily disabled due to import issues
#     return {'quarters': [], 'semesters': []}

# def extract_holidays_and_events(text_content, text_lower):
#     """Extract holidays and special event dates."""
#     # PDF processing temporarily disabled due to import issues
#     return {'holidays': [], 'parent_teacher_conferences': [], 'early_dismissal': [], 'no_school': []}

def extract_breaks_and_vacations(text_content, text_lower):
    """Extract vacation and break dates."""
    breaks = {
        'breaks': []
    }
    
    # Break patterns
    break_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*winter\s+break',
        r'winter\s+break[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*spring\s+break',
        r'spring\s+break[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*summer\s+break',
        r'summer\s+break[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*fall\s+break',
        r'fall\s+break[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in break_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                start_date = parse_date_string(match.group(1))
                end_date = parse_date_string(match.group(2))
                
                if start_date and end_date:
                    # Determine break type from the pattern
                    if 'winter' in pattern:
                        break_name = 'Winter Break'
                    elif 'spring' in pattern:
                        break_name = 'Spring Break'
                    elif 'summer' in pattern:
                        break_name = 'Summer Break'
                    elif 'fall' in pattern:
                        break_name = 'Fall Break'
                    else:
                        break_name = 'School Break'
                    
                    breaks['breaks'].append({
                        'name': break_name,
                        'start_date': start_date,
                        'end_date': end_date
                    })
            except:
                continue
    
    return breaks

def extract_professional_dates(text_content, text_lower):
    """Extract professional development and staff dates."""
    prof_dates = {
        'professional_development': []
    }
    
    # Professional development patterns
    pd_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*professional\s+development',
        r'professional\s+development[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*pd\s+day',
        r'pd\s+day[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*staff\s+development',
        r'staff\s+development[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*teacher\s+workday',
        r'teacher\s+workday[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in pd_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    prof_dates['professional_development'].append({
                        'name': 'Professional Development',
                        'date': parsed_date
                    })
            except:
                continue
    
    return prof_dates

def parse_date_string(date_str):
    """Parse various date string formats into a date object."""
    if not date_str:
        return None
    
    # Remove extra whitespace and common punctuation
    date_str = re.sub(r'[,\s]+', ' ', date_str.strip())
    
    # Common date formats
    date_formats = [
        '%B %d %Y',      # January 15 2024
        '%b %d %Y',      # Jan 15 2024
        '%B %d, %Y',     # January 15, 2024
        '%b %d, %Y',     # Jan 15, 2024
        '%m/%d/%Y',      # 01/15/2024
        '%m-%d-%Y',      # 01-15-2024
        '%Y-%m-%d',      # 2024-01-15
        '%B %d',         # January 15 (assume current year)
        '%b %d',         # Jan 15 (assume current year)
        '%m/%d',         # 01/15 (assume current year)
        '%m-%d'          # 01-15 (assume current year)
    ]
    
    current_year = datetime.now().year
    
    for fmt in date_formats:
        try:
            if fmt in ['%B %d', '%b %d', '%m/%d', '%m-%d']:
                # For formats without year, assume current year
                parsed_date = datetime.strptime(date_str, fmt)
                return date(current_year, parsed_date.month, parsed_date.day)
            else:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.date()
        except ValueError:
            continue
    
    return None

@management_blueprint.route('/view-class/<int:class_id>')
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
    
    # Get assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).all()
    
    # Get current date for assignment status comparison
    today = datetime.now().date()
    
    return render_template('management/view_class.html', 
                         class_info=class_info,
                         teacher=teacher,
                         enrolled_students=enrolled_students,
                         assignments=assignments,
                         today=today,
                         role_prefix=None)




@management_blueprint.route('/manage-class-roster/<int:class_id>', methods=['GET', 'POST'])
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
    teachers = TeacherStaff.query.all()
    available_teachers = []
    for t in teachers:
        user = User.query.filter_by(teacher_staff_id=t.id).first()
        username = user.username if user else ''
        name = f"{t.first_name} {t.last_name}"
        available_teachers.append({'id': t.id, 'name': name, 'username': username})
    
    return render_template('management/manage_class_roster.html', 
                         class_info=class_info,
                         all_students=all_students,
                         enrolled_students=enrolled_students,
                         available_teachers=available_teachers,
                         today=datetime.now().date())

@management_blueprint.route('/remove-student/<int:student_id>', methods=['POST'])
@login_required
@management_required
def remove_student(student_id):
    """Remove a student"""
    student = Student.query.get_or_404(student_id)
    
    # Delete associated user account if it exists
    if student.user:
        db.session.delete(student.user)
    
    # Delete the student
    db.session.delete(student)
    db.session.commit()
    
    flash('Student removed successfully.', 'success')
    return redirect(url_for('management.students'))

@management_blueprint.route('/resources')
@login_required
@management_required
def resources():
    """Display the resources page with MinuteMath files."""
    try:
        # Get list of PDF files in MinuteMath directory
        import os
        minute_math_dir = os.path.join(os.getcwd(), 'MinuteMath')
        study_guides_dir = os.path.join(minute_math_dir, 'StudyGuides')
        
        # Original PDF files
        pdf_files = []
        if os.path.exists(minute_math_dir):
            for filename in os.listdir(minute_math_dir):
                if filename.endswith('.pdf'):
                    pdf_files.append({
                        'name': filename,
                        'display_name': filename.replace('.pdf', ''),
                        'grade': filename.split()[0] if filename.split()[0].replace('th', '').replace('rd', '').replace('st', '').replace('nd', '').isdigit() else 'Unknown',
                        'type': 'Original',
                        'path': os.path.join('MinuteMath', filename)
                    })
        
        # Study guide files
        study_guide_files = []
        if os.path.exists(study_guides_dir):
            for filename in os.listdir(study_guides_dir):
                if filename.endswith('.txt'):
                    study_guide_files.append({
                        'name': filename,
                        'display_name': filename.replace(' - Study Guide.txt', ''),
                        'grade': filename.split()[0] if filename.split()[0].replace('th', '').replace('rd', '').replace('st', '').replace('nd', '').isdigit() else 'Unknown',
                        'type': 'Study Guide',
                        'path': os.path.join('MinuteMath', 'StudyGuides', filename)
                    })
        
        # Combine and sort by grade
        all_files = pdf_files + study_guide_files
        all_files.sort(key=lambda x: int(x['grade'].replace('th', '').replace('rd', '').replace('st', '').replace('nd', '')) if x['grade'].replace('th', '').replace('rd', '').replace('st', '').replace('nd', '').isdigit() else 999)
        
        return render_template('management/resources.html', 
                             files=all_files,
                             pdf_files=pdf_files,
                             study_guide_files=study_guide_files)
    
    except Exception as e:
        print(f"Error loading resources: {e}")
        flash('Error loading resources. Please try again.', 'error')
        return redirect(url_for('management.management_dashboard'))

@management_blueprint.route('/resources/download/<path:filename>')
@login_required
@management_required
def download_resource(filename):
    """Download a resource file."""
    try:
        import os
        from flask import send_from_directory
        
        # Security check - ensure filename is safe
        if '..' in filename or filename.startswith('/'):
            flash('Invalid file path.', 'error')
            return redirect(url_for('management.resources'))
        
        # Check if file exists
        file_path = os.path.join(os.getcwd(), filename)
        if not os.path.exists(file_path):
            flash('File not found.', 'error')
            return redirect(url_for('management.resources'))
        
        # Send file for download
        directory = os.path.dirname(file_path)
        filename_only = os.path.basename(file_path)
        
        return send_from_directory(directory, filename_only, as_attachment=True)
    
    except Exception as e:
        print(f"Error downloading file {filename}: {e}")
        flash('Error downloading file. Please try again.', 'error')
        return redirect(url_for('management.resources'))

# def store_calendar_data(calendar_data, school_year_id, pdf_filename):
#     """Store extracted calendar data in the database."""
#     # PDF processing temporarily disabled due to import issues
#     pass
