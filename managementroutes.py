from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from models import db, Student, TeacherStaff, Class, SchoolYear, User, ReportCard, Assignment, Announcement, Message, MessageGroup, ScheduledAnnouncement, Notification, MessageGroupMember, Grade, Enrollment, Attendance
from decorators import management_required
from app import calculate_and_get_grade_for_student, get_grade_for_student
try:
    import pdfkit  # type: ignore
except ImportError:
    pdfkit = None
import os
import json
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

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
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('assigned_role', 'Teacher').strip()
        hire_date = request.form.get('hire_date', '').strip()
        # Handle multiple department selections
        departments = request.form.getlist('department')
        department = ', '.join(departments) if departments else ''
        position = request.form.get('position', '').strip()
        
        # Auto-assign role and department for Tech users
        if current_user.role in ['Tech', 'IT Support']:
            role = 'IT Support'
            department = 'Administration'
        
        # Address fields
        street = request.form.get('street_address', '').strip()
        apt_unit = request.form.get('apt_unit_suite', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        zip_code = request.form.get('zip_code', '').strip()
        phone = request.form.get('phone', '').strip()
        
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
            teacher_staff.last_name = last_name
            teacher_staff.email = email
            teacher_staff.hire_date = hire_date
            teacher_staff.department = department
            teacher_staff.position = position
            
            # Address fields
            teacher_staff.street = street
            teacher_staff.apt_unit = apt_unit
            teacher_staff.city = city
            teacher_staff.state = state
            teacher_staff.zip_code = zip_code
            teacher_staff.phone = phone
            
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
            user.role = role
            user.teacher_staff_id = teacher_staff.id
            
            db.session.add(user)
            db.session.commit()
            
            # Show success message with credentials
            flash(f'{role} added successfully! Username: {username}, Password: {password}, Staff ID: {teacher_staff.staff_id}', 'success')
            return redirect(url_for('management.teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding {role.lower()}: {str(e)}', 'danger')
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
    students = Student.query.order_by(Student.last_name, Student.first_name).all()
    return render_template('role_dashboard.html', 
                         students=students,
                         section='students',
                         active_tab='students')

@management_blueprint.route('/teachers')
@login_required
@management_required
def teachers():
    teachers = TeacherStaff.query.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()
    return render_template('role_dashboard.html', 
                         teachers=teachers,
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
    return render_template('role_dashboard.html',
                         assignments=assignments,
                         classes=classes,
                         today=datetime.now(),
                         section='assignments',
                         active_tab='assignments')

@management_blueprint.route('/attendance')
@login_required
@management_required
def attendance():
    classes = Class.query.all()
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
                week_data.append({'day_num': day, 'is_current_month': True, 'is_today': is_today, 'events': []})
        calendar_data['weeks'].append(week_data)
    
    return render_template('role_dashboard.html', 
                         calendar_data=calendar_data,
                         prev_month=prev_month,
                         next_month=next_month,
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

@management_blueprint.route('/communications')
@login_required
@management_required
def communications():
    """Enhanced communications hub with unified inbox."""
    # Get all messages for the admin
    messages = Message.query.filter(
        (Message.recipient_id == current_user.id) |
        (Message.sender_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    
    # Get announcements
    announcements = Announcement.query.order_by(Announcement.timestamp.desc()).all()
    
    # Get message groups
    groups = MessageGroup.query.filter_by(is_active=True).all()
    
    # Get scheduled announcements
    scheduled = ScheduledAnnouncement.query.filter_by(is_sent=False).order_by(ScheduledAnnouncement.scheduled_for).all()
    
    # Get notifications
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).limit(10).all()
    
    return render_template('management_communications.html',
                         messages=messages,
                         announcements=announcements,
                         groups=groups,
                         scheduled=scheduled,
                         notifications=notifications,
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


@management_blueprint.route('/view-assignment/<int:assignment_id>')
@login_required
@management_required
def view_assignment(assignment_id):
    """View assignment details"""
    return render_template('view_assignment.html', assignment_id=assignment_id)


@management_blueprint.route('/edit-assignment/<int:assignment_id>')
@login_required
@management_required
def edit_assignment(assignment_id):
    """Edit an assignment"""
    return render_template('edit_assignment.html', assignment_id=assignment_id)


@management_blueprint.route('/remove-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    # This would delete the assignment from the database
    flash('Assignment removed successfully.', 'success')
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
        teacher.last_name = request.form.get('last_name', teacher.last_name)
        teacher.email = request.form.get('email', teacher.email)
        teacher.phone = request.form.get('phone', teacher.phone)
        
        # Role and department
        teacher.position = request.form.get('position', teacher.position)
        # Handle multiple department selections
        departments = request.form.getlist('department')
        teacher.department = ', '.join(departments) if departments else teacher.department
        
        # Auto-assign role and department for Tech users
        if current_user.role in ['Tech', 'IT Support']:
            teacher.department = 'Administration'
        
        # Address information
        teacher.street = request.form.get('street', teacher.street)
        teacher.apt_unit = request.form.get('apt_unit', teacher.apt_unit)
        teacher.city = request.form.get('city', teacher.city)
        teacher.state = request.form.get('state', teacher.state)
        teacher.zip_code = request.form.get('zip_code', teacher.zip_code)
        
        # Emergency contact information
        teacher.emergency_first_name = request.form.get('emergency_first_name', teacher.emergency_first_name)
        teacher.emergency_last_name = request.form.get('emergency_last_name', teacher.emergency_last_name)
        teacher.emergency_email = request.form.get('emergency_email', teacher.emergency_email)
        teacher.emergency_phone = request.form.get('emergency_phone', teacher.emergency_phone)
        teacher.emergency_relationship = request.form.get('emergency_relationship', teacher.emergency_relationship)
        
        # Update user role if user account exists
        if teacher.user:
            # Auto-assign role for Tech users
            if current_user.role in ['Tech', 'IT Support']:
                teacher.user.role = 'IT Support'
            else:
                teacher.user.role = request.form.get('role', teacher.user.role)
        
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
        db.session.commit()
        flash(f'School year "{name}" created successfully!', 'success')
        return redirect(url_for('management.school_years'))

    school_years = SchoolYear.query.order_by(SchoolYear.start_date.desc()).all()
    return render_template('management_school_years.html', school_years=school_years)


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
    
    # Get enrolled students (placeholder - would need enrollment system)
    enrolled_students = []  # This would be populated from enrollment system
    
    # Get assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).all()
    
    return render_template('view_class.html', 
                         class_info=class_info,
                         teacher=teacher,
                         enrolled_students=enrolled_students,
                         assignments=assignments)


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
