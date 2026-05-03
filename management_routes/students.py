"""
Students routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify, session
from flask_login import login_required, current_user
from decorators import management_required, teacher_required, permissions_required
from models import (
    db, Student, User, Enrollment, Class, Grade, Assignment, ReportCard, SchoolYear,
    Attendance, SchoolDayAttendance, StudentGoal, StudentGroupMember, StudentGroup, Submission,
    GroupSubmission, GroupGrade, GroupAssignment, AssignmentExtension, MessageGroupMember, Notification,
    QuizAnswer, QuizProgress, DiscussionPost, GroupQuizAnswer, CleaningTeamMember,
    CleaningTeam, CleaningInspection, GradeHistory
)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, text, exists
from datetime import datetime, timedelta, date
import os
import json
import csv
import io
import uuid
import random
from .utils import allowed_file
from utils.student_login_policy import grade_may_have_login, parse_grade_level_for_policy
from utils.credential_modal import student_grade3_plus_modal_payload, student_k2_modal_payload
from services.google_directory_service import create_google_user
from services.google_sync_tasks import sync_single_user_to_google, DEFAULT_TEMP_PASSWORD

bp = Blueprint('students', __name__)

STUDENTS_PER_PAGE = 40


def _strip_student_user_account(student):
    """Remove portal login only; keep Student row and academic history."""
    if not getattr(student, 'user', None):
        return
    user = student.user
    Notification.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    MessageGroupMember.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.delete(user)


def _provision_student_login_if_needed(student):
    """
    Create a Student User for grade 3+ when missing. Caller commits.

    Returns:
        None if no new account was created.
        Dict with portal + Workspace fields when a new User row was added (for UI / email).
    """
    if not grade_may_have_login(student.grade_level):
        return None
    if getattr(student, 'is_deleted', False) or student.user:
        return None
    first_name = (student.first_name or '').strip()
    last_name = (student.last_name or '').strip()
    if not first_name or not last_name:
        return None

    generated_workspace_email = student.generate_email()
    if not generated_workspace_email:
        return None

    if not student.email:
        student.email = generated_workspace_email

    base_username = f"{first_name[0].lower()}{last_name.lower()}"
    username = base_username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1

    dob = student.dob or ''
    year = dob.split('-')[0] if '-' in dob else str(random.randint(2000, 2010))
    password = f"{first_name.lower()}{year[-4:]}"

    user = User()
    user.username = username
    user.password_hash = generate_password_hash(password)
    user.role = 'Student'
    user.student_id = student.id
    user.email = student.email
    user.google_workspace_email = generated_workspace_email
    user.is_temporary_password = True
    user.password_changed_at = None
    db.session.add(user)
    from services.google_sync_tasks import DEFAULT_TEMP_PASSWORD

    return {
        "username": username,
        "portal_password": password,
        "school_email": generated_workspace_email,
        "google_initial_password": DEFAULT_TEMP_PASSWORD,
    }


def _build_entrance_school_year_options(start_year=2020):
    """Return school-year labels from current year back to start_year."""
    today = date.today()
    current_start_year = today.year if today.month >= 7 else today.year - 1
    return [f"{year}-{year + 1}" for year in range(current_start_year, start_year - 1, -1)]


def _is_valid_school_year_label(value):
    """Validate 'YYYY-YYYY' format where second year = first + 1."""
    if not value or not isinstance(value, str):
        return False
    raw = value.strip()
    if len(raw) != 9 or raw[4] != '-':
        return False
    left, right = raw.split('-', 1)
    if not (left.isdigit() and right.isdigit()):
        return False
    return int(right) == int(left) + 1


def _calculate_expected_grad_date(grade_level, entrance_school_year):
    """Estimate expected graduation month/year from grade and entrance year."""
    if grade_level is None or not _is_valid_school_year_label(entrance_school_year):
        return None
    try:
        start_year = int(str(entrance_school_year).split('-', 1)[0])
        years_to_graduation = 12 - int(grade_level)
        if years_to_graduation < 0:
            years_to_graduation = 0
        return f"06/{start_year + years_to_graduation}"
    except (TypeError, ValueError):
        return None


def _student_ou_path(grade_level: int, grad_year: int | None) -> str:
    """
    Map a student to the desired Google OU path.
    Example: /Students/Elementary/Class of 2034
    """
    base = "/Students"
    if grad_year is None:
        return base

    # Match your Admin Console structure: Elementary / Middle School / High School
    if grade_level is None:
        school_level = None
    elif int(grade_level) <= 5:
        school_level = "Elementary"
    elif 6 <= int(grade_level) <= 8:
        school_level = "Middle School"
    else:
        school_level = "High School"

    if not school_level:
        return base
    return f"{base}/{school_level}/Class of {int(grad_year)}"


# ============================================================
# Route: /add-student', methods=['GET', 'POST']
# Function: add_student
# ============================================================

@bp.route('/add-student', methods=['GET', 'POST'])
@login_required
@permissions_required('students:edit')
def add_student():
    """Add a new student"""
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('student_first_name', '').strip()
        last_name = request.form.get('student_last_name', '').strip()
        dob = request.form.get('dob', '').strip()
        grade_level_str = request.form.get('grade_level', '').strip()
        gender = request.form.get('gender', '').strip()
        entrance_school_year = request.form.get('entrance_date', '').strip()
        
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
        
        # Validate that emergency_phone is not an email and is not too long
        if emergency_phone:
            if '@' in emergency_phone or len(emergency_phone) > 20:
                flash('Emergency phone number is invalid. Please enter a valid phone number (max 20 characters).', 'danger')
                return redirect(request.url)
        
        # Validate parent phone numbers as well
        if parent1_phone and len(parent1_phone) > 20:
            flash('Parent 1 phone number is too long. Please enter a valid phone number (max 20 characters).', 'danger')
            return redirect(request.url)
        
        if parent2_phone and len(parent2_phone) > 20:
            flash('Parent 2 phone number is too long. Please enter a valid phone number (max 20 characters).', 'danger')
            return redirect(request.url)
        
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
        
        # Validate required fields (use 'is not None' for grade_level since 0 is valid for Kindergarten)
        if not first_name or not last_name or not dob or grade_level is None:
            flash('First name, last name, date of birth, and grade level are required.', 'danger')
            return redirect(request.url)

        if not gender:
            flash('Gender is required for student records and report card confirmation.', 'danger')
            return redirect(request.url)

        if gender not in ['Male', 'Female', 'Non-binary', 'Prefer not to say', 'Other']:
            flash('Please select a valid gender option.', 'danger')
            return redirect(request.url)

        if not _is_valid_school_year_label(entrance_school_year):
            flash('Entrance school year is required and must use format YYYY-YYYY.', 'danger')
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
            student.gender = gender
            student.entrance_date = entrance_school_year
            student.expected_grad_date = _calculate_expected_grad_date(grade_level, entrance_school_year)
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
            
            # Check if student ID already exists
            existing_student = Student.query.filter_by(student_id=student.student_id).first()
            if existing_student:
                flash(f'A student with ID {student.student_id} already exists: {existing_student.first_name} {existing_student.last_name}. This student may have already been added. Please check the student list or contact support if you believe this is an error.', 'danger')
                return redirect(request.url)
            
            db.session.add(student)
            db.session.flush()  # Get the student ID
            
            # Workspace email (3rd grade+ only): Student.generate_email() → FirstnameLastinitialmmyy@...
            generated_workspace_email = None
            if grade_may_have_login(grade_level):
                generated_workspace_email = student.generate_email()

            # If no personal email was provided in the form, use the generated workspace address (grade 3+)
            if not email and generated_workspace_email:
                student.email = generated_workspace_email

            if grade_may_have_login(grade_level):
                user = User()
                user.username = username
                user.password_hash = generate_password_hash(password)
                user.role = 'Student'
                user.student_id = student.id
                user.email = student.email
                user.google_workspace_email = generated_workspace_email
                user.is_temporary_password = True
                user.password_changed_at = None
                db.session.add(user)
                db.session.commit()

                google_warning = None
                google_user_created = False

                try:
                    sync_single_user_to_google(user.id)
                except Exception as e:
                    current_app.logger.warning(
                        "Google Directory sync after save failed for user %s: %s", user.id, e
                    )
                    google_warning = (
                        "Google Directory sync failed after save; the account may update on the next sync run."
                    )

                try:
                    grad_year = None
                    if hasattr(student, "grad_year") and getattr(student, "grad_year"):
                        grad_year = int(getattr(student, "grad_year"))
                    elif student.expected_grad_date and "/" in str(student.expected_grad_date):
                        grad_year = int(str(student.expected_grad_date).split("/", 1)[1])

                    ou_path = _student_ou_path(student.grade_level, grad_year)
                    if generated_workspace_email:
                        created = create_google_user(
                            {
                                "primaryEmail": generated_workspace_email,
                                "name": {"givenName": student.first_name, "familyName": student.last_name},
                                "password": DEFAULT_TEMP_PASSWORD,
                                "orgUnitPath": ou_path,
                                "changePasswordAtNextLogin": True,
                            }
                        )
                        google_user_created = bool(created)
                        if not created:
                            google_warning = (
                                f"Google account creation failed for {generated_workspace_email}. "
                                "Verify the account does not already exist and that Directory permissions are configured."
                            )
                    else:
                        google_warning = (
                            "No Google Workspace email was generated, so no Google user was created."
                        )
                except Exception as e:
                    current_app.logger.error(f"Failed to auto-create Google student account: {e}")
                    google_warning = (
                        "Google account creation encountered an error. Check server logs for details."
                    )

                session["credential_modal"] = student_grade3_plus_modal_payload(
                    first_name=first_name,
                    last_name=last_name,
                    student_id=student.student_id or "",
                    username=username,
                    portal_password=password,
                    school_email=generated_workspace_email,
                    google_initial_password=DEFAULT_TEMP_PASSWORD,
                    google_user_created=google_user_created,
                    google_warning=google_warning,
                )
                flash("Student saved. Use the credential summary popup to copy login details.", "success")
            else:
                db.session.commit()
                session["credential_modal"] = student_k2_modal_payload(
                    first_name=first_name,
                    last_name=last_name,
                    student_id=student.student_id or "",
                    grade_level=grade_level,
                    entrance_school_year=entrance_school_year,
                )
                flash("Student saved. Review the K–2 policy summary in the popup.", "success")
            return redirect(url_for('management.students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template(
        'students/add_student.html',
        entrance_school_year_options=_build_entrance_school_year_options()
    )



# ============================================================
# Route: /class/<int:class_id>/enrolled-students-json', methods=['GET']
# Function: get_enrolled_students_json
# ============================================================

@bp.route('/class/<int:class_id>/enrolled-students-json', methods=['GET'])
@login_required
@management_required
def get_enrolled_students_json(class_id):
    """Get enrolled students for a class as JSON (for void modal)"""
    try:
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students_data = []
        
        for enrollment in enrollments:
            if enrollment.student:
                students_data.append({
                    'id': enrollment.student.id,
                    'first_name': enrollment.student.first_name,
                    'last_name': enrollment.student.last_name,
                    'grade_level': enrollment.student.grade_level,
                    'student_id': enrollment.student.student_id
                })
        
        return jsonify({'success': True, 'students': students_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



# ============================================================
# Route: /api/student/<int:student_id>/classes', methods=['GET']
# Function: get_student_classes
# ============================================================

@bp.route('/api/student/<int:student_id>/classes', methods=['GET'])
@login_required
@management_required
def get_student_classes(student_id):
    """Get all classes a student is actively enrolled in"""
    try:
        student = Student.query.get_or_404(student_id)
        enrollments = Enrollment.query.filter_by(student_id=student_id, is_active=True).all()
        
        classes_data = []
        for enrollment in enrollments:
            class_info = enrollment.class_info
            if class_info:
                classes_data.append({
                    'id': class_info.id,
                    'name': class_info.name,
                    'subject': class_info.subject or 'N/A',
                    'teacher_name': f"{class_info.teacher.first_name} {class_info.teacher.last_name}" if class_info.teacher else 'N/A'
                })
        
        return jsonify({
            'success': True,
            'classes': classes_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500



# ============================================================
# Route: /api/student/<int:student_id>/details', methods=['GET']
# Function: get_student_details
# ============================================================

@bp.route('/api/student/<int:student_id>/details', methods=['GET'])
@login_required
@management_required
def get_student_details(student_id):
    """Get detailed student information for report card confirmation"""
    try:
        student = Student.query.get_or_404(student_id)
        
        # Format address
        address_parts = []
        if student.street:
            address_parts.append(student.street)
        if student.apt_unit:
            address_parts.append(student.apt_unit)
        if student.city:
            address_parts.append(student.city)
        if student.state:
            address_parts.append(student.state)
        if student.zip_code:
            address_parts.append(student.zip_code)
        address = ', '.join(address_parts) if address_parts else ''
        
        # Expected graduation date: prioritize stored value, then derive from entrance school year.
        expected_grad_date = getattr(student, 'expected_grad_date', None) or _calculate_expected_grad_date(
            student.grade_level, getattr(student, 'entrance_date', None)
        )
        
        # Format student ID
        student_id_formatted = student.student_id if student.student_id else 'N/A'
        if hasattr(student, 'student_id_formatted'):
            student_id_formatted = student.student_id_formatted
        
        # Get SSN/State ID (might not exist in model)
        ssn = getattr(student, 'ssn', None) or getattr(student, 'state_student_id', None) or 'N/A'
        
        gender = getattr(student, 'gender', None) or ''
        
        # Format DOB
        dob = student.dob if student.dob else 'N/A'
        
        entrance_date = getattr(student, 'entrance_date', None) or ''
        
        student_data = {
            'first_name': student.first_name,
            'last_name': student.last_name,
            'student_id': student_id_formatted,
            'gender': gender,
            'grade_level': student.grade_level,
            'address': address,
            'dob': dob,
            'state_id': ssn,
            'entrance_date': entrance_date,
            'expected_grad_date': expected_grad_date or ''
        }
        
        return jsonify({
            'success': True,
            'student': student_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Report Card Generation


# ============================================================
# Route: /students
# Function: students
# ============================================================

@bp.route('/students')
@login_required
@permissions_required('students:view', 'students:edit')
def students():
    # Get search parameters
    search_query = request.args.get('search', '').strip()
    search_type = request.args.get('search_type', 'all')
    grade_filter = request.args.get('grade_level', '')
    status_filter = request.args.get('status', '')
    alert_filter = request.args.get('alert_filter', '').strip()
    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'asc')
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    
    # Build the query (exclude soft-deleted students by default, unless requested)
    if status_filter == 'former':
        query = Student.query.filter(Student.is_deleted == True)
    elif status_filter == 'all':
        query = Student.query
    else:
        query = Student.query.filter(Student.is_deleted == False)
    
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

    if alert_filter == 'critical':
        query = query.filter(Student.gpa.isnot(None), Student.gpa < 2.0)
    elif alert_filter == 'warning':
        query = query.filter(Student.gpa.isnot(None), Student.gpa >= 2.0, Student.gpa < 3.0)
    elif alert_filter == 'good':
        query = query.filter(Student.gpa.isnot(None), Student.gpa >= 3.0)
    
    # Apply status filter (account status) — only has_account / no_account
    # Use EXISTS on user.student_id; Student.user.isnot(None) breaks on SQLAlchemy 2.x.
    _has_login = exists().where(User.student_id == Student.id)
    if status_filter in ('has_account', 'no_account'):
        if status_filter == 'has_account':
            query = query.filter(_has_login)
        else:
            query = query.filter(~_has_login)
    
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
    elif sort_by == 'gpa_desc':
        query = query.order_by(Student.gpa.desc(), Student.last_name, Student.first_name)
    else:
        # Default sorting
        query = query.order_by(Student.last_name, Student.first_name)
    
    stats_query = query
    total_students = stats_query.count()
    students_with_accounts = stats_query.filter(
        exists().where(User.student_id == Student.id)
    ).count()
    students_without_accounts = total_students - students_with_accounts
    high_gpa_count = stats_query.filter(Student.gpa.isnot(None), Student.gpa >= 3.5).count()

    pagination = query.paginate(page=page, per_page=STUDENTS_PER_PAGE, error_out=False)
    students = pagination.items
    
    return render_template('management/role_dashboard.html', 
                         students=students,
                         pagination=pagination,
                         search_query=search_query,
                         search_type=search_type,
                         grade_filter=grade_filter,
                         status_filter=status_filter,
                         alert_filter=alert_filter,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_students=total_students,
                         students_with_accounts=students_with_accounts,
                         students_without_accounts=students_without_accounts,
                         high_gpa_count=high_gpa_count,
                         section='students',
                         active_tab='students')


@bp.route('/students/mark-repeating', methods=['POST'])
@login_required
@permissions_required('students:edit')
def mark_students_repeating():
    """
    Bulk mark selected students as repeating and bump grad_year by 1.
    """
    student_ids = request.form.getlist('student_ids')
    if not student_ids:
        flash('No students selected.', 'warning')
        return redirect(url_for('management.students'))

    updated = 0
    try:
        for sid in student_ids:
            student = Student.query.get(int(sid))
            if not student or getattr(student, 'is_deleted', False):
                continue

            # Mark repeating
            student.is_repeating = True

            # Ensure grad_year exists; derive from expected_grad_date if needed
            grad_year = getattr(student, 'grad_year', None)
            if not grad_year and student.expected_grad_date and '/' in str(student.expected_grad_date):
                try:
                    grad_year = int(str(student.expected_grad_date).split('/', 1)[1])
                except Exception:
                    grad_year = None

            if grad_year:
                student.grad_year = int(grad_year) + 1

            # Audit timestamp (also used by automation for time-based policies)
            student.status_updated_at = datetime.utcnow()
            updated += 1

        db.session.commit()
        flash(f'Marked {updated} student(s) as repeating and updated graduation year.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to mark students repeating: {e}")
        flash('Failed to update selected students. Please try again.', 'danger')

    return redirect(url_for('management.students'))



# ============================================================
# Route: /students/download-csv
# Function: download_students_csv
# ============================================================

@bp.route('/students/download-csv')
@login_required
@management_required
def download_students_csv():
    """Download all students as a CSV file."""
    try:
        # Get all students
        students = Student.query.order_by(Student.last_name, Student.first_name).all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Student ID', 'First Name', 'Last Name', 'Date of Birth', 'Grade Level', 
            'Email', 'Street', 'Apt/Unit', 'City', 'State', 'Zip Code',
            'Parent 1 First Name', 'Parent 1 Last Name', 'Parent 1 Email', 'Parent 1 Phone', 'Parent 1 Relationship',
            'Parent 2 First Name', 'Parent 2 Last Name', 'Parent 2 Email', 'Parent 2 Phone', 'Parent 2 Relationship',
            'Emergency First Name', 'Emergency Last Name', 'Emergency Email', 'Emergency Phone', 'Emergency Relationship',
            'Previous School', 'Medical Concerns', 'Notes', 'GPA'
        ])
        
        # Write student data
        for student in students:
            writer.writerow([
                student.student_id or '',
                student.first_name or '',
                student.last_name or '',
                student.dob or '',
                student.grade_level or '',
                student.email or '',
                student.street or '',
                student.apt_unit or '',
                student.city or '',
                student.state or '',
                student.zip_code or '',
                student.parent1_first_name or '',
                student.parent1_last_name or '',
                student.parent1_email or '',
                student.parent1_phone or '',
                student.parent1_relationship or '',
                student.parent2_first_name or '',
                student.parent2_last_name or '',
                student.parent2_email or '',
                student.parent2_phone or '',
                student.parent2_relationship or '',
                student.emergency_first_name or '',
                student.emergency_last_name or '',
                student.emergency_email or '',
                student.emergency_phone or '',
                student.emergency_relationship or '',
                student.previous_school or '',
                student.medical_concerns or '',
                student.notes or '',
                student.gpa or ''
            ])
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=students_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error downloading students CSV: {e}")
        flash('Error downloading CSV file. Please try again.', 'error')
        return redirect(url_for('management.students'))



# ============================================================
# Route: /students/download-template
# Function: download_students_template
# ============================================================

@bp.route('/students/download-template')
@login_required
@management_required
def download_students_template():
    """Download a template CSV file for student upload."""
    try:
        # Create CSV template in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header (same as download, but with example data)
        writer.writerow([
            'Student ID', 'First Name', 'Last Name', 'Date of Birth', 'Grade Level', 
            'Email', 'Street', 'Apt/Unit', 'City', 'State', 'Zip Code',
            'Parent 1 First Name', 'Parent 1 Last Name', 'Parent 1 Email', 'Parent 1 Phone', 'Parent 1 Relationship',
            'Parent 2 First Name', 'Parent 2 Last Name', 'Parent 2 Email', 'Parent 2 Phone', 'Parent 2 Relationship',
            'Emergency First Name', 'Emergency Last Name', 'Emergency Email', 'Emergency Phone', 'Emergency Relationship',
            'Previous School', 'Medical Concerns', 'Notes', 'GPA'
        ])
        
        # Write example row
        writer.writerow([
            '',  # Student ID (auto-generated if empty)
            'John',  # First Name
            'Doe',  # Last Name
            '01/15/2010',  # Date of Birth (MM/DD/YYYY)
            '8',  # Grade Level
            'john.doe@example.com',  # Email
            '123 Main Street',  # Street
            'Apt 4B',  # Apt/Unit
            'Springfield',  # City
            'Illinois',  # State
            '62701',  # Zip Code
            'Jane',  # Parent 1 First Name
            'Doe',  # Parent 1 Last Name
            'jane.doe@example.com',  # Parent 1 Email
            '555-0100',  # Parent 1 Phone
            'Mother',  # Parent 1 Relationship
            'James',  # Parent 2 First Name
            'Doe',  # Parent 2 Last Name
            'james.doe@example.com',  # Parent 2 Email
            '555-0101',  # Parent 2 Phone
            'Father',  # Parent 2 Relationship
            'Emergency',  # Emergency First Name
            'Contact',  # Emergency Last Name
            'emergency@example.com',  # Emergency Email
            '555-0102',  # Emergency Phone
            'Grandmother',  # Emergency Relationship
            'Springfield Elementary',  # Previous School
            'None',  # Medical Concerns
            'Sample student',  # Notes
            '3.5'  # GPA
        ])
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=students_upload_template.csv'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error downloading template CSV: {e}")
        flash('Error downloading template file. Please try again.', 'error')
        return redirect(url_for('management.students'))



# ============================================================
# Route: /students/upload-csv', methods=['POST']
# Function: upload_students_csv
# ============================================================

@bp.route('/students/upload-csv', methods=['POST'])
@login_required
@management_required
def upload_students_csv():
    """Upload and process a CSV file with student data."""
    try:
        # Check if file was uploaded
        if 'csv_file' not in request.files:
            flash('No file selected. Please choose a CSV file to upload.', 'error')
            return redirect(url_for('management.students'))
        
        file = request.files['csv_file']
        
        # Check if file has a name
        if file.filename == '':
            flash('No file selected. Please choose a CSV file to upload.', 'error')
            return redirect(url_for('management.students'))
        
        # Check file extension
        if not file.filename.lower().endswith('.csv'):
            flash('Invalid file type. Please upload a CSV file.', 'error')
            return redirect(url_for('management.students'))
        
        # Read and process CSV
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        added_count = 0
        updated_count = 0
        error_count = 0
        errors = []
        touched_student_ids = set()
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header row
            try:
                # Validate required fields
                if not row.get('First Name') or not row.get('Last Name'):
                    errors.append(f"Row {row_num}: First Name and Last Name are required")
                    error_count += 1
                    continue
                
                # Check if student exists by student_id or by name+dob
                student = None
                if row.get('Student ID'):
                    student = Student.query.filter_by(student_id=row['Student ID']).first()
                
                # If no student found by ID, try to match by name and DOB
                if not student and row.get('Date of Birth'):
                    student = Student.query.filter_by(
                        first_name=row['First Name'].strip(),
                        last_name=row['Last Name'].strip(),
                        dob=row['Date of Birth'].strip()
                    ).first()
                
                # Parse grade level
                grade_level = None
                if row.get('Grade Level'):
                    try:
                        grade_level = int(row['Grade Level'])
                    except (ValueError, TypeError):
                        pass
                
                # Parse GPA
                gpa = 0.0
                if row.get('GPA'):
                    try:
                        gpa = float(row['GPA'])
                    except (ValueError, TypeError):
                        gpa = 0.0
                
                if student:
                    # Update existing student
                    student.first_name = row.get('First Name', '').strip()
                    student.last_name = row.get('Last Name', '').strip()
                    if row.get('Date of Birth'):
                        student.dob = row['Date of Birth'].strip()
                    if grade_level is not None:
                        student.grade_level = grade_level
                    if row.get('Email'):
                        student.email = row['Email'].strip()
                    if row.get('Street'):
                        student.street = row['Street'].strip()
                    if row.get('Apt/Unit'):
                        student.apt_unit = row['Apt/Unit'].strip()
                    if row.get('City'):
                        student.city = row['City'].strip()
                    if row.get('State'):
                        student.state = row['State'].strip()
                    if row.get('Zip Code'):
                        student.zip_code = row['Zip Code'].strip()
                    if row.get('Parent 1 First Name'):
                        student.parent1_first_name = row['Parent 1 First Name'].strip()
                    if row.get('Parent 1 Last Name'):
                        student.parent1_last_name = row['Parent 1 Last Name'].strip()
                    if row.get('Parent 1 Email'):
                        student.parent1_email = row['Parent 1 Email'].strip()
                    if row.get('Parent 1 Phone'):
                        student.parent1_phone = row['Parent 1 Phone'].strip()
                    if row.get('Parent 1 Relationship'):
                        student.parent1_relationship = row['Parent 1 Relationship'].strip()
                    if row.get('Parent 2 First Name'):
                        student.parent2_first_name = row['Parent 2 First Name'].strip()
                    if row.get('Parent 2 Last Name'):
                        student.parent2_last_name = row['Parent 2 Last Name'].strip()
                    if row.get('Parent 2 Email'):
                        student.parent2_email = row['Parent 2 Email'].strip()
                    if row.get('Parent 2 Phone'):
                        student.parent2_phone = row['Parent 2 Phone'].strip()
                    if row.get('Parent 2 Relationship'):
                        student.parent2_relationship = row['Parent 2 Relationship'].strip()
                    if row.get('Emergency First Name'):
                        student.emergency_first_name = row['Emergency First Name'].strip()
                    if row.get('Emergency Last Name'):
                        student.emergency_last_name = row['Emergency Last Name'].strip()
                    if row.get('Emergency Email'):
                        student.emergency_email = row['Emergency Email'].strip()
                    if row.get('Emergency Phone'):
                        student.emergency_phone = row['Emergency Phone'].strip()
                    if row.get('Emergency Relationship'):
                        student.emergency_relationship = row['Emergency Relationship'].strip()
                    if row.get('Previous School'):
                        student.previous_school = row['Previous School'].strip()
                    if row.get('Medical Concerns'):
                        student.medical_concerns = row['Medical Concerns'].strip()
                    if row.get('Notes'):
                        student.notes = row['Notes'].strip()
                    student.gpa = gpa
                    
                    updated_count += 1
                    touched_student_ids.add(student.id)
                else:
                    # Create new student
                    student = Student(
                        first_name=row.get('First Name', '').strip(),
                        last_name=row.get('Last Name', '').strip(),
                        dob=row.get('Date of Birth', '').strip() if row.get('Date of Birth') else None,
                        grade_level=grade_level,
                        email=row.get('Email', '').strip() if row.get('Email') else None,
                        street=row.get('Street', '').strip() if row.get('Street') else None,
                        apt_unit=row.get('Apt/Unit', '').strip() if row.get('Apt/Unit') else None,
                        city=row.get('City', '').strip() if row.get('City') else None,
                        state=row.get('State', '').strip() if row.get('State') else None,
                        zip_code=row.get('Zip Code', '').strip() if row.get('Zip Code') else None,
                        parent1_first_name=row.get('Parent 1 First Name', '').strip() if row.get('Parent 1 First Name') else None,
                        parent1_last_name=row.get('Parent 1 Last Name', '').strip() if row.get('Parent 1 Last Name') else None,
                        parent1_email=row.get('Parent 1 Email', '').strip() if row.get('Parent 1 Email') else None,
                        parent1_phone=row.get('Parent 1 Phone', '').strip() if row.get('Parent 1 Phone') else None,
                        parent1_relationship=row.get('Parent 1 Relationship', '').strip() if row.get('Parent 1 Relationship') else None,
                        parent2_first_name=row.get('Parent 2 First Name', '').strip() if row.get('Parent 2 First Name') else None,
                        parent2_last_name=row.get('Parent 2 Last Name', '').strip() if row.get('Parent 2 Last Name') else None,
                        parent2_email=row.get('Parent 2 Email', '').strip() if row.get('Parent 2 Email') else None,
                        parent2_phone=row.get('Parent 2 Phone', '').strip() if row.get('Parent 2 Phone') else None,
                        parent2_relationship=row.get('Parent 2 Relationship', '').strip() if row.get('Parent 2 Relationship') else None,
                        emergency_first_name=row.get('Emergency First Name', '').strip() if row.get('Emergency First Name') else None,
                        emergency_last_name=row.get('Emergency Last Name', '').strip() if row.get('Emergency Last Name') else None,
                        emergency_email=row.get('Emergency Email', '').strip() if row.get('Emergency Email') else None,
                        emergency_phone=row.get('Emergency Phone', '').strip() if row.get('Emergency Phone') else None,
                        emergency_relationship=row.get('Emergency Relationship', '').strip() if row.get('Emergency Relationship') else None,
                        previous_school=row.get('Previous School', '').strip() if row.get('Previous School') else None,
                        medical_concerns=row.get('Medical Concerns', '').strip() if row.get('Medical Concerns') else None,
                        notes=row.get('Notes', '').strip() if row.get('Notes') else None,
                        gpa=gpa
                    )
                    
                    # Generate student ID if not provided
                    if not row.get('Student ID') and student.state and student.dob:
                        student.student_id = student.generate_student_id()
                    elif row.get('Student ID'):
                        student.student_id = row['Student ID'].strip()
                    
                    db.session.add(student)
                    db.session.flush()
                    touched_student_ids.add(student.id)
                    added_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
                continue
        
        # Commit all changes
        try:
            db.session.commit()

            for sid in touched_student_ids:
                st = Student.query.get(sid)
                if not st or getattr(st, 'is_deleted', False):
                    continue
                if not grade_may_have_login(st.grade_level):
                    _strip_student_user_account(st)
                else:
                    _provision_student_login_if_needed(st)
            db.session.commit()
            
            # Prepare success message
            message_parts = []
            if added_count > 0:
                message_parts.append(f"{added_count} student(s) added")
            if updated_count > 0:
                message_parts.append(f"{updated_count} student(s) updated")
            
            if message_parts:
                flash(f"CSV upload successful: {', '.join(message_parts)}", 'success')
            
            if error_count > 0:
                error_msg = f"{error_count} error(s) occurred during upload."
                if len(errors) <= 10:
                    error_msg += " Errors: " + "; ".join(errors)
                else:
                    error_msg += f" First 10 errors: " + "; ".join(errors[:10])
                flash(error_msg, 'warning')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error committing CSV upload: {e}")
            flash(f'Error saving data: {str(e)}', 'error')
        
        return redirect(url_for('management.students'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing CSV upload: {e}")
        flash(f'Error processing CSV file: {str(e)}', 'error')
        return redirect(url_for('management.students'))



# ============================================================
# Route: /report-cards/student/<int:student_id>
# Function: student_report_card_history
# ============================================================

@bp.route('/report-cards/student/<int:student_id>')
@login_required
@management_required
def student_report_card_history(student_id):
    """View all report cards for a specific student (historical view)."""
    student = Student.query.get_or_404(student_id)
    
    # Get all report cards for this student, ordered by school year and quarter
    report_cards_list = ReportCard.query.filter_by(
        student_id=student_id
    ).join(SchoolYear).order_by(
        SchoolYear.start_date.desc(),
        ReportCard.quarter.desc()
    ).all()
    
    # Group by school year for better display
    report_cards_by_year = {}
    for rc in report_cards_list:
        year_name = rc.school_year.name if rc.school_year else 'Unknown'
        if year_name not in report_cards_by_year:
            report_cards_by_year[year_name] = []
        report_cards_by_year[year_name].append(rc)
    
    return render_template('management/student_report_card_history.html',
                         student=student,
                         report_cards_by_year=report_cards_by_year,
                         total_count=len(report_cards_list))



# ============================================================
# Route: /report-cards/generate/<int:student_id>
# Function: generate_report_card_for_student
# ============================================================

@bp.route('/report-cards/generate/<int:student_id>')
@login_required
@management_required
def generate_report_card_for_student(student_id):
    """Enhanced report card generation form for a specific student."""
    student = Student.query.get_or_404(student_id)
    category = request.args.get('category', '')
    
    # Get all data needed for the form
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    
    # Get student's enrolled classes
    from models import Enrollment
    enrollments = Enrollment.query.filter_by(
        student_id=student_id,
        is_active=True
    ).all()
    
    classes = [enrollment.class_info for enrollment in enrollments if enrollment.class_info]
    
    return render_template('management/report_card_generate_form.html',
                         student=student,
                         students=[student],  # For compatibility with existing template
                         school_years=school_years,
                         classes=classes,
                         category=category,
                         pre_selected_student=student_id,
                         entrance_school_year_options=_build_entrance_school_year_options())



# ============================================================
# Helper: _void_one_assignment_impl (no commit; used by single and bulk void)
# ============================================================

def _void_one_assignment_impl(assignment_id, assignment_type, student_ids, void_all, reason):
    """
    Void one assignment for the given students. Does not commit.
    Returns (voided_count, [(student_id, class_id, school_year_id, quarter), ...]).
    """
    voided_count = 0
    affected = []
    if assignment_type == 'group':
        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        class_id = group_assignment.class_id
        school_year_id = group_assignment.school_year_id
        quarter = group_assignment.quarter
        if void_all or not student_ids:
            # Void for all students in groups
            groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id).all()
            for group in groups:
                members = StudentGroupMember.query.filter_by(student_group_id=group.id).all()
                for member in members:
                    group_grade = GroupGrade.query.filter_by(
                        group_assignment_id=assignment_id,
                        student_id=member.student_id
                    ).first()
                    if group_grade:
                        if not group_grade.is_voided:
                            group_grade.is_voided = True
                            group_grade.voided_by = current_user.id
                            group_grade.voided_at = datetime.utcnow()
                            group_grade.voided_reason = reason
                            if group_grade.grade_data:
                                group_grade.grade_data = json.dumps({
                                    'score': 0,
                                    'points_earned': 0,
                                    'total_points': group_assignment.total_points if group_assignment.total_points else 100.0,
                                    'percentage': 0,
                                    'comment': '',
                                    'feedback': '',
                                    'is_voided': True
                                })
                            voided_count += 1
                            affected.append((member.student_id, class_id, school_year_id, quarter))
                    else:
                        new_group_grade = GroupGrade(
                            student_id=member.student_id,
                            group_assignment_id=assignment_id,
                            student_group_id=group.id,
                            grade_data=json.dumps({'score': 'N/A', 'comments': ''}),
                            is_voided=True,
                            voided_by=current_user.id,
                            voided_at=datetime.utcnow(),
                            voided_reason=reason,
                            graded_at=None
                        )
                        db.session.add(new_group_grade)
                        voided_count += 1
                        affected.append((member.student_id, class_id, school_year_id, quarter))
            return (voided_count, affected)
        else:
            # Void for specific students
            for student_id in student_ids:
                member = StudentGroupMember.query.filter_by(student_id=int(student_id)).first()
                if member:
                    group_grade = GroupGrade.query.filter_by(
                        group_assignment_id=assignment_id,
                        student_id=int(student_id)
                    ).first()
                    if group_grade:
                        if not group_grade.is_voided:
                            group_grade.is_voided = True
                            group_grade.voided_by = current_user.id
                            group_grade.voided_at = datetime.utcnow()
                            group_grade.voided_reason = reason
                            if group_grade.grade_data:
                                group_grade.grade_data = json.dumps({
                                    'score': 0,
                                    'points_earned': 0,
                                    'total_points': group_assignment.total_points if group_assignment.total_points else 100.0,
                                    'percentage': 0,
                                    'comment': '',
                                    'feedback': '',
                                    'is_voided': True
                                })
                            voided_count += 1
                            affected.append((int(student_id), class_id, school_year_id, quarter))
                    else:
                        new_group_grade = GroupGrade(
                            student_id=int(student_id),
                            group_assignment_id=assignment_id,
                            student_group_id=member.student_group_id,
                            grade_data=json.dumps({'score': 'N/A', 'comments': ''}),
                            is_voided=True,
                            voided_by=current_user.id,
                            voided_at=datetime.utcnow(),
                            voided_reason=reason,
                            graded_at=None
                        )
                        db.session.add(new_group_grade)
                        voided_count += 1
                        affected.append((int(student_id), class_id, school_year_id, quarter))
            return (voided_count, affected)
    else:
            assignment = Assignment.query.get_or_404(assignment_id)
            class_id = assignment.class_id
            school_year_id = assignment.school_year_id
            quarter = assignment.quarter
            if void_all or not student_ids:
                enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
                for enrollment in enrollments:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=enrollment.student_id
                    ).first()
                    if grade:
                        if not grade.is_voided:
                            original_grade_data = grade.grade_data
                            if original_grade_data:
                                try:
                                    history_entry = GradeHistory(
                                        grade_id=grade.id,
                                        student_id=grade.student_id,
                                        assignment_id=assignment_id,
                                        previous_grade_data=original_grade_data,
                                        new_grade_data=json.dumps({
                                            'score': 0,
                                            'points_earned': 0,
                                            'total_points': assignment.total_points if assignment.total_points else 100.0,
                                            'percentage': 0,
                                            'comment': '',
                                            'feedback': '',
                                            'is_voided': True
                                        }),
                                        changed_by=current_user.id,
                                        change_reason=f'Assignment voided: {reason}'
                                    )
                                    db.session.add(history_entry)
                                except Exception as e:
                                    current_app.logger.warning(f"Could not save grade history for grade {grade.id}: {e}")
                            grade.is_voided = True
                            grade.voided_by = current_user.id
                            grade.voided_at = datetime.utcnow()
                            grade.voided_reason = reason
                            if grade.grade_data:
                                grade.grade_data = json.dumps({
                                    'score': 0,
                                    'points_earned': 0,
                                    'total_points': assignment.total_points if assignment.total_points else 100.0,
                                    'percentage': 0,
                                    'comment': '',
                                    'feedback': '',
                                    'is_voided': True
                                })
                            voided_count += 1
                            affected.append((enrollment.student_id, class_id, school_year_id, quarter))
                    else:
                        new_grade = Grade(
                            student_id=enrollment.student_id,
                            assignment_id=assignment_id,
                            grade_data=json.dumps({'score': 'N/A', 'comments': ''}),
                            is_voided=True,
                            voided_by=current_user.id,
                            voided_at=datetime.utcnow(),
                            voided_reason=reason,
                            graded_at=None
                        )
                        db.session.add(new_grade)
                        voided_count += 1
                        affected.append((enrollment.student_id, class_id, school_year_id, quarter))
                return (voided_count, affected)
            else:
                for student_id in student_ids:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=int(student_id)
                    ).first()
                    if grade:
                        if not grade.is_voided:
                            original_grade_data = grade.grade_data
                            if original_grade_data:
                                try:
                                    history_entry = GradeHistory(
                                        grade_id=grade.id,
                                        student_id=grade.student_id,
                                        assignment_id=assignment_id,
                                        previous_grade_data=original_grade_data,
                                        new_grade_data=json.dumps({
                                            'score': 0,
                                            'points_earned': 0,
                                            'total_points': assignment.total_points if assignment.total_points else 100.0,
                                            'percentage': 0,
                                            'comment': '',
                                            'feedback': '',
                                            'is_voided': True
                                        }),
                                        changed_by=current_user.id,
                                        change_reason=f'Assignment voided: {reason}'
                                    )
                                    db.session.add(history_entry)
                                except Exception as e:
                                    current_app.logger.warning(f"Could not save grade history for grade {grade.id}: {e}")
                            grade.is_voided = True
                            grade.voided_by = current_user.id
                            grade.voided_at = datetime.utcnow()
                            grade.voided_reason = reason
                            if grade.grade_data:
                                grade.grade_data = json.dumps({
                                    'score': 0,
                                    'points_earned': 0,
                                    'total_points': assignment.total_points if assignment.total_points else 100.0,
                                    'percentage': 0,
                                    'comment': '',
                                    'feedback': '',
                                    'is_voided': True
                                })
                            voided_count += 1
                            affected.append((int(student_id), class_id, school_year_id, quarter))
                    else:
                        new_grade = Grade(
                            student_id=int(student_id),
                            assignment_id=assignment_id,
                            grade_data=json.dumps({'score': 'N/A', 'comments': ''}),
                            is_voided=True,
                            voided_by=current_user.id,
                            voided_at=datetime.utcnow(),
                            voided_reason=reason,
                            graded_at=None
                        )
                        db.session.add(new_grade)
                        voided_count += 1
                        affected.append((int(student_id), class_id, school_year_id, quarter))
                return (voided_count, affected)


@bp.route('/void-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def void_assignment_for_students(assignment_id):
    """Void an assignment for all students or specific students."""
    try:
        assignment_type = request.form.get('assignment_type', 'individual')
        student_ids = request.form.getlist('student_ids')
        reason = request.form.get('reason', 'Voided by administrator')
        void_all = request.form.get('void_all', '').lower() == 'true'
        void_type = request.form.get('void_type', '')
        if not void_all and void_type == 'all':
            void_all = True
        voided_count, affected = _void_one_assignment_impl(
            assignment_id, assignment_type, student_ids, void_all, reason
        )
        db.session.commit()
        from utils.quarter_grade_calculator import update_quarter_grade
        seen = set()
        for (sid, cid, syid, q) in affected:
            key = (sid, cid, q)
            if key not in seen:
                seen.add(key)
                try:
                    update_quarter_grade(student_id=int(sid), class_id=cid, school_year_id=syid, quarter=q, force=True)
                except Exception as e:
                    current_app.logger.warning(f"Could not update quarter grade for student {sid}: {e}")
        message = f'Voided assignment for {voided_count} grade(s).'
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')
        if is_ajax:
            return jsonify({'success': True, 'message': message, 'voided_count': voided_count})
        flash(message, 'success')
        redirect_url = request.form.get('redirect_url', '').strip()
        if redirect_url and redirect_url.startswith('/'):
            return redirect(redirect_url)
        return redirect(url_for('management.assignments_and_grades'))
    except Exception as e:
        db.session.rollback()
        error_message = f'Error voiding assignment: {str(e)}'
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')
        if is_ajax:
            return jsonify({'success': False, 'message': error_message}), 500
        flash(error_message, 'danger')
        return redirect(url_for('management.assignments_and_grades'))


# ============================================================
# Route: /bulk-void-assignments', methods=['POST']
# Function: bulk_void_assignments
# ============================================================

@bp.route('/bulk-void-assignments', methods=['POST'])
@login_required
@management_required
def bulk_void_assignments():
    """Void multiple assignments at once for all or selected students."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        assignment_specs = data.get('assignment_specs', [])  # list of {id, type: 'individual'|'group'}
        if not assignment_specs:
            assignment_ids = data.get('assignment_ids', [])
            assignment_types = data.get('assignment_types', [])
            if not assignment_ids or len(assignment_types) != len(assignment_ids):
                return jsonify({'success': False, 'message': 'Provide assignment_specs or assignment_ids and assignment_types.'}), 400
            assignment_specs = [{'id': int(aid), 'type': t} for aid, t in zip(assignment_ids, assignment_types)]
        else:
            assignment_specs = [{'id': int(s['id']), 'type': s.get('type', 'individual')} for s in assignment_specs]
        if not assignment_specs:
            return jsonify({'success': False, 'message': 'No assignments selected.'}), 400
        void_all = data.get('void_all', True)
        student_ids = data.get('student_ids', [])
        if isinstance(student_ids, str):
            student_ids = [student_ids] if student_ids else []
        student_ids = [int(s) for s in student_ids]
        reason = data.get('reason', 'Voided by administrator')
        total_voided = 0
        all_affected = []
        errors = []
        for spec in assignment_specs:
            aid, atype = spec['id'], spec['type']
            try:
                voided_count, affected = _void_one_assignment_impl(aid, atype, student_ids, void_all, reason)
                total_voided += voided_count
                all_affected.extend(affected)
            except Exception as e:
                errors.append(f"Assignment {aid} ({atype}): {str(e)}")
                current_app.logger.warning(f"Bulk void failed for assignment {aid}: {e}")
        db.session.commit()
        from utils.quarter_grade_calculator import update_quarter_grade
        seen = set()
        for (sid, cid, syid, q) in all_affected:
            key = (sid, cid, q)
            if key not in seen:
                seen.add(key)
                try:
                    update_quarter_grade(student_id=int(sid), class_id=cid, school_year_id=syid, quarter=q, force=True)
                except Exception as e:
                    current_app.logger.warning(f"Could not update quarter grade for student {sid}: {e}")
        message = f'Bulk void complete: {total_voided} grade(s) voided across {len(assignment_specs)} assignment(s).'
        if errors:
            message += ' Partial errors: ' + '; '.join(errors[:3])
        return jsonify({
            'success': True,
            'message': message,
            'voided_count': total_voided,
            'assignments_processed': len(assignment_specs),
            'errors': errors
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# Route: /unvoid-assignment/<int:assignment_id>', methods=['POST']
# Function: unvoid_assignment_for_students
# ============================================================

@bp.route('/unvoid-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def unvoid_assignment_for_students(assignment_id):
    """Un-void an assignment (restore grades) for all students or specific students."""
    try:
        assignment_type = request.form.get('assignment_type', 'individual')
        student_ids = request.form.getlist('student_ids')
        unvoid_all = request.form.get('unvoid_all', 'false').lower() == 'true'
        
        unvoided_count = 0
        
        if assignment_type == 'group':
            from models import GroupAssignment, GroupGrade
            group_assignment = GroupAssignment.query.get_or_404(assignment_id)
            
            if unvoid_all or not student_ids:
                from models import StudentGroupMember, StudentGroup
                
                groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id).all()
                for group in groups:
                    members = StudentGroupMember.query.filter_by(student_group_id=group.id).all()
                    for member in members:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_id=member.student_id,
                            is_voided=True
                        ).first()
                        
                        if group_grade:
                            group_grade.is_voided = False
                            group_grade.voided_by = None
                            group_grade.voided_at = None
                            group_grade.voided_reason = None
                            unvoided_count += 1
                
                message = f'Restored group assignment "{group_assignment.title}" for all students ({unvoided_count} grades)'
            else:
                from models import StudentGroupMember
                for student_id in student_ids:
                    member = StudentGroupMember.query.filter_by(student_id=int(student_id)).first()
                    if member:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_id=int(student_id),
                            is_voided=True
                        ).first()
                        
                        if group_grade:
                            group_grade.is_voided = False
                            group_grade.voided_by = None
                            group_grade.voided_at = None
                            group_grade.voided_reason = None
                            unvoided_count += 1
                
                message = f'Restored group assignment "{group_assignment.title}" for {unvoided_count} student(s)'
        else:
            assignment = Assignment.query.get_or_404(assignment_id)
            
            if unvoid_all or not student_ids:
                # Unvoid for all students
                from models import Enrollment
                enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
                
                for enrollment in enrollments:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=enrollment.student_id,
                        is_voided=True
                    ).first()
                    
                    if grade:
                        # Restore grade data from history if available
                        from models import GradeHistory
                        history_entry = GradeHistory.query.filter_by(
                            grade_id=grade.id
                        ).order_by(GradeHistory.changed_at.desc()).first()
                        
                        if history_entry and history_entry.previous_grade_data:
                            # Restore original grade data from history
                            try:
                                grade.grade_data = history_entry.previous_grade_data
                            except Exception as e:
                                current_app.logger.warning(f"Could not restore grade data from history: {e}")
                        
                        grade.is_voided = False
                        grade.voided_by = None
                        grade.voided_at = None
                        grade.voided_reason = None
                        unvoided_count += 1
                
                message = f'Restored assignment "{assignment.title}" for all students ({unvoided_count} grades)'
            else:
                # Unvoid for specific students
                for student_id in student_ids:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=int(student_id),
                        is_voided=True
                    ).first()
                    
                    if grade:
                        # Restore grade data from history if available
                        from models import GradeHistory
                        history_entry = GradeHistory.query.filter_by(
                            grade_id=grade.id
                        ).order_by(GradeHistory.changed_at.desc()).first()
                        
                        if history_entry and history_entry.previous_grade_data:
                            # Restore original grade data from history
                            try:
                                grade.grade_data = history_entry.previous_grade_data
                            except Exception as e:
                                current_app.logger.warning(f"Could not restore grade data from history: {e}")
                        
                        grade.is_voided = False
                        grade.voided_by = None
                        grade.voided_at = None
                        grade.voided_reason = None
                        unvoided_count += 1
                
                message = f'Restored assignment "{assignment.title}" for {unvoided_count} student(s)'
        
        db.session.commit()
        
        # Update quarter grades for affected students (force recalculation)
        from utils.quarter_grade_calculator import update_quarter_grade
        if assignment_type == 'individual':
            quarter = assignment.quarter
            school_year_id = assignment.school_year_id
            class_id = assignment.class_id
        else:
            quarter = group_assignment.quarter
            school_year_id = group_assignment.school_year_id
            class_id = group_assignment.class_id
        
        # Refresh quarter grades for affected students
        students_to_update = []
        if student_ids:
            students_to_update = student_ids
        else:
            if assignment_type == 'individual':
                students_to_update = [g.student_id for g in Grade.query.filter_by(assignment_id=assignment_id).all()]
            else:
                students_to_update = [g.student_id for g in GroupGrade.query.filter_by(group_assignment_id=assignment_id).all()]
        
        for sid in students_to_update:
            try:
                update_quarter_grade(
                    student_id=int(sid),
                    class_id=class_id,
                    school_year_id=school_year_id,
                    quarter=quarter,
                    force=True
                )
            except Exception as e:
                current_app.logger.warning(f"Could not update quarter grade for student {sid}: {e}")
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')
        
        if is_ajax:
            return jsonify({'success': True, 'message': message, 'unvoided_count': unvoided_count})
        else:
            flash(message, 'success')
            return redirect(url_for('management.assignments_and_grades'))
        
    except Exception as e:
        db.session.rollback()
        error_message = f'Error unvoiding assignment: {str(e)}'
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')
        
        if is_ajax:
            return jsonify({'success': False, 'message': error_message}), 500
        else:
            flash(error_message, 'danger')
            return redirect(url_for('management.assignments_and_grades'))




