from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from models import db, Student, TeacherStaff, Class, SchoolYear, User, ReportCard, Assignment, Announcement, Message, MessageGroup, ScheduledAnnouncement, Notification, MessageGroupMember, Grade, Enrollment, Attendance, AcademicPeriod, CalendarEvent, TeacherWorkDay, SchoolBreak, Submission
from decorators import management_required
from app import calculate_and_get_grade_for_student, get_grade_for_student, create_notification
import os
import json
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, date
import time # Added for time.time()
import re
# import PyPDF2
# import pdfplumber
from sqlalchemy import text
from werkzeug.security import generate_password_hash
from add_academic_periods import add_academic_periods_for_year

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    stats = {
        'students': Student.query.count(),
        'teachers': TeacherStaff.query.count(),
        'classes': Class.query.count(),
        'assignments': Assignment.query.count()
    }
    return render_template('role_dashboard.html', 
                         stats=stats,
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
            
            db.session.add(user)
            db.session.commit()
            
            # Show success message with credentials
            flash(f'Student added successfully! Username: {username}, Password: {password}', 'success')
            return redirect(url_for('management.students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('add_student.html')

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
            
            db.session.add(user)
            db.session.commit()
            
            # Show success message with credentials
            flash(f'{assigned_role} added successfully! Username: {username}, Password: {password}, Staff ID: {teacher_staff.staff_id}', 'success')
            return redirect(url_for('management.teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding {assigned_role.lower()}: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('add_teacher_staff.html')

@management_blueprint.route('/edit-teacher-staff/<int:staff_id>')
@login_required
@management_required
def edit_teacher_staff(staff_id):
    """Edit a teacher or staff member"""
    teacher_staff = TeacherStaff.query.get_or_404(staff_id)
    return render_template('edit_teacher_staff.html', teacher_staff=teacher_staff)

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

    return render_template('report_card_generate_form.html', students=students, school_years=school_years)

@management_blueprint.route('/report/card/view/<int:report_card_id>')
@login_required
@management_required
def view_report_card(report_card_id):
    report_card = ReportCard.query.get_or_404(report_card_id)
    grades = json.loads(report_card.grades_details) if report_card.grades_details else {}
    # attendance = json.loads(report_card.attendance_details) if report_card.attendance_details else {}
    
    # Dummy attendance data for now
    attendance = {"Present": 45, "Absent": 2, "Tardy": 1}

    return render_template('report_card_detail.html', report_card=report_card, grades=grades, attendance=attendance)

@management_blueprint.route('/report/card/pdf/<int:report_card_id>')
@login_required
@management_required
def generate_report_card_pdf(report_card_id):
    if pdfkit is None:
        flash('PDF generation is not available. Please install pdfkit.', 'danger')
        return redirect(url_for('management.view_report_card', report_card_id=report_card_id))
        
    report_card = ReportCard.query.get_or_404(report_card_id)
    student = report_card.student
    grades = json.loads(report_card.grades_details) if report_card.grades_details else {}
    
    # Dummy attendance data
    attendance = {"Present": 45, "Absent": 2, "Tardy": 1}

    # Choose template based on grade level
    grade_level = student.grade_level
    if grade_level in [1, 2]:
        template_name = 'official_report_card_pdf_template_1_2.html'
    elif grade_level == 3:
        template_name = 'official_report_card_pdf_template_3.html'
    elif grade_level in [4, 5, 6, 7, 8]:
        template_name = 'official_report_card_pdf_template_4_8.html'
    else:
        flash(f"No report card template for grade level {grade_level}.", "danger")
        return redirect(url_for('management.view_report_card', report_card_id=report_card_id))
        
    rendered_template = render_template(
        template_name, 
        report_card=report_card, 
        student=student, 
        grades=grades, 
        attendance=attendance
    )
    
    # Get path to CSS file
    css_path = os.path.join(current_app.root_path, 'static', 'report_card_styles.css')
    
    options = {
        'page-size': 'Letter',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None
    }

    try:
        # Generate PDF from rendered HTML
        pdf = pdfkit.from_string(rendered_template, False, options=options, css=css_path)
        
        # Create a response to send the PDF to the browser
        response = Response(pdf, mimetype='application/pdf')
        response.headers['Content-Disposition'] = f'inline; filename=ReportCard_{student.last_name}_{report_card.id}.pdf'
        
        return response
    except Exception as e:
        current_app.logger.error(f"PDF generation failed for report card {report_card_id}: {e}")
        flash(f'Could not generate PDF. Please ensure wkhtmltopdf is installed and configured correctly. Error: {e}', 'danger')
        return redirect(url_for('management.view_report_card', report_card_id=report_card_id))

@management_blueprint.route('/students')
@login_required
@management_required
def students():
    search_query = request.args.get('search', '').strip()
    
    # Build the query
    query = Student.query
    
    # Apply search filter if query exists
    if search_query:
        search_filter = db.or_(
            Student.first_name.ilike(f'%{search_query}%'),
            Student.last_name.ilike(f'%{search_query}%'),
            Student.email.ilike(f'%{search_query}%'),
            Student.student_id.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)
    
    # Order by last name, then first name
    students = query.order_by(Student.last_name, Student.first_name).all()
    
    return render_template('role_dashboard.html', 
                         students=students,
                         search_query=search_query,
                         section='students',
                         active_tab='students')

@management_blueprint.route('/teachers')
@login_required
@management_required
def teachers():
    search_query = request.args.get('search', '').strip()
    
    # Build the query
    query = TeacherStaff.query
    
    # Apply search filter if query exists
    if search_query:
        search_filter = db.or_(
            TeacherStaff.first_name.ilike(f'%{search_query}%'),
            TeacherStaff.last_name.ilike(f'%{search_query}%'),
            TeacherStaff.email.ilike(f'%{search_query}%'),
            TeacherStaff.assigned_role.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)
    
    # Order by last name, then first name
    teachers = query.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()
    
    return render_template('role_dashboard.html', 
                         teachers=teachers,
                         search_query=search_query,
                         section='teachers',
                         active_tab='teachers')

@management_blueprint.route('/classes')
@login_required
@management_required
def classes():
    classes = Class.query.all()
    return render_template('role_dashboard.html', 
                         classes=classes,
                         section='classes',
                         active_tab='classes')

@management_blueprint.route('/assignments')
@login_required
@management_required
def assignments():
    assignments = Assignment.query.all()
    classes = Class.query.all()  # For the filter dropdown
    from datetime import datetime
    
    # Get current date for filtering
    today = datetime.now().date()
    
    # Add status to each assignment based on due date
    for assignment in assignments:
        if assignment.due_date:
            due_date = assignment.due_date.date()
            if due_date < today:
                assignment.status = 'overdue'
            elif due_date == today:
                assignment.status = 'due_today'
            else:
                assignment.status = 'active'
        else:
            assignment.status = 'no_due_date'
    
    return render_template('role_dashboard.html',
                         assignments=assignments,
                         classes=classes,
                         today=today,
                         selected_class_id=request.args.get('class_id', type=int),
                         selected_status=request.args.get('status', ''),
                         selected_due_date=request.args.get('due_date', ''),
                         total_pages=1,
                         page=1,
                         section='assignments',
                         active_tab='assignments')

@management_blueprint.route('/attendance')
@login_required
@management_required
def attendance():
    # Get all classes with student counts
    classes = Class.query.all()
    
    # For each class, get the enrolled student count
    for class_obj in classes:
        # Count active enrollments for this class
        student_count = db.session.query(Enrollment).filter_by(
            class_id=class_obj.id, 
            is_active=True
        ).count()
        class_obj.enrolled_student_count = student_count
    
    return render_template('role_dashboard.html',
                         classes=classes,
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

    return render_template('attendance_report_view.html',
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
    
    return render_template('role_dashboard.html', 
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
    return render_template('role_dashboard.html',
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
    
    return render_template('role_calendar.html', 
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
    
    return render_template('management_teacher_work_days.html',
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
    
    return render_template('management_school_breaks.html',
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
    return render_template('under_development.html',
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
    
    return render_template('management_messages.html',
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
    
    return render_template('management_send_message.html',
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
    
    return render_template('management_view_message.html',
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
    
    return render_template('management_groups.html',
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
    
    return render_template('management_create_group.html',
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
    
    return render_template('management_view_group.html',
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
    
    return render_template('management_create_announcement.html',
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
    
    return render_template('management_schedule_announcement.html',
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
    
    return render_template('role_dashboard.html',
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
    return render_template('role_dashboard.html',
                         section='settings',
                         active_tab='settings')


@management_blueprint.route('/add-class', methods=['GET', 'POST'])
@login_required
@management_required
def add_class():
    """Add a new class"""
    # Query all teachers (role='Teacher')
    teachers = TeacherStaff.query.all()
    available_teachers = []
    for t in teachers:
        user = User.query.filter_by(teacher_staff_id=t.id).first()
        username = user.username if user else ''
        name = f"{t.first_name} {t.last_name}"
        available_teachers.append({'id': t.id, 'name': name, 'username': username})

    if request.method == 'POST':
        class_name = request.form.get('class_name', '').strip()
        subject = request.form.get('subject', '').strip()
        teacher_id = request.form.get('teacher_id', type=int)

        # Validate required fields
        if not all([class_name, subject, teacher_id]):
            flash('Class name, subject, and teacher are required.', 'danger')
            return render_template('add_class.html', available_teachers=available_teachers)

        # Fetch the currently active school year
        current_school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_school_year:
            # UPDATED ERROR MESSAGE
            flash_message = (
                'Cannot add class: There is no active school year. '
                f'<a href="{url_for("management.school_years")}" class="alert-link">'
                'Please create or set an active school year here.</a>'
            )
            flash(flash_message, "danger")
            return redirect(url_for('management.classes'))

        # Create the class
        new_class = Class(
            name=class_name,
            subject=subject,
            teacher_id=teacher_id,
            school_year_id=current_school_year.id  # Add the active school year ID
        )
        db.session.add(new_class)
        db.session.commit()
        flash('Class added successfully!', 'success')
        return redirect(url_for('management.classes'))

    return render_template('add_class.html', available_teachers=available_teachers)





@management_blueprint.route('/class-grades-view/<int:class_id>')
@login_required
@management_required
def class_grades_view(class_id):
    """View class grades"""
    return render_template('class_grades_view.html', class_id=class_id)


@management_blueprint.route('/remove-class/<int:class_id>', methods=['POST'])
@login_required
@management_required
def remove_class(class_id):
    """Remove a class"""
    # This would delete the class from the database
    flash('Class removed successfully.', 'success')
    return redirect(url_for('management.classes'))


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
        
        if not all([title, class_id, due_date_str, quarter]):
            flash("Title, Class, Due Date, and Quarter are required.", "danger")
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
        new_assignment.quarter = int(quarter)
        
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

    # For GET request, get all classes for the dropdown
    classes = Class.query.all()
    return render_template('add_assignment.html', classes=classes)


@management_blueprint.route('/grade/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@management_required
def grade_assignment(assignment_id):
    """Grade an assignment - Directors and School Administrators can grade any assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
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
    
    return render_template('teacher_grade_assignment.html', 
                         assignment=assignment, 
                         class_obj=class_obj,
                         students=students, 
                         grades=grades, 
                         submissions=submissions)


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
    
    return render_template('view_assignment.html', 
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
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, due_date_str, quarter]):
            flash('Title, Due Date, and Quarter are required.', 'danger')
            return redirect(request.url)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Update assignment
            assignment.title = title
            assignment.description = description
            assignment.due_date = due_date
            assignment.quarter = int(quarter)
            
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
    
    return render_template('edit_assignment.html', 
                         assignment=assignment,
                         classes=classes,
                         school_years=school_years)


@management_blueprint.route('/remove-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
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
    
    return render_template('management_school_years.html', 
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
            academic_dates.append({
                'day': work_day.date.day,
                'title': f"{work_day.title} ({work_day.attendance_requirement})",
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
                academic_dates.append({
                    'day': school_break.start_date.day,
                    'title': f"{school_break.name} Start",
                    'category': school_break.break_type,
                    'type': 'school_break_start'
                })
            
            if school_break.end_date.month == month:
                academic_dates.append({
                    'day': school_break.end_date.day,
                    'title': f"{school_break.name} End",
                    'category': school_break.break_type,
                    'type': 'school_break_end'
                })
    
    return academic_dates


@management_blueprint.route('/upload-calendar-pdf', methods=['POST'])
@login_required
@management_required
def upload_calendar_pdf():
    """Upload and process a school calendar PDF."""
    if 'calendar_pdf' not in request.files:
        flash('No PDF file selected.', 'danger')
        return redirect(url_for('management.school_years'))
    
    file = request.files['calendar_pdf']
    school_year_id = request.form.get('school_year')
    calendar_name = request.form.get('calendar_name', 'School Calendar')
    
    if file.filename == '':
        flash('No PDF file selected.', 'danger')
        return redirect(url_for('management.school_years'))
    
    if not school_year_id:
        flash('Please select a school year.', 'danger')
        return redirect(url_for('management.school_years'))
    
    if file and file.filename.lower().endswith('.pdf'):
        try:
            # Save the PDF file
            filename = secure_filename(f"calendar_{school_year_id}_{int(time.time())}.pdf")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the PDF to extract calendar information
            calendar_data = process_calendar_pdf(filepath)
            
            # Store the calendar data in the database
            store_calendar_data(calendar_data, school_year_id, filename)
            
            flash(f'Calendar PDF uploaded and processed successfully! Found {len(calendar_data["holidays"])} holidays, {len(calendar_data["breaks"])} breaks, and {len(calendar_data["professional_development"])} PD days.', 'success')
            
        except Exception as e:
            flash(f'Error processing calendar PDF: {str(e)}', 'danger')
    else:
        flash('Please upload a valid PDF file.', 'danger')
    
    return redirect(url_for('management.school_years'))


def process_calendar_pdf(filepath):
    """Process a PDF calendar to extract important dates."""
    try:
        calendar_data = {
            'school_year_start': None,
            'school_year_end': None,
            'quarters': [],
            'holidays': [],
            'breaks': [],
            'professional_development': [],
            'parent_teacher_conferences': [],
            'early_dismissal': [],
            'no_school': []
        }
        
        # Try to extract text using pdfplumber first (better for complex layouts)
        try:
            with pdfplumber.open(filepath) as pdf:
                text_content = ""
                for page in pdf.pages:
                    if page.extract_text():
                        text_content += page.extract_text() + "\n"
        except Exception as e:
            current_app.logger.warning(f"pdfplumber failed, trying PyPDF2: {str(e)}")
            # Fallback to PyPDF2
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
        
        if not text_content.strip():
            raise Exception("Could not extract text from PDF")
        
        # Convert to lowercase for easier pattern matching
        text_lower = text_content.lower()
        
        # Extract school year dates
        calendar_data.update(extract_school_year_dates(text_content, text_lower))
        
        # Extract academic periods (quarters/semesters)
        calendar_data.update(extract_academic_periods(text_content, text_lower))
        
        # Extract holidays and special events
        calendar_data.update(extract_holidays_and_events(text_content, text_lower))
        
        # Extract breaks and vacations
        calendar_data.update(extract_breaks_and_vacations(text_content, text_lower))
        
        # Extract professional development and conference dates
        calendar_data.update(extract_professional_dates(text_content, text_lower))
        
        current_app.logger.info(f"Successfully processed PDF calendar: {len(calendar_data['holidays'])} holidays, {len(calendar_data['breaks'])} breaks found")
        
        return calendar_data
        
    except Exception as e:
        current_app.logger.error(f"Error processing PDF: {str(e)}")
        raise

def extract_school_year_dates(text_content, text_lower):
    """Extract school year start and end dates."""
    dates = {
        'school_year_start': None,
        'school_year_end': None
    }
    
    # Common patterns for school year dates
    patterns = [
        r'school\s+year\s+(\d{4})[-\s]+(\d{4})',
        r'(\d{4})[-\s]+(\d{4})\s+school\s+year',
        r'(\d{4})[-\s]+(\d{4})\s+academic\s+year',
        r'(\d{4})[-\s]+(\d{4})\s+calendar'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            year1, year2 = int(match.group(1)), int(match.group(2))
            # Assume school year starts in August/September and ends in May/June
            dates['school_year_start'] = date(year1, 8, 1)  # August 1st
            dates['school_year_end'] = date(year2, 6, 30)   # June 30th
            break
    
    # Look for specific start/end dates
    start_patterns = [
        r'first\s+day\s+of\s+school[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'school\s+starts[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'classes\s+begin[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    end_patterns = [
        r'last\s+day\s+of\s+school[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'school\s+ends[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'classes\s+end[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in start_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    dates['school_year_start'] = parsed_date
                    break
            except:
                continue
    
    for pattern in end_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    dates['school_year_end'] = parsed_date
                    break
            except:
                continue
    
    return dates

def extract_academic_periods(text_content, text_lower):
    """Extract quarter and semester dates."""
    periods = {
        'quarters': [],
        'semesters': []
    }
    
    # Quarter patterns
    quarter_patterns = [
        r'quarter\s+(\d)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'q(\d)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*quarter\s+(\d)'
    ]
    
    # Semester patterns
    semester_patterns = [
        r'semester\s+(\d)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r's(\d)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    # Extract quarters
    for pattern in quarter_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                if len(match.groups()) == 3:
                    if 'quarter' in pattern or 'q' in pattern:
                        quarter_num = int(match.group(1))
                        start_date = parse_date_string(match.group(2))
                        end_date = parse_date_string(match.group(3))
                    else:
                        start_date = parse_date_string(match.group(1))
                        end_date = parse_date_string(match.group(2))
                        quarter_num = int(match.group(3))
                    
                    if start_date and end_date:
                        periods['quarters'].append({
                            'name': f'Q{quarter_num}',
                            'start_date': start_date,
                            'end_date': end_date
                        })
            except:
                continue
    
    # Extract semesters
    for pattern in semester_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                semester_num = int(match.group(1))
                start_date = parse_date_string(match.group(2))
                end_date = parse_date_string(match.group(3))
                
                if start_date and end_date:
                    periods['semesters'].append({
                        'name': f'S{semester_num}',
                        'start_date': start_date,
                        'end_date': end_date
                    })
            except:
                continue
    
    return periods

def extract_holidays_and_events(text_content, text_lower):
    """Extract holidays and special event dates."""
    events = {
        'holidays': [],
        'parent_teacher_conferences': [],
        'early_dismissal': [],
        'no_school': []
    }
    
    # Common holiday patterns
    holiday_patterns = [
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*labor\s+day', 'Labor Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*columbus\s+day', 'Columbus Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*veterans\s+day', 'Veterans Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*thanksgiving', 'Thanksgiving'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*christmas', 'Christmas'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*new\s+year', 'New Year'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*martin\s+luther\s+king', 'Martin Luther King Jr. Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*presidents\s+day', 'Presidents Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*memorial\s+day', 'Memorial Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*independence\s+day', 'Independence Day')
    ]
    
    for pattern, holiday_name in holiday_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    events['holidays'].append({
                        'name': holiday_name,
                        'date': parsed_date
                    })
            except:
                continue
    
    # Parent-teacher conference patterns
    ptc_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*parent[-\s]*teacher\s+conference',
        r'parent[-\s]*teacher\s+conference[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'ptc[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in ptc_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    events['parent_teacher_conferences'].append({
                        'name': 'Parent-Teacher Conference',
                        'date': parsed_date
                    })
            except:
                continue
    
    # Early dismissal patterns
    early_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*early\s+dismissal',
        r'early\s+dismissal[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in early_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    events['early_dismissal'].append({
                        'name': 'Early Dismissal',
                        'date': parsed_date
                    })
            except:
                continue
    
    # No school patterns
    no_school_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*no\s+school',
        r'no\s+school[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*school\s+closed',
        r'school\s+closed[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in no_school_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    events['no_school'].append({
                        'name': 'No School',
                        'date': parsed_date
                    })
            except:
                continue
    
    return events

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
    
    return render_template('view_class.html', 
                         class_info=class_info,
                         teacher=teacher,
                         enrolled_students=enrolled_students,
                         assignments=assignments,
                         today=today)


@management_blueprint.route('/edit-class/<int:class_id>', methods=['GET', 'POST'])
@login_required
@management_required
def edit_class(class_id):
    """Edit class information"""
    class_info = Class.query.get_or_404(class_id)
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        teacher_id = request.form.get('teacher_id', type=int)
        
        # Validate required fields
        if not all([name, subject, teacher_id]):
            flash('Class name, subject, and teacher are required.', 'danger')
            return redirect(request.url)
        
        try:
            # Update class information
            class_info.name = name
            class_info.subject = subject
            class_info.teacher_id = teacher_id
            
            db.session.commit()
            flash('Class updated successfully!', 'success')
            return redirect(url_for('management.classes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating class: {str(e)}', 'danger')
            return redirect(request.url)
    
    # For GET request, get all teachers for the dropdown
    teachers = TeacherStaff.query.all()
    available_teachers = []
    for t in teachers:
        user = User.query.filter_by(teacher_staff_id=t.id).first()
        username = user.username if user else ''
        name = f"{t.first_name} {t.last_name}"
        available_teachers.append({'id': t.id, 'name': name, 'username': username})
    
    return render_template('edit_class.html', 
                         class_info=class_info,
                         available_teachers=available_teachers)


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
    
    return render_template('manage_class_roster.html', 
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

def store_calendar_data(calendar_data, school_year_id, pdf_filename):
    """Store extracted calendar data in the database."""
    try:
        # Clear existing calendar events for this school year
        CalendarEvent.query.filter_by(school_year_id=school_year_id).delete()
        
        events_added = 0
        
        # Store holidays
        for holiday in calendar_data.get('holidays', []):
            event = CalendarEvent(
                school_year_id=school_year_id,
                event_type='holiday',
                name=holiday['name'],
                start_date=holiday['date'],
                end_date=holiday['date'],
                pdf_filename=pdf_filename
            )
            db.session.add(event)
            events_added += 1
        
        # Store breaks
        for break_event in calendar_data.get('breaks', []):
            event = CalendarEvent(
                school_year_id=school_year_id,
                event_type='break',
                name=break_event['name'],
                start_date=break_event['start_date'],
                end_date=break_event['end_date'],
                pdf_filename=pdf_filename
            )
            db.session.add(event)
            events_added += 1
        
        # Store professional development days
        for pd_day in calendar_data.get('professional_development', []):
            event = CalendarEvent(
                school_year_id=school_year_id,
                event_type='professional_development',
                name=pd_day['name'],
                start_date=pd_day['date'],
                end_date=pd_day['date'],
                pdf_filename=pdf_filename
            )
            db.session.add(event)
            events_added += 1
        
        # Store parent-teacher conferences
        for ptc in calendar_data.get('parent_teacher_conferences', []):
            event = CalendarEvent(
                school_year_id=school_year_id,
                event_type='parent_teacher_conference',
                name=ptc['name'],
                start_date=ptc['date'],
                end_date=ptc['date'],
                pdf_filename=pdf_filename
            )
            db.session.add(event)
            events_added += 1
        
        # Store early dismissal days
        for early in calendar_data.get('early_dismissal', []):
            event = CalendarEvent(
                school_year_id=school_year_id,
                event_type='early_dismissal',
                name=early['name'],
                start_date=early['date'],
                end_date=early['date'],
                pdf_filename=pdf_filename
            )
            db.session.add(event)
            events_added += 1
        
        # Store no school days
        for no_school in calendar_data.get('no_school', []):
            event = CalendarEvent(
                school_year_id=school_year_id,
                event_type='no_school',
                name=no_school['name'],
                start_date=no_school['date'],
                end_date=no_school['date'],
                pdf_filename=pdf_filename
            )
            db.session.add(event)
            events_added += 1
        
        # Store academic periods if found
        for quarter in calendar_data.get('quarters', []):
            event = CalendarEvent(
                school_year_id=school_year_id,
                event_type='quarter',
                name=quarter['name'],
                start_date=quarter['start_date'],
                end_date=quarter['end_date'],
                pdf_filename=pdf_filename
            )
            db.session.add(event)
            events_added += 1
        
        for semester in calendar_data.get('semesters', []):
            event = CalendarEvent(
                school_year_id=school_year_id,
                event_type='semester',
                name=semester['name'],
                start_date=semester['start_date'],
                end_date=semester['end_date'],
                pdf_filename=pdf_filename
            )
            db.session.add(event)
            events_added += 1
        
        db.session.commit()
        current_app.logger.info(f"Stored {events_added} calendar events in database")
        
    except Exception as e:
        current_app.logger.error(f"Error storing calendar data: {str(e)}")
        db.session.rollback()
        raise
