"""
Students routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import (
    db, Student, User, Enrollment, Class, Grade, Assignment, ReportCard, SchoolYear,
    Attendance, SchoolDayAttendance, StudentGoal, StudentGroupMember, Submission,
    GroupSubmission, GroupGrade, AssignmentExtension, MessageGroupMember, Notification,
    QuizAnswer, QuizProgress, DiscussionPost, GroupQuizAnswer, CleaningTeamMember,
    CleaningTeam, CleaningInspection
)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, text
from datetime import datetime, timedelta, date
import os
import json
import csv
import io
import uuid
import random
from .utils import allowed_file

bp = Blueprint('students', __name__)


# ============================================================
# Route: /add-student', methods=['GET', 'POST']
# Function: add_student
# ============================================================

@bp.route('/add-student', methods=['GET', 'POST'])
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
            
            # Check if student ID already exists
            existing_student = Student.query.filter_by(student_id=student.student_id).first()
            if existing_student:
                flash(f'A student with ID {student.student_id} already exists: {existing_student.first_name} {existing_student.last_name}. This student may have already been added. Please check the student list or contact support if you believe this is an error.', 'danger')
                return redirect(request.url)
            
            db.session.add(student)
            db.session.flush()  # Get the student ID
            
            # Auto-generate Google Workspace email for student
            # Format: firstname.lastname@clarascienceacademy.org
            generated_workspace_email = None
            if first_name and last_name:
                first = first_name.lower().replace(' ', '').replace('-', '')
                last = last_name.lower().replace(' ', '').replace('-', '')
                generated_workspace_email = f"{first}.{last}@clarascienceacademy.org"
                
                # Check if this email is already in use
                existing_user = User.query.filter_by(google_workspace_email=generated_workspace_email).first()
                if existing_user:
                    # Add a number suffix if duplicate
                    counter = 2
                    while existing_user:
                        generated_workspace_email = f"{first}.{last}{counter}@clarascienceacademy.org"
                        existing_user = User.query.filter_by(google_workspace_email=generated_workspace_email).first()
                        counter += 1
            
            # If no email was provided in the form, use the generated workspace email
            if not email and generated_workspace_email:
                student.email = generated_workspace_email
            
            # Create user account
            user = User()
            user.username = username
            user.password_hash = generate_password_hash(password)
            user.role = 'Student'
            user.student_id = student.id
            user.email = student.email  # Set personal email from student record
            user.google_workspace_email = generated_workspace_email  # Set generated workspace email
            user.is_temporary_password = True  # New users must change password
            user.password_changed_at = None
            
            db.session.add(user)
            db.session.commit()
            
            # Show success message with credentials
            success_msg = f'Student added successfully! Username: {username}, Password: {password}.'
            if generated_workspace_email:
                success_msg += f' Google Workspace Email: {generated_workspace_email}.'
            success_msg += ' Student will be required to change password on first login.'
            flash(success_msg, 'success')
            return redirect(url_for('management.students'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('students/add_student.html')



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
        from datetime import datetime
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
        
        # Calculate expected graduation date
        # Assuming graduation is in June of the year they reach 12th grade
        expected_grad_date = None
        if student.grade_level:
            years_to_graduation = 12 - student.grade_level
            if years_to_graduation >= 0:
                current_year = datetime.now().year
                grad_year = current_year + years_to_graduation
                expected_grad_date = f"06/{grad_year}"
        
        # Format student ID
        student_id_formatted = student.student_id if student.student_id else 'N/A'
        if hasattr(student, 'student_id_formatted'):
            student_id_formatted = student.student_id_formatted
        
        # Get SSN/State ID (might not exist in model)
        ssn = getattr(student, 'ssn', None) or getattr(student, 'state_student_id', None) or 'N/A'
        
        # Get gender (might not exist in model)
        gender = getattr(student, 'gender', None) or 'N/A'
        
        # Format DOB
        dob = student.dob if student.dob else 'N/A'
        
        # Get entrance date (might not exist in model)
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
            'expected_grad_date': expected_grad_date
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
                    added_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
                continue
        
        # Commit all changes
        try:
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
                         pre_selected_student=student_id)



# ============================================================
# Route: /void-assignment/<int:assignment_id>', methods=['POST']
# Function: void_assignment_for_students
# ============================================================

@bp.route('/void-assignment/<int:assignment_id>', methods=['POST'])
@login_required
@management_required
def void_assignment_for_students(assignment_id):
    """Void an assignment for all students or specific students."""
    try:
        assignment_type = request.form.get('assignment_type', 'individual')
        student_ids = request.form.getlist('student_ids')
        reason = request.form.get('reason', 'Voided by administrator')
        void_all = request.form.get('void_all', 'false').lower() == 'true'
        
        voided_count = 0
        
        if assignment_type == 'group':
            group_assignment = GroupAssignment.query.get_or_404(assignment_id)
            
            if void_all or not student_ids:
                # Void for all students in groups
                from models import StudentGroupMember, StudentGroup
                import json
                
                # Get all groups in this class
                groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id).all()
                
                for group in groups:
                    # Get all members of this group
                    members = StudentGroupMember.query.filter_by(student_group_id=group.id).all()
                    
                    for member in members:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_id=member.student_id
                        ).first()
                        
                        if group_grade:
                            # Grade exists - void it if not already voided
                            if not group_grade.is_voided:
                                # Note: GroupGrade doesn't have GradeHistory, so we'll just void it
                                # The unvoid will restore from the voided state
                                group_grade.is_voided = True
                                group_grade.voided_by = current_user.id
                                group_grade.voided_at = datetime.utcnow()
                                group_grade.voided_reason = reason
                                # Nullify grade data if it exists
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
                        else:
                            # No grade exists - create a placeholder voided grade
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
                
                message = f'Voided group assignment "{group_assignment.title}" for all students ({voided_count} grades)'
            else:
                # Void for specific students
                from models import StudentGroupMember
                import json
                
                for student_id in student_ids:
                    # Find student's group for this assignment
                    member = StudentGroupMember.query.filter_by(student_id=int(student_id)).first()
                    
                    if member:
                        group_grade = GroupGrade.query.filter_by(
                            group_assignment_id=assignment_id,
                            student_id=int(student_id)
                        ).first()
                        
                        if group_grade:
                            # Grade exists - void it if not already voided
                            if not group_grade.is_voided:
                                # Note: GroupGrade doesn't have GradeHistory, so we'll just void it
                                # The unvoid will restore from the voided state
                                group_grade.is_voided = True
                                group_grade.voided_by = current_user.id
                                group_grade.voided_at = datetime.utcnow()
                                group_grade.voided_reason = reason
                                # Nullify grade data if it exists
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
                        else:
                            # No grade exists - create a placeholder voided grade
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
                
                message = f'Voided group assignment "{group_assignment.title}" for {voided_count} student(s)'
        else:
            assignment = Assignment.query.get_or_404(assignment_id)
            
            if void_all or not student_ids:
                # Void for all students - need to get all enrolled students
                from models import Enrollment
                import json
                
                enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
                
                for enrollment in enrollments:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=enrollment.student_id
                    ).first()
                    
                    if grade:
                        # Grade exists - void it if not already voided
                        if not grade.is_voided:
                            # Save current grade data to history before voiding
                            from models import GradeHistory
                            original_grade_data = grade.grade_data
                            
                            if original_grade_data:
                                try:
                                    # Create history entry to preserve original grade data
                                    history_entry = GradeHistory(
                                        grade_id=grade.id,
                                        student_id=grade.student_id,
                                        assignment_id=assignment_id,
                                        previous_grade_data=original_grade_data,  # Save original
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
                            # Nullify grade data if it exists
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
                    else:
                        # No grade exists - create a placeholder voided grade
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
                
                message = f'Voided assignment "{assignment.title}" for all students ({voided_count} grades)'
            else:
                # Void for specific students
                import json
                
                for student_id in student_ids:
                    grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=int(student_id)
                    ).first()
                    
                    if grade:
                        # Grade exists - void it if not already voided
                        if not grade.is_voided:
                            # Save current grade data to history before voiding
                            from models import GradeHistory
                            original_grade_data = grade.grade_data
                            
                            if original_grade_data:
                                try:
                                    # Create history entry to preserve original grade data
                                    history_entry = GradeHistory(
                                        grade_id=grade.id,
                                        student_id=grade.student_id,
                                        assignment_id=assignment_id,
                                        previous_grade_data=original_grade_data,  # Save original
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
                            # Nullify grade data if it exists
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
                    else:
                        # No grade exists - create a placeholder voided grade
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
                
                message = f'Voided assignment "{assignment.title}" for {voided_count} student(s)'
        
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
            return jsonify({'success': True, 'message': message, 'voided_count': voided_count})
        else:
            # Regular form submission - redirect with flash message
            flash(message, 'success')
            return redirect(url_for('management.assignments_and_grades'))
        
    except Exception as e:
        db.session.rollback()
        error_message = f'Error voiding assignment: {str(e)}'
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  'application/json' in request.headers.get('Accept', '')
        
        if is_ajax:
            return jsonify({'success': False, 'message': error_message}), 500
        else:
            flash(error_message, 'danger')
            return redirect(url_for('management.assignments_and_grades'))




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
@management_required
def edit_student(student_id):
    """Edit student information via AJAX modal"""
    student = Student.query.get_or_404(student_id)
    try:
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
        student.grade_level = request.form.get('grade_level', student.grade_level)
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
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Student updated successfully.'})
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
    """Remove a student and all associated data"""
    try:
        student = Student.query.get_or_404(student_id)
        
        # Delete all related records first to avoid foreign key constraints
        from models import (
            Attendance, SchoolDayAttendance, StudentGoal, StudentGroupMember, Grade, 
            Submission, GroupSubmission, GroupGrade, AssignmentExtension, Enrollment, 
            MessageGroupMember, Notification, QuizAnswer, QuizProgress, DiscussionPost,
            ReportCard, GroupQuizAnswer, CleaningTeamMember
        )
        
        # Delete enrollment records first (these reference the student)
        Enrollment.query.filter_by(student_id=student_id).delete()
        
        # Delete attendance records (both class and school day attendance)
        Attendance.query.filter_by(student_id=student_id).delete()
        SchoolDayAttendance.query.filter_by(student_id=student_id).delete()
        
        # Delete student goals
        StudentGoal.query.filter_by(student_id=student_id).delete()
        
        # Delete group memberships
        StudentGroupMember.query.filter_by(student_id=student_id).delete()
        
        # Delete grades
        Grade.query.filter_by(student_id=student_id).delete()
        
        # Delete assignment submissions
        Submission.query.filter_by(student_id=student_id).delete()
        
        # Delete group submissions
        GroupSubmission.query.filter_by(submitted_by=student_id).delete()
        
        # Delete group grades
        GroupGrade.query.filter_by(student_id=student_id).delete()
        
        # Delete assignment extensions
        AssignmentExtension.query.filter_by(student_id=student_id).delete()
        
        # Delete quiz answers and progress
        QuizAnswer.query.filter_by(student_id=student_id).delete()
        QuizProgress.query.filter_by(student_id=student_id).delete()
        
        # Delete discussion posts
        DiscussionPost.query.filter_by(student_id=student_id).delete()
        
        # Delete report cards
        ReportCard.query.filter_by(student_id=student_id).delete()
        
        # Delete group quiz answers
        GroupQuizAnswer.query.filter_by(student_id=student_id).delete()
        
        # Delete cleaning team memberships
        CleaningTeamMember.query.filter_by(student_id=student_id).delete()
        
        # Delete associated user account if it exists
        if student.user:
            # Delete notifications before deleting the user
            Notification.query.filter_by(user_id=student.user.id).delete()
            # Delete message group memberships before deleting the user
            MessageGroupMember.query.filter_by(user_id=student.user.id).delete()
            db.session.delete(student.user)
        
        # Finally, delete the student
        db.session.delete(student)
        db.session.commit()
        
        flash('Student removed successfully.', 'success')
        return redirect(url_for('management.students'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error removing student: {e}")
        flash('Error removing student. Please try again.', 'error')
        return redirect(url_for('management.students'))



# ============================================================
# Route: /student-jobs
# Function: student_jobs
# ============================================================

@bp.route('/student-jobs')
@login_required
@management_required
def student_jobs():
    """Student Jobs management page for cleaning crews"""
    try:
        # Get all cleaning teams
        teams = CleaningTeam.query.filter_by(is_active=True).all()
        
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
            members = CleaningTeamMember.query.filter_by(
                team_id=team.id,
                is_active=True
            ).all()
            
            # Get recent inspections for this team
            recent_inspections = CleaningInspection.query.filter_by(
                team_id=team.id
            ).order_by(
                CleaningInspection.inspection_date.desc()
            ).limit(5).all()
            
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
            
            team_data[team.id] = {
                'team': team,
                'members': member_list,
                'recent_inspections': recent_inspections,
                'current_score': current_score
            }
        
        # Get all inspections from all teams for the global history table
        all_inspections = CleaningInspection.query.order_by(
            CleaningInspection.inspection_date.desc()
        ).limit(50).all()
        
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
    """API endpoint to get all students for dynamic team creation"""
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
# Route: /student-jobs/inspection', methods=['POST']
# Function: submit_cleaning_inspection
# ============================================================

@bp.route('/student-jobs/inspection', methods=['POST'])
@login_required
@management_required
def submit_cleaning_inspection():
    """Submit a cleaning inspection result"""
    try:
        data = request.get_json()
        
        # Create new inspection record
        inspection = CleaningInspection(
            team_id=data['team_id'],
            inspection_date=datetime.strptime(data['inspection_date'], '%Y-%m-%d').date(),
            inspector_name=data['inspector_name'],
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
        
        # Separate grades by class and find missing/at-risk assignments
        grades_by_class = {}
        missing_assignments_by_class = {}
        
        for g in all_grades:
            try:
                # Ensure assignment relationship is loaded
                if not g.assignment:
                    print(f"Grade {g.id} has no assignment, skipping")
                    continue
                
                if not g.assignment.class_info:
                    print(f"Assignment {g.assignment_id} has no class info, skipping")
                    continue
                
                class_id = g.assignment.class_id
                if class_id not in grades_by_class:
                    grades_by_class[class_id] = []
                grades_by_class[class_id].append(g)
                
                # Parse grade data
                if not g.grade_data:
                    print(f"Grade {g.id} has no grade_data, treating as missing")
                    score = None
                else:
                    try:
                        grade_data = json.loads(g.grade_data)
                        score = grade_data.get('score')
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Error parsing grade_data for grade {g.id}: {e}")
                        score = None
                
                g.display_score = score
                
                # Check if assignment is past due or failing
                is_overdue = g.assignment.due_date and g.assignment.due_date < datetime.utcnow()
                
                # Determine if this is truly at-risk (missing OR failing, not passing overdue assignments)
                is_at_risk = False
                status = None
                
                if score is None:
                    # Missing assignment (no grade recorded)
                    if is_overdue:
                        is_at_risk = True
                        status = 'missing'
                elif score <= 69:
                    # Failing assignment (score below 70)
                    is_at_risk = True
                    status = 'failing'
                    at_risk_grades_list.append(g)
                # If score >= 70, don't include even if overdue (they passed, not at-risk)
                
                if is_at_risk:
                    class_name = g.assignment.class_info.name
                    
                    if class_name not in missing_assignments_by_class:
                        missing_assignments_by_class[class_name] = []
                    
                    missing_assignments_by_class[class_name].append({
                        'title': g.assignment.title,
                        'due_date': g.assignment.due_date.strftime('%Y-%m-%d') if g.assignment.due_date else 'No due date',
                        'status': status,
                        'score': score if score is not None else 'N/A'
                    })
                        
            except Exception as e:
                print(f"Error processing grade {g.id}: {e}")
                import traceback
                traceback.print_exc()
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