# ============================================================
# Route: /class/<int:class_id>/students
# Function: get_class_students
# ============================================================

@bp.route('/class/<int:class_id>/students')
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



# ============================================================
# Route: /view-student/<int:student_id>
# Function: view_student
# ============================================================

@bp.route('/view-student/<int:student_id>')
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
        'gender': getattr(student, 'gender', None),
        'entrance_date': getattr(student, 'entrance_date', None),
        'expected_grad_date': getattr(student, 'expected_grad_date', None),
        'email': student.email,
        'google_workspace_email': student.user.google_workspace_email if student.user else None,
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




# ============================================================
# Route: /edit-student/<int:student_id>', methods=['POST']
# Function: edit_student
# ============================================================

@bp.route('/edit-student/<int:student_id>', methods=['POST'])
@login_required
@permissions_required('students:edit')
def edit_student(student_id):
    """Edit student information via AJAX modal"""
    student = Student.query.get_or_404(student_id)
    try:
        prev_grade = student.grade_level
        # Get phone numbers for validation
        parent1_phone = request.form.get('parent1_phone', student.parent1_phone)
        parent2_phone = request.form.get('parent2_phone', student.parent2_phone)
        emergency_phone = request.form.get('emergency_phone', student.emergency_phone)
        
        # Validate phone numbers
        if parent1_phone and (len(parent1_phone) > 20 or '@' in parent1_phone):
            return jsonify({'success': False, 'message': 'Parent 1 phone number is invalid. Please enter a valid phone number (max 20 characters).'}), 400
        
        if parent2_phone and (len(parent2_phone) > 20 or '@' in parent2_phone):
            return jsonify({'success': False, 'message': 'Parent 2 phone number is invalid. Please enter a valid phone number (max 20 characters).'}), 400
        
        if emergency_phone and (len(emergency_phone) > 20 or '@' in emergency_phone):
            return jsonify({'success': False, 'message': 'Emergency phone number is invalid. Please enter a valid phone number (max 20 characters).'}), 400
        
        # Basic info
        student.first_name = request.form.get('first_name', student.first_name).strip()
        student.last_name = request.form.get('last_name', student.last_name).strip()
        student.dob = request.form.get('dob', student.dob)
        raw_grade = request.form.get('grade_level', student.grade_level)
        parsed_grade = parse_grade_level_for_policy(raw_grade)
        if parsed_grade is not None:
            student.grade_level = parsed_grade
        gender = (request.form.get('gender') or getattr(student, 'gender', '') or '').strip()
        entrance_school_year = (request.form.get('entrance_date') or getattr(student, 'entrance_date', '') or '').strip()
        if not gender:
            return jsonify({'success': False, 'message': 'Gender is required.'}), 400
        if gender not in ['Male', 'Female', 'Non-binary', 'Prefer not to say', 'Other']:
            return jsonify({'success': False, 'message': 'Please select a valid gender option.'}), 400
        if not _is_valid_school_year_label(entrance_school_year):
            return jsonify({'success': False, 'message': 'Entrance school year is required and must use format YYYY-YYYY.'}), 400
        student.gender = gender
        student.entrance_date = entrance_school_year
        student.expected_grad_date = _calculate_expected_grad_date(student.grade_level, entrance_school_year)
        # State ID is disabled, so we don't update it
        
        # Parent 1 information
        student.parent1_first_name = request.form.get('parent1_first_name', student.parent1_first_name)
        student.parent1_last_name = request.form.get('parent1_last_name', student.parent1_last_name)
        student.parent1_email = request.form.get('parent1_email', student.parent1_email)
        student.parent1_phone = parent1_phone
        student.parent1_relationship = request.form.get('parent1_relationship', student.parent1_relationship)
        
        # Parent 2 information
        student.parent2_first_name = request.form.get('parent2_first_name', student.parent2_first_name)
        student.parent2_last_name = request.form.get('parent2_last_name', student.parent2_last_name)
        student.parent2_email = request.form.get('parent2_email', student.parent2_email)
        student.parent2_phone = parent2_phone
        student.parent2_relationship = request.form.get('parent2_relationship', student.parent2_relationship)
        
        # Emergency contact
        student.emergency_first_name = request.form.get('emergency_first_name', student.emergency_first_name)
        student.emergency_last_name = request.form.get('emergency_last_name', student.emergency_last_name)
        student.emergency_email = request.form.get('emergency_email', student.emergency_email)
        student.emergency_phone = emergency_phone
        student.emergency_relationship = request.form.get('emergency_relationship', student.emergency_relationship)
        
        # Address
        student.street = request.form.get('street', student.street)
        student.apt_unit = request.form.get('apt_unit', student.apt_unit)
        student.city = request.form.get('city', student.city)
        student.state = request.form.get('state', student.state)
        student.zip_code = request.form.get('zip_code', student.zip_code)
        
        # Update student's personal email
        student_email = request.form.get('email', student.email)
        if student_email:
            student.email = student_email
        
        # Update Google Workspace email in User account if student has one
        google_workspace_email = request.form.get('google_workspace_email', '').strip()
        if student.user:
            if google_workspace_email:
                # Check if this email is already used by another user
                existing_user = User.query.filter_by(google_workspace_email=google_workspace_email).first()
                if existing_user and existing_user.id != student.user.id:
                    return jsonify({'success': False, 'message': f'Google Workspace email {google_workspace_email} is already in use by another user.'}), 400
                
                student.user.google_workspace_email = google_workspace_email
            else:
                # Clear the Google Workspace email if field is empty
                student.user.google_workspace_email = None

        new_creds = None
        if not grade_may_have_login(student.grade_level):
            _strip_student_user_account(student)
        else:
            new_creds = _provision_student_login_if_needed(student)

        db.session.commit()
        # Google Directory sync immediately after commit (Save → Workspace updated in one step)
        if getattr(student, "user", None) and student.user.google_workspace_email:
            try:
                sync_single_user_to_google(student.user.id)
            except Exception as e:
                current_app.logger.warning(
                    "Google Directory sync after student edit failed for user %s: %s",
                    student.user.id,
                    e,
                )

        response = {"success": True, "message": "Student updated successfully."}
        if new_creds:
            promoted = (prev_grade is not None and not grade_may_have_login(prev_grade)) and grade_may_have_login(
                student.grade_level
            )
            try:
                from services.email_service import notify_school_admins_new_student_login

                notify_school_admins_new_student_login(
                    student_name=f"{student.first_name} {student.last_name}".strip(),
                    student_id=student.student_id or "",
                    username=new_creds["username"],
                    portal_password=new_creds["portal_password"],
                    school_email=new_creds.get("school_email"),
                    google_initial_password=new_creds.get("google_initial_password", DEFAULT_TEMP_PASSWORD),
                    context_note=(
                        "Grade was updated to 3rd+ and a new portal account was created."
                        if promoted
                        else "A portal account was created for this student (was missing)."
                    ),
                )
            except Exception as e:
                current_app.logger.warning("Admin notification email for new student login failed: %s", e)

            response["credential_modal"] = student_grade3_plus_modal_payload(
                first_name=student.first_name or "",
                last_name=student.last_name or "",
                student_id=student.student_id or "",
                username=new_creds["username"],
                portal_password=new_creds["portal_password"],
                school_email=new_creds.get("school_email"),
                google_initial_password=new_creds.get("google_initial_password", DEFAULT_TEMP_PASSWORD),
                google_user_created=None,
                google_warning=None,
            )
            response["credential_modal"].setdefault("notes", []).append(
                "After this save, the app attempted Google Directory sync. If Google sign-in still fails, "
                "open Google Admin or run your usual Directory sync job."
            )
            if promoted:
                response["message"] = (
                    "Student updated. A new login was created; School Administrators were emailed a copy."
                )
            else:
                response["message"] = "Student updated. A new login was created — see the credential summary."

        return jsonify(response)
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500




# ============================================================
# Route: /check-student-id/<student_id>
# Function: check_student_id
# ============================================================

@bp.route('/check-student-id/<student_id>')
@login_required
@management_required
def check_student_id(student_id):
    """Check if a student ID already exists"""
    existing_student = Student.query.filter_by(student_id=student_id).first()
    if existing_student:
        return jsonify({
            'exists': True,
            'student': {
                'id': existing_student.id,
                'first_name': existing_student.first_name,
                'last_name': existing_student.last_name,
                'grade_level': existing_student.grade_level,
                'has_user_account': existing_student.user is not None
            }
        })
    return jsonify({'exists': False})



# ============================================================
# Route: /remove-student/<int:student_id>', methods=['POST']
# Function: remove_student
# ============================================================

@bp.route('/remove-student/<int:student_id>', methods=['POST'])
@login_required
@management_required
def remove_student(student_id):
    """Soft-remove a student (preserve record like staff)."""
    try:
        student = Student.query.get_or_404(student_id)

        from datetime import datetime, timezone
        from models import Enrollment

        # Mark as deleted (record preserved)
        student.is_deleted = True
        student.deleted_at = datetime.now(timezone.utc)
        student.marked_for_removal = False
        student.status_updated_at = datetime.now(timezone.utc)

        # Deactivate enrollments so they no longer appear in active rosters
        for enr in Enrollment.query.filter_by(student_id=student_id).all():
            enr.is_active = False
            if hasattr(enr, 'dropped_at') and enr.dropped_at is None:
                enr.dropped_at = datetime.now(timezone.utc)

        # Remove associated login account (keep student profile data)
        _strip_student_user_account(student)

        db.session.commit()

        flash('Student removed (record preserved).', 'success')
        return redirect(url_for('management.students'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('remove_student failed student_id=%s', student_id)
        print(f"Error removing student: {e}")
        flash('Error removing student. Please try again.', 'error')
        return redirect(url_for('management.students'))



# ============================================================
# Route: /student-jobs
# Function: student_jobs
# ============================================================

def get_team_detailed_description(team):
    """Get detailed description for a team based on its name and type"""
    team_name = team.team_name.lower()
    # Safely get team_type - handle case where column doesn't exist in database yet
    team_type = getattr(team, 'team_type', None)
    team_type = team_type.lower() if team_type else 'cleaning'
    
    # Cleaning Team 1 - match "Team 1", "Cleaning Team 1", or any team with "1" and cleaning type
    if ('team 1' in team_name or 'cleaning team 1' in team_name) or (team_type == 'cleaning' and ('1' in team_name or team.team_name == 'Team 1')):
        return {
            'classrooms': {
                '1st-3rd Classroom': 'DO NOT TOUCH - This classroom is not cleaned by cleaning teams.',
                '3rd, 4th & 5th Classroom': '''• Sweep the entire floor, including under the table and in between the chairs.
• Wipe down all tables, no crumbs on chairs, no crumbs on tables
• Trash taken out, new trash liner''',
                '6th, 7th & 8th Classroom': '''• All desk in a straight line/row with no spaces starting from the wall with windows.
• Desks wiped down
• Floors swept
• No crumbs, no paper, clean and shiny
• Should be 5x5x5, 3 rows of 5s on Tuesdays and Thursdays
• Should be 4x6x5 on Mondays, Wednesdays and Fridays.
• Trash taken out, new trash liner''',
                'K Classroom': 'N/A'
            },
            'common_areas': {
                'Hallway': '• Swept & all trash liners replaced',
                'Females Restroom': '• Swept, Toilet Paper in each stall, soap near sink, Papertowls/napkins to dry hands.',
                'Mens Restroom': '• Swept, Toilet Paper in each stall, soap near sink, Papertowls/napkins to dry hands.'
            }
        }
    
    # Cleaning Team 2 - match "Team 2", "Cleaning Team 2", or any team with "2" and cleaning type
    elif ('team 2' in team_name or 'cleaning team 2' in team_name) or (team_type == 'cleaning' and ('2' in team_name or team.team_name == 'Team 2')):
        return {
            'classrooms': {
                '1st-3rd Classroom': 'DO NOT TOUCH - This classroom is not cleaned by cleaning teams.',
                '3rd, 4th & 5th Classroom': '''• Sweep the entire floor, including under the table and in between the chairs.
• Wipe down all tables, no crumbs on chairs, no crumbs on tables
• Trash taken out, new trash liner''',
                '6th, 7th & 8th Classroom': '''• All desk in a straight line/row with no spaces starting from the wall with windows.
• Desks wiped down
• Floors swept
• No crumbs, no paper, clean and shiny
• Should be 5x5x5, 3 rows of 5s on Tuesdays and Thursdays
• Should be 4x6x5 on Mondays, Wednesdays and Fridays.
• Trash taken out, new trash liner''',
                'K Classroom': 'N/A'
            },
            'common_areas': {
                'Hallway': '• Swept & all trash liners replaced',
                'Females Restroom': '• Swept, Toilet Paper in each stall, soap near sink, Papertowls/napkins to dry hands.',
                'Mens Restroom': '• Swept, Toilet Paper in each stall, soap near sink, Papertowls/napkins to dry hands.'
            }
        }
    
    # Computer Team
    elif 'computer team' in team_name and 'backup' not in team_name:
        return {
            'description': '''They are to make sure all computers are in the cabinet upstairs in the office:

• 28 Student computers marked with numbers 1-28

• They are to make sure all cords relating to each computer is in the office near the school. 28 Cords accounted for including 3-8 Extension cords

• So it will be 28+ extension cords

• Along with chromebooks, there should be 5+ unmarked chromebooks and charges so it would be 28+ computers and 28+ chargers with extension cords and chromebook chargers'''
        }
    
    # Backup Computer Team
    elif 'backup computer' in team_name or ('computer' in team_name and 'backup' in team_name):
        return {
            'description': '''They are to make sure all computers are in the cabinet upstairs in the office:

• 28 Student computers marked with numbers 1-28

• They are to make sure all cords relating to each computer is in the office near the school. 28 Cords accounted for including 3-8 Extension cords

• So it will be 28+ extension cords

• Along with chromebooks, there should be 5+ unmarked chromebooks and charges so it would be 28+ computers and 28+ chargers with extension cords and chromebook chargers'''
        }
    
    # Other teams - if it's a cleaning team but didn't match above, still return cleaning description
    elif team_type == 'cleaning':
        # Default cleaning team description if name doesn't match Team 1 or 2
        return {
            'classrooms': {
                '1st-3rd Classroom': 'DO NOT TOUCH - This classroom is not cleaned by cleaning teams.',
                '3rd, 4th & 5th Classroom': '''• Sweep the entire floor, including under the table and in between the chairs.
• Wipe down all tables, no crumbs on chairs, no crumbs on tables
• Trash taken out, new trash liner''',
                '6th, 7th & 8th Classroom': '''• All desk in a straight line/row with no spaces starting from the wall with windows.
• Desks wiped down
• Floors swept
• No crumbs, no paper, clean and shiny
• Should be 5x5x5, 3 rows of 5s on Tuesdays and Thursdays
• Should be 4x6x5 on Mondays, Wednesdays and Fridays.
• Trash taken out, new trash liner''',
                'K Classroom': 'N/A'
            },
            'common_areas': {
                'Hallway': '• Swept & all trash liners replaced',
                'Females Restroom': '• Swept, Toilet Paper in each stall, soap near sink, Papertowls/napkins to dry hands.',
                'Mens Restroom': '• Swept, Toilet Paper in each stall, soap near sink, Papertowls/napkins to dry hands.'
            }
        }
    
    # Other teams
    else:
        return {
            'description': team.team_description or 'No detailed description available.'
        }


@bp.route('/student-jobs')
@login_required
def student_jobs():
    """Student Jobs management page for cleaning crews, computer teams, and other teams"""
    try:
        # Get all teams (cleaning, computer, and other)
        # Check if team_type column exists first, then order accordingly
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('cleaning_team')]
        
        if 'team_type' in columns:
            # Column exists, order by team_type and name
            # Use CASE to prioritize: cleaning first, then computer, then others
            from sqlalchemy import case
            teams = CleaningTeam.query.filter_by(is_active=True).order_by(
                case(
                    (CleaningTeam.team_type == 'cleaning', 1),
                    (CleaningTeam.team_type == 'computer', 2),
                    else_=3
                ),
                CleaningTeam.team_name
            ).all()
        else:
            # Column doesn't exist yet, order by name but prioritize computer teams
            # Check if team name contains "computer" to identify computer teams
            teams = CleaningTeam.query.filter_by(is_active=True).all()
            # Sort manually: cleaning teams first, then computer teams, then others
            teams.sort(key=lambda t: (
                1 if 'computer' in t.team_name.lower() and 'backup' not in t.team_name.lower() else
                2 if 'backup' in t.team_name.lower() and 'computer' in t.team_name.lower() else
                0 if 'team 1' in t.team_name.lower() or t.team_name == 'Team 1' else
                0 if 'team 2' in t.team_name.lower() or t.team_name == 'Team 2' else
                3,
                t.team_name
            ))
        
        # Import datetime for checking reset time
        from datetime import datetime, timezone, timedelta
        from pytz import timezone as tz
        
        # Check if we need to reset points (every Monday at 12:00 AM EST)
        # Get current time in EST
        est = tz('US/Eastern')
        now_est = datetime.now(est)
        
        # Calculate the start of the current week (Monday at 12:00 AM)
        current_weekday = now_est.weekday()  # 0=Monday, 6=Sunday
        days_since_monday = current_weekday
        current_week_start = now_est.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
        
        # We'll check later if inspections are from before this week's Monday
        
        # Get team members for all teams
        team_data = {}
        for team in teams:
            # Get team members
            try:
                members = CleaningTeamMember.query.filter_by(
                    team_id=team.id,
                    is_active=True
                ).all()
            except Exception as e:
                # If query fails due to missing column, provide helpful error
                if 'assignment_description' in str(e):
                    print(f"Error: assignment_description column missing. Please run migration: python maintenance_scripts/add_assignment_description_to_cleaning_teams.py")
                    print(f"Error details: {e}")
                    # Return empty members list to allow page to load
                    members = []
                else:
                    raise
            
            # Get recent inspections for this team
            try:
                recent_inspections = CleaningInspection.query.filter_by(
                    team_id=team.id
                ).order_by(
                    CleaningInspection.inspection_date.desc()
                ).limit(5).all()
            except Exception as e:
                # If query fails due to missing column, provide helpful error
                if 'inspection_type' in str(e):
                    print(f"Error: inspection_type column missing. Please run migration: python maintenance_scripts/add_team_and_inspection_types.py")
                    print(f"Error details: {e}")
                    # Return empty inspections list to allow page to load
                    recent_inspections = []
                else:
                    raise
            
            # Get current score - use the most recent inspection's score
            # But check if we need to reset based on Monday 12:00 AM EST rule
            current_score = 100  # Default to 100
            
            if recent_inspections:
                # Get the most recent inspection
                latest_inspection = recent_inspections[0]
                
                # Convert date to datetime (inspection_date is a date object, not datetime)
                # Create a datetime at midnight EST for the inspection date
                inspection_date = latest_inspection.inspection_date
                if isinstance(inspection_date, datetime):
                    # Already a datetime
                    inspection_datetime = inspection_date
                    if inspection_datetime.tzinfo is None:
                        inspection_datetime = est.localize(inspection_datetime)
                    else:
                        inspection_datetime = inspection_datetime.astimezone(est)
                else:
                    # It's a date object, convert to datetime at midnight EST
                    inspection_datetime = est.localize(datetime.combine(inspection_date, datetime.min.time()))
                
                # Check if the inspection was before this week's Monday at 12:00 AM
                if inspection_datetime < current_week_start:
                    # Inspection is from last week or earlier - reset to 100
                    current_score = 100
                else:
                    # Inspection is from this week - use its score
                    current_score = latest_inspection.final_score
            else:
                # No inspections exist, show default 100
                current_score = 100
            
            # Build member list with student info
            member_list = []
            for member in members:
                if member.student:
                    # Safely get assignment_description
                    assignment_desc = ''
                    try:
                        assignment_desc = member.assignment_description or ''
                    except:
                        pass
                    
                    member_list.append({
                        'id': member.student.id,
                        'name': f"{member.student.first_name} {member.student.last_name}",
                        'role': member.role,
                        'assignment_description': assignment_desc,
                        'member_id': member.id
                    })
            
            # Get detailed description for the team
            detailed_description = get_team_detailed_description(team)
            
            team_data[team.id] = {
                'team': team,
                'members': member_list,
                'recent_inspections': recent_inspections,
                'current_score': current_score,
                'detailed_description': detailed_description
            }
        
        # Get all inspections from all teams for the global history table
        try:
            all_inspections = CleaningInspection.query.order_by(
                CleaningInspection.inspection_date.desc()
            ).limit(50).all()
        except Exception as e:
            # If query fails due to missing column, provide helpful error
            if 'inspection_type' in str(e):
                print(f"Error: inspection_type column missing. Please run migration: python maintenance_scripts/add_team_and_inspection_types.py")
                print(f"Error details: {e}")
                # Return empty inspections list to allow page to load
                all_inspections = []
            else:
                raise
        
        # Prepare inspection history data
        inspection_history = []
        for inspection in all_inspections:
            # Get team name
            team = CleaningTeam.query.get(inspection.team_id)
            team_name = team.team_name if team else f"Team {inspection.team_id}"
            
            inspection_history.append({
                'date': inspection.inspection_date,
                'team_name': team_name,
                'score': inspection.final_score,
                'major_deductions': inspection.major_deductions,
                'bonus_points': inspection.bonus_points,
                'status': 'Passed' if inspection.final_score >= 60 else 'Failed - Re-do Required',
                'inspector_name': inspection.inspector_name
            })
        
        return render_template('management/student_jobs.html', 
                             team_data=team_data, 
                             inspection_history=inspection_history)
    except Exception as e:
        print(f"Error loading student jobs: {e}")
        flash('Error loading student jobs data.', 'error')
        return render_template('management/student_jobs.html', team_data=[], inspection_history=[])




# ============================================================
# Route: /api/students
# Function: api_get_students
# ============================================================

@bp.route('/api/students')
@login_required
@management_required
def api_get_students():
    """API endpoint to get all students (Student Jobs / Add Members)."""
    try:
        # Get all students (no is_active filter since Student model doesn't have that column)
        students = Student.query.all()
        student_list = []
        for student in students:
            student_list.append({
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'student_id': student.student_id
            })
        
        return jsonify({
            'success': True,
            'students': student_list
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching students: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# Route: /api/team-members/<team_identifier>
# Function: api_get_team_members
# ============================================================

@bp.route('/api/team-members/<team_identifier>')
@login_required
@management_required
def api_get_team_members(team_identifier):
    """API endpoint to get team members by team ID or team name."""
    try:
        # Try to find team by ID first (if team_identifier is numeric)
        team = None
        if team_identifier.isdigit():
            team = CleaningTeam.query.filter_by(id=int(team_identifier), is_active=True).first()
        
        # If not found by ID, try to find by team name (e.g., "Team 1", "Team 2")
        if not team:
            # Handle both "Team 1" and "1" formats
            team_name = team_identifier
            if team_identifier.isdigit():
                team_name = f"Team {team_identifier}"
            team = CleaningTeam.query.filter_by(team_name=team_name, is_active=True).first()
        
        if not team:
            return jsonify({
                'success': False,
                'error': f'Team not found: {team_identifier}'
            }), 404
        
        # Get team members
        # Check if assignment_description column exists
        from sqlalchemy import inspect as sql_inspect
        inspector = sql_inspect(db.engine)
        member_columns = [col['name'] for col in inspector.get_columns('cleaning_team_member')]
        has_assignment_desc = 'assignment_description' in member_columns
        
        try:
            members = CleaningTeamMember.query.filter_by(
                team_id=team.id,
                is_active=True
            ).all()
        except Exception as e:
            # If query fails due to missing column, handle gracefully
            if 'assignment_description' in str(e):
                print(f"Warning: assignment_description column issue: {e}")
                # Return empty list - column should exist after migration
                return jsonify({
                    'success': False,
                    'error': 'Database schema needs migration. Please run: python maintenance_scripts/add_assignment_description_to_cleaning_teams.py'
                }), 500
            else:
                raise
        
        member_list = []
        for member in members:
            if member.student:
                assignment_desc = ''
                try:
                    assignment_desc = member.assignment_description or ''
                except:
                    pass
                
                member_list.append({
                    'id': member.student.id,
                    'name': f"{member.student.first_name} {member.student.last_name}",
                    'role': member.role or '',
                    'assignment_description': assignment_desc,
                    'member_id': member.id
                })
        
        return jsonify({
            'success': True,
            'members': member_list,
            'team': {
                'id': team.id,
                'name': team.team_name,
                'description': team.team_description
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching team members: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# Route: /api/team-members/<int:team_id>/add', methods=['POST']
# ============================================================
def _resolve_cleaning_team(team_id_or_num):
    """Resolve team by id or by number (1 -> Team 1 / Cleaning Team 1, 2 -> Team 2 / Cleaning Team 2)."""
    team = CleaningTeam.query.filter_by(id=team_id_or_num, is_active=True).first()
    if not team and team_id_or_num in (1, 2):
        for name in (f'Team {team_id_or_num}', f'Cleaning Team {team_id_or_num}', f'Cleanup Team {team_id_or_num}'):
            team = CleaningTeam.query.filter_by(team_name=name, is_active=True).first()
            if team:
                break
    return team


@bp.route('/api/team-members/<int:team_id>/add', methods=['POST'])
@login_required
@management_required
def api_team_members_add(team_id):
    """Add students to a cleaning team."""
    try:
        team = _resolve_cleaning_team(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team not found'}), 404
        data = request.get_json() or {}
        student_ids = data.get('student_ids') or []
        if not student_ids:
            return jsonify({'success': False, 'error': 'No student_ids provided'}), 400
        added = 0
        tid = team.id
        for sid in student_ids:
            existing = CleaningTeamMember.query.filter_by(
                team_id=tid, student_id=int(sid), is_active=True
            ).first()
            if not existing:
                member = CleaningTeamMember(
                    team_id=tid,
                    student_id=int(sid),
                    role='Team Member',
                    is_active=True
                )
                db.session.add(member)
                added += 1
        db.session.commit()
        return jsonify({'success': True, 'message': f'Added {added} member(s).'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding team members: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Route: /api/team-members/<int:team_id>/remove', methods=['POST']
# ============================================================
@bp.route('/api/team-members/<int:team_id>/remove', methods=['POST'])
@login_required
@management_required
def api_team_members_remove(team_id):
    """Remove students from a cleaning team (soft-deactivate)."""
    try:
        team = _resolve_cleaning_team(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team not found'}), 404
        data = request.get_json() or {}
        # Frontend may send student_ids or member ids; support both
        student_ids = data.get('student_ids') or []
        member_ids = data.get('member_ids') or []
        if not student_ids and not member_ids:
            return jsonify({'success': False, 'error': 'No student_ids or member_ids provided'}), 400
        removed = 0
        tid = team.id
        if student_ids:
            for sid in student_ids:
                m = CleaningTeamMember.query.filter_by(
                    team_id=tid, student_id=int(sid), is_active=True
                ).first()
                if m:
                    m.is_active = False
                    removed += 1
        for mid in member_ids:
            m = CleaningTeamMember.query.filter_by(id=int(mid), team_id=tid, is_active=True).first()
            if m:
                m.is_active = False
                removed += 1
        db.session.commit()
        return jsonify({'success': True, 'message': f'Removed {removed} member(s).'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing team members: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Route: /api/team-members/<int:member_id>/update', methods=['POST']
# ============================================================
@bp.route('/api/team-members/<int:member_id>/update', methods=['POST'])
@login_required
@management_required
def api_team_member_update(member_id):
    """Update a team member's role and assignment description."""
    try:
        member = CleaningTeamMember.query.filter_by(id=member_id, is_active=True).first()
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        data = request.get_json() or {}
        if 'role' in data:
            member.role = (data['role'] or '').strip() or member.role
        if 'assignment_description' in data:
            member.assignment_description = (data.get('assignment_description') or '').strip() or None
        db.session.commit()
        return jsonify({'success': True, 'message': 'Member updated.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating team member: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Route: /api/team-inspections/<team_identifier>
# ============================================================
@bp.route('/api/team-inspections/<team_identifier>')
@login_required
@management_required
def api_team_inspections(team_identifier):
    """Get inspection history for a team (by team number or id)."""
    try:
        team = None
        if team_identifier.isdigit():
            tid = int(team_identifier)
            team = CleaningTeam.query.filter_by(id=tid, is_active=True).first()
            if not team:
                team = CleaningTeam.query.filter_by(team_name=f'Team {tid}', is_active=True).first()
        if not team:
            team = CleaningTeam.query.filter_by(team_name=team_identifier, is_active=True).first()
        if not team:
            return jsonify({'success': False, 'error': 'Team not found'}), 404
        inspections = CleaningInspection.query.filter_by(team_id=team.id).order_by(
            CleaningInspection.inspection_date.desc()
        ).limit(50).all()
        out = []
        for i in inspections:
            out.append({
                'id': i.id,
                'date': i.inspection_date.isoformat() if hasattr(i.inspection_date, 'isoformat') else str(i.inspection_date),
                'score': i.final_score,
                'major_deductions': i.major_deductions,
                'bonus_points': i.bonus_points,
                'status': 'Passed' if i.final_score >= 60 else 'Failed - Re-do Required',
                'inspector_name': i.inspector_name,
                'inspector_notes': i.inspector_notes or ''
            })
        return jsonify({'success': True, 'inspections': out})
    except Exception as e:
        current_app.logger.error(f"Error fetching team inspections: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Route: /api/inspection/<int:inspection_id>
# ============================================================
@bp.route('/api/inspection/<int:inspection_id>')
@login_required
@management_required
def api_inspection_get(inspection_id):
    """Get a single inspection by id."""
    try:
        i = CleaningInspection.query.filter_by(id=inspection_id).first()
        if not i:
            return jsonify({'success': False, 'error': 'Inspection not found'}), 404
        team = CleaningTeam.query.get(i.team_id)
        team_name = team.team_name if team else f'Team {i.team_id}'
        return jsonify({
            'success': True,
            'inspection': {
                'id': i.id,
                'team_id': i.team_id,
                'team_name': team_name,
                'date': i.inspection_date.isoformat() if hasattr(i.inspection_date, 'isoformat') else str(i.inspection_date),
                'score': i.final_score,
                'major_deductions': i.major_deductions,
                'moderate_deductions': i.moderate_deductions,
                'minor_deductions': i.minor_deductions,
                'bonus_points': i.bonus_points,
                'inspector_name': i.inspector_name,
                'inspector_notes': i.inspector_notes or '',
                'bathroom_not_restocked': i.bathroom_not_restocked,
                'trash_can_left_full': i.trash_can_left_full,
                'floor_not_swept': i.floor_not_swept,
                'materials_left_out': i.materials_left_out,
                'tables_missed': i.tables_missed,
                'classroom_trash_full': i.classroom_trash_full,
                'bathroom_floor_poor': i.bathroom_floor_poor,
                'not_finished_on_time': i.not_finished_on_time,
                'small_debris_left': i.small_debris_left,
                'trash_spilled': i.trash_spilled,
                'dispensers_half_filled': i.dispensers_half_filled,
                'exceptional_finish': i.exceptional_finish,
                'speed_efficiency': i.speed_efficiency,
                'going_above_beyond': i.going_above_beyond,
                'teamwork_award': i.teamwork_award,
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching inspection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# Route: /api/save-inspection', methods=['POST'] (alias for student-jobs/inspection)
# ============================================================
@bp.route('/api/save-inspection', methods=['POST'])
@login_required
@management_required
def api_save_inspection():
    """Save cleaning inspection (same as student-jobs/inspection). Used by Student Jobs UI."""
    return submit_cleaning_inspection()


# ============================================================
# Route: /api/dynamic-teams (GET returns empty; POST returns 400 so UI does not break)
# ============================================================
@bp.route('/api/dynamic-teams', methods=['GET', 'POST'])
@login_required
@management_required
def api_dynamic_teams():
    """GET: list dynamic teams (empty). POST: not implemented."""
    if request.method == 'GET':
        return jsonify({'success': True, 'teams': []})
    return jsonify({'success': False, 'error': 'Creating new teams from this panel is not available. Use existing cleaning teams.'}), 400


# ============================================================
# Route: /student-jobs/inspection', methods=['POST']
# Function: submit_cleaning_inspection
# ============================================================

@bp.route('/student-jobs/inspection', methods=['POST'])
@login_required
@management_required
def submit_cleaning_inspection():
    """Submit a cleaning inspection result"""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'success': False, 'error': 'JSON body is required'}), 400
        
        # Create new inspection record
        team_id = data.get('team_id')
        inspection_date_raw = data.get('inspection_date')
        inspector_name = (data.get('inspector_name') or '').strip()
        if not team_id or not inspection_date_raw or not inspector_name:
            return jsonify({'success': False, 'error': 'team_id, inspection_date, and inspector_name are required'}), 400

        inspection = CleaningInspection(
            team_id=team_id,
            inspection_date=datetime.strptime(str(inspection_date_raw), '%Y-%m-%d').date(),
            inspector_name=inspector_name,
            inspector_notes=data.get('inspector_notes', ''),
            
            # Deductions
            bathroom_not_restocked=data.get('bathroom_not_restocked', False),
            trash_can_left_full=data.get('trash_can_left_full', False),
            floor_not_swept=data.get('floor_not_swept', False),
            materials_left_out=data.get('materials_left_out', False),
            tables_missed=data.get('tables_missed', False),
            classroom_trash_full=data.get('classroom_trash_full', False),
            bathroom_floor_poor=data.get('bathroom_floor_poor', False),
            not_finished_on_time=data.get('not_finished_on_time', False),
            small_debris_left=data.get('small_debris_left', False),
            trash_spilled=data.get('trash_spilled', False),
            dispensers_half_filled=data.get('dispensers_half_filled', False),
            
            # Bonuses
            exceptional_finish=data.get('exceptional_finish', False),
            speed_efficiency=data.get('speed_efficiency', False),
            going_above_beyond=data.get('going_above_beyond', False),
            teamwork_award=data.get('teamwork_award', False),
            
            # Calculate scores
            major_deductions=data.get('major_deductions', 0),
            moderate_deductions=data.get('moderate_deductions', 0),
            minor_deductions=data.get('minor_deductions', 0),
            bonus_points=data.get('bonus_points', 0),
            final_score=data.get('final_score', 100)
        )
        
        db.session.add(inspection)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inspection submitted successfully',
            'inspection_id': inspection.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting inspection: {e}")
        return jsonify({
            'success': False,
            'message': 'Error submitting inspection'
        }), 500



# ============================================================
# Route: /class/<int:class_id>/groups/create', methods=['GET', 'POST']
# Function: admin_create_student_group
# ============================================================

@bp.route('/class/<int:class_id>/groups/create', methods=['GET', 'POST'])
@login_required
@management_required
def admin_create_student_group(class_id):
    """Create a new student group for a class (Administrator access)."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description', '')
            max_students = request.form.get('max_members', type=int)  # Form field is max_members but model field is max_students
            
            if not name:
                flash('Group name is required.', 'error')
                return redirect(url_for('management.admin_class_groups', class_id=class_id))
            
            # Create the group
            group = StudentGroup(
                name=name,
                description=description,
                class_id=class_id,
                max_students=max_students,  # Use max_students instead of max_members
                created_by=current_user.teacher_staff_id,  # Add required created_by field
                is_active=True
            )
            
            db.session.add(group)
            db.session.commit()
            
            flash('Group created successfully!', 'success')
            return redirect(url_for('management.admin_class_groups', class_id=class_id))
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        enrolled_students = [enrollment.student for enrollment in enrollments]
        
        return render_template('teachers/teacher_create_group.html',
                             class_obj=class_obj,
                             enrolled_students=enrolled_students,
                             role_prefix=True)
    
    except Exception as e:
        print(f"Error creating group: {e}")
        flash('Error creating group. Please try again.', 'error')
        return redirect(url_for('management.admin_class_groups', class_id=class_id))



# ============================================================
# Route: /student/<int:student_id>/details
# Function: view_student_details
# ============================================================

@bp.route('/student/<int:student_id>/details')
@login_required
@management_required
def view_student_details(student_id):
    """View detailed student information including academic analysis."""
    from gpa_scheduler import calculate_student_gpa
    from copy import copy
    import json
    
    student = Student.query.get_or_404(student_id)
    
    # Get the user associated with this student (if any)
    user = User.query.filter_by(student_id=student_id).first()
    
    # --- GPA IMPACT ANALYSIS ---
    current_gpa = None
    hypothetical_gpa = None
    at_risk_grades_list = []
    all_missing_assignments = []
    class_gpa_breakdown = []

    # Get all non-voided grades for the student
    all_grades = Grade.query.filter_by(student_id=student.id).filter(Grade.is_voided == False).all()
    
    # Get all classes this student is enrolled in
    enrollments = Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
    student_classes = {enrollment.class_id: enrollment.class_info for enrollment in enrollments if enrollment.class_info}
    
    # Separate grades by class and find missing/at-risk assignments
    grades_by_class = {}
    for g in all_grades:
        class_id = g.assignment.class_id
        if class_id not in grades_by_class:
            grades_by_class[class_id] = []
        grades_by_class[class_id].append(g)
        
        try:
            grade_data = json.loads(g.grade_data)
            score = grade_data.get('score')
            g.display_score = score
            
            # Check if assignment is past due
            if g.assignment.due_date < datetime.utcnow():
                if score is None:
                    # Missing assignment
                    all_missing_assignments.append({
                        'grade': g,
                        'assignment': g.assignment,
                        'class_name': g.assignment.class_info.name,
                        'due_date': g.assignment.due_date,
                        'status': 'missing'
                    })
                elif score <= 69:
                    # Failing assignment
                    at_risk_grades_list.append(g)
                    all_missing_assignments.append({
                        'grade': g,
                        'assignment': g.assignment,
                        'class_name': g.assignment.class_info.name,
                        'due_date': g.assignment.due_date,
                        'status': 'failing',
                        'score': score
                    })
        except (json.JSONDecodeError, TypeError):
            continue

    # Calculate Current Overall GPA
    current_gpa = calculate_student_gpa(all_grades) 

    # Calculate GPA per class
    for class_id, class_grades in grades_by_class.items():
        if class_id in student_classes:
            class_obj = student_classes[class_id]
            class_current_gpa = calculate_student_gpa(class_grades)
            
            # Calculate hypothetical GPA for this class (fixing at-risk assignments)
            class_at_risk = [g for g in class_grades if g in at_risk_grades_list]
            class_hypothetical_grades = []
            for g in class_grades:
                if g in class_at_risk:
                    hypothetical_grade = copy(g)
                    try:
                        grade_data = json.loads(g.grade_data)
                        grade_data['score'] = 70
                        hypothetical_grade.grade_data = json.dumps(grade_data)
                        class_hypothetical_grades.append(hypothetical_grade)
                    except (json.JSONDecodeError, TypeError):
                        class_hypothetical_grades.append(g)
                else:
                    class_hypothetical_grades.append(g)
            
            class_hypothetical_gpa = calculate_student_gpa(class_hypothetical_grades)
            
            # Get assignments impacting this class
            class_impact_assignments = [
                item for item in all_missing_assignments 
                if item['assignment'].class_id == class_id
            ]
            
            class_gpa_breakdown.append({
                'class_name': class_obj.name,
                'class_id': class_id,
                'current_gpa': class_current_gpa,
                'hypothetical_gpa': class_hypothetical_gpa,
                'impact_assignments': class_impact_assignments,
                'total_assignments': len(class_grades)
            })
    
    # Calculate Hypothetical Overall GPA
    hypothetical_grades = []
    for g in all_grades:
        if g in at_risk_grades_list:
            hypothetical_grade = copy(g)
            try:
                grade_data = json.loads(g.grade_data)
                grade_data['score'] = 70
                hypothetical_grade.grade_data = json.dumps(grade_data)
                hypothetical_grades.append(hypothetical_grade)
            except (json.JSONDecodeError, TypeError):
                hypothetical_grades.append(g)
        else:
            hypothetical_grades.append(g)
    
    hypothetical_gpa = calculate_student_gpa(hypothetical_grades)
    # --- END GPA ANALYSIS ---
    
    return render_template('management/user_details.html', 
                         user=user,
                         student=student,
                         current_gpa=current_gpa,
                         hypothetical_gpa=hypothetical_gpa,
                         at_risk_grades_list=at_risk_grades_list,
                         all_missing_assignments=all_missing_assignments,
                         class_gpa_breakdown=class_gpa_breakdown)



# ============================================================
# Route: /student/<int:student_id>/details/data
# Function: view_student_details_data
# ============================================================

@bp.route('/student/<int:student_id>/details/data')
@login_required
@management_required
def view_student_details_data(student_id):
    """API endpoint to get detailed student information as JSON for academic alerts."""
    from flask import jsonify
    from gpa_scheduler import calculate_student_gpa
    from copy import copy
    import json
    
    try:
        from utils.at_risk_alerts import _percentage_from_grade_data
        from utils.academic_concern_submission import academic_concern_effective_submitted

        student = Student.query.get_or_404(student_id)
        
        # --- GPA IMPACT ANALYSIS ---
        current_gpa = None
        hypothetical_gpa = None
        at_risk_grades_list = []
        all_missing_assignments = []
        class_gpa_breakdown = {}

        # Get all non-voided grades for the student
        all_grades = Grade.query.filter_by(student_id=student.id).filter(
            db.or_(Grade.is_voided.is_(False), Grade.is_voided.is_(None))
        ).all()
        
        # Get all classes this student is enrolled in
        enrollments = Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
        student_classes = {enrollment.class_id: enrollment.class_info for enrollment in enrollments if enrollment.class_info}
        student_class_ids = list(student_classes.keys())
        
        # Separate grades by class and find missing/at-risk assignments
        grades_by_class = {}
        missing_assignments_by_class = {}
        
        for g in all_grades:
            try:
                # Ensure assignment relationship is loaded
                if not g.assignment:
                    continue
                
                if not g.assignment.class_info:
                    continue
                
                class_id = g.assignment.class_id
                if class_id not in grades_by_class:
                    grades_by_class[class_id] = []
                grades_by_class[class_id].append(g)
                
                # Parse grade data and get percentage using assignment total_points
                total_pts = getattr(g.assignment, 'total_points', None) or 100.0
                if not g.grade_data:
                    percentage = None
                else:
                    try:
                        grade_data = json.loads(g.grade_data)
                        percentage, _ = _percentage_from_grade_data(grade_data, total_pts)
                    except (json.JSONDecodeError, TypeError):
                        percentage = None
                
                g.display_score = percentage
                
                # Check if assignment is past due or failing
                is_overdue = g.assignment.due_date and g.assignment.due_date < datetime.utcnow()
                
                # Determine if this is truly at-risk (missing OR failing)
                is_at_risk = False
                status = None
                
                if percentage is None:
                    if is_overdue:
                        is_at_risk = True
                        status = 'missing'
                elif percentage <= 69:
                    is_at_risk = True
                    status = 'failing'
                    at_risk_grades_list.append(g)
                
                if is_at_risk:
                    class_name = g.assignment.class_info.name
                    # Detect "awaiting grade": exclude from display per user request
                    awaiting_grade = False
                    if status == 'failing' and percentage is not None and percentage == 0:
                        sub = Submission.query.filter_by(
                            student_id=student.id,
                            assignment_id=g.assignment_id
                        ).first()
                        if sub and sub.submission_type in ('online', 'in_person'):
                            awaiting_grade = True
                    
                    # Do not include assignments awaiting a grade
                    if not awaiting_grade:
                        sub = Submission.query.filter_by(
                            student_id=student.id,
                            assignment_id=g.assignment_id
                        ).first()
                        submitted = academic_concern_effective_submitted(
                            student.id, g.assignment_id, g, sub
                        )
                        if class_name not in missing_assignments_by_class:
                            missing_assignments_by_class[class_name] = []
                        missing_assignments_by_class[class_name].append({
                            'title': g.assignment.title,
                            'due_date': g.assignment.due_date.strftime('%Y-%m-%d') if g.assignment.due_date else 'No due date',
                            'status': status,
                            'score': round(percentage, 1) if percentage is not None else 'N/A',
                            'assignment_type': g.assignment.assignment_type or 'pdf',
                            'submission_status': 'submitted' if submitted else 'not_submitted'
                        })
                        
            except Exception as e:
                continue

        # Add group assignments for this student's classes
        if student_class_ids:
            group_assignments = GroupAssignment.query.filter(
                GroupAssignment.class_id.in_(student_class_ids),
                GroupAssignment.status != 'Voided',
                GroupAssignment.due_date.isnot(None)
            ).all()
            for ga in group_assignments:
                try:
                    # Check if student is in a group that has this assignment
                    membership = StudentGroupMember.query.join(StudentGroup).filter(
                        StudentGroupMember.student_id == student.id,
                        StudentGroup.class_id == ga.class_id
                    ).first()
                    if not membership:
                        continue
                    group_id = membership.group_id
                    selected_ids = ga.selected_group_ids
                    if selected_ids:
                        try:
                            ids = json.loads(selected_ids) if isinstance(selected_ids, str) else selected_ids
                            if group_id not in ids:
                                continue
                        except (TypeError, ValueError):
                            pass
                    class_name = ga.class_info.name if ga.class_info else 'Unknown Class'
                    if class_name not in missing_assignments_by_class:
                        missing_assignments_by_class[class_name] = []
                    grade = GroupGrade.query.filter_by(
                        group_assignment_id=ga.id,
                        student_id=student.id
                    ).first()
                    total_pts = getattr(ga, 'total_points', None) or 100.0
                    is_overdue = ga.due_date and ga.due_date < datetime.utcnow()
                    awaiting_grade = False
                    if grade and grade.grade_data:
                        try:
                            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                            percentage, _ = _percentage_from_grade_data(grade_data, total_pts)
                            if percentage is not None and percentage <= 69:
                                sub = GroupSubmission.query.filter_by(
                                    group_assignment_id=ga.id,
                                    group_id=group_id
                                ).first()
                                if sub and (sub.attachment_file_path or sub.attachment_filename) and percentage == 0:
                                    awaiting_grade = True
                                if not awaiting_grade:
                                    sub_type = grade_data.get('submission_type', '')
                                    grp_submitted = sub_type in ('online', 'in_person')
                                    missing_assignments_by_class[class_name].append({
                                        'title': ga.title,
                                        'due_date': ga.due_date.strftime('%Y-%m-%d') if ga.due_date else 'No due date',
                                        'status': 'failing',
                                        'score': round(percentage, 1),
                                        'assignment_type': f'group_{ga.assignment_type or "pdf"}',
                                        'submission_status': 'submitted' if grp_submitted else 'not_submitted'
                                    })
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif is_overdue and not grade:
                        grp_sub = GroupSubmission.query.filter_by(
                            group_assignment_id=ga.id,
                            group_id=group_id
                        ).first()
                        grp_submitted = grp_sub and (grp_sub.attachment_file_path or grp_sub.attachment_filename)
                        missing_assignments_by_class[class_name].append({
                            'title': ga.title,
                            'due_date': ga.due_date.strftime('%Y-%m-%d') if ga.due_date else 'No due date',
                            'status': 'missing',
                            'score': 'N/A',
                            'assignment_type': f'group_{ga.assignment_type or "pdf"}',
                            'submission_status': 'submitted' if grp_submitted else 'not_submitted'
                        })
                except Exception:
                    continue

        # Calculate Current Overall GPA
        if all_grades:
            current_gpa = calculate_student_gpa(all_grades)

        # Calculate Hypothetical Overall GPA
        hypothetical_grades = []
        for g in all_grades:
            if g in at_risk_grades_list:
                hypothetical_grade = copy(g)
                try:
                    grade_data = json.loads(g.grade_data)
                    grade_data['score'] = 70
                    hypothetical_grade.grade_data = json.dumps(grade_data)
                    hypothetical_grades.append(hypothetical_grade)
                except (json.JSONDecodeError, TypeError):
                    hypothetical_grades.append(g)
            else:
                hypothetical_grades.append(g)
        
        if hypothetical_grades:
            hypothetical_gpa = calculate_student_gpa(hypothetical_grades)

        # Calculate GPA per class
        class_gpa_data = {}
        for class_id, class_grades in grades_by_class.items():
            if class_id in student_classes:
                class_obj = student_classes[class_id]
                class_name = class_obj.name
                
                class_current_gpa = calculate_student_gpa(class_grades) if class_grades else None
                
                # Calculate hypothetical GPA for this class (fixing at-risk assignments)
                class_at_risk = [g for g in class_grades if g in at_risk_grades_list]
                class_hypothetical_grades = []
                for g in class_grades:
                    if g in class_at_risk:
                        hypothetical_grade = copy(g)
                        try:
                            grade_data = json.loads(g.grade_data)
                            grade_data['score'] = 70
                            hypothetical_grade.grade_data = json.dumps(grade_data)
                            class_hypothetical_grades.append(hypothetical_grade)
                        except (json.JSONDecodeError, TypeError):
                            class_hypothetical_grades.append(g)
                    else:
                        class_hypothetical_grades.append(g)
                
                class_hypothetical_gpa = calculate_student_gpa(class_hypothetical_grades) if class_hypothetical_grades else None
                
                class_gpa_data[class_name] = {
                    'current': class_current_gpa,
                    'hypothetical': class_hypothetical_gpa
                }

        # Ensure we always return valid data
        response_data = {
            'success': True,
            'student': {
                'name': f"{student.first_name} {student.last_name}",
                'student_id': student.id,
                'current_gpa': current_gpa if current_gpa is not None else 0.0,
                'hypothetical_gpa': hypothetical_gpa if hypothetical_gpa is not None else 0.0,
                'missing_assignments': missing_assignments_by_class if missing_assignments_by_class else {},
                'class_gpa': class_gpa_data if class_gpa_data else {}
            }
        }
        
        print(f"Returning student details for {student.first_name} {student.last_name}")
        print(f"Missing assignments: {len(missing_assignments_by_class)} classes with issues")
        print(f"Current GPA: {current_gpa}, Hypothetical GPA: {hypothetical_gpa}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in view_student_details_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'details': traceback.format_exc()
        }), 500

