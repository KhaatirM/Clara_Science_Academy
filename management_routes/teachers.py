"""
Teachers routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import db


bp = Blueprint('teachers', __name__)


# ============================================================
# Route: /add-teacher-staff', methods=['GET', 'POST']
# Function: add_teacher_staff
# ============================================================

@bp.route('/add-teacher-staff', methods=['GET', 'POST'])
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
        
        # Validate that emergency_phone is not an email and is not too long
        if emergency_phone:
            if '@' in emergency_phone or len(emergency_phone) > 20:
                flash('Emergency phone number is invalid. Please enter a valid phone number (max 20 characters).', 'danger')
                return redirect(request.url)
        
        # Validate staff phone number
        if phone and len(phone) > 20:
            flash('Phone number is too long. Please enter a valid phone number (max 20 characters).', 'danger')
            return redirect(request.url)
        
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
            
            # Auto-generate Google Workspace email for teacher/staff
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
            
            # Create user account
            user = User()
            user.username = username
            user.password_hash = generate_password_hash(password)
            user.role = assigned_role
            user.teacher_staff_id = teacher_staff.id
            user.email = email  # Set personal email from form
            user.google_workspace_email = generated_workspace_email  # Set generated workspace email
            user.is_temporary_password = True  # New users must change password
            user.password_changed_at = None
            
            db.session.add(user)
            db.session.commit()
            
            # Show success message with credentials
            success_msg = f'{assigned_role} added successfully! Username: {username}, Password: {password}, Staff ID: {teacher_staff.staff_id}.'
            if generated_workspace_email:
                success_msg += f' Google Workspace Email: {generated_workspace_email}.'
            success_msg += ' User will be required to change password on first login.'
            flash(success_msg, 'success')
            return redirect(url_for('management.teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding {assigned_role.lower()}: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('management/add_teacher_staff.html')



# ============================================================
# Route: /edit-teacher-staff/<int:staff_id>
# Function: edit_teacher_staff
# ============================================================

@bp.route('/edit-teacher-staff/<int:staff_id>')
@login_required
@management_required
def edit_teacher_staff(staff_id):
    """Edit a teacher or staff member"""
    teacher_staff = TeacherStaff.query.get_or_404(staff_id)
    return render_template('management/add_teacher_staff.html', teacher_staff=teacher_staff, editing=True)



# ============================================================
# Route: /remove-teacher-staff/<int:staff_id>', methods=['POST']
# Function: remove_teacher_staff
# ============================================================

@bp.route('/remove-teacher-staff/<int:staff_id>', methods=['POST'])
@login_required
@management_required
def remove_teacher_staff(staff_id):
    """Remove a teacher or staff member"""
    teacher_staff = TeacherStaff.query.get_or_404(staff_id)
    db.session.delete(teacher_staff)
    db.session.commit()
    flash('Teacher/Staff member removed successfully.', 'success')
    return redirect(url_for('management.teachers'))

# Report Card Generation - API endpoint to get classes for a student


# ============================================================
# Route: /teachers
# Function: teachers
# ============================================================

@bp.route('/teachers')
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



# ============================================================
# Route: /api/teachers
# Function: api_teachers
# ============================================================

@bp.route('/api/teachers')
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



# ============================================================
# Route: /calendar/teacher-work-days
# Function: teacher_work_days
# ============================================================

@bp.route('/calendar/teacher-work-days')
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




# ============================================================
# Route: /calendar/teacher-work-days/add', methods=['POST']
# Function: add_teacher_work_days
# ============================================================

@bp.route('/calendar/teacher-work-days/add', methods=['POST'])
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




# ============================================================
# Route: /calendar/teacher-work-days/delete/<int:work_day_id>', methods=['POST']
# Function: delete_teacher_work_day
# ============================================================

@bp.route('/calendar/teacher-work-days/delete/<int:work_day_id>', methods=['POST'])
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


# ============================================================
# Route: /view-teacher/<int:teacher_id>
# Function: view_teacher
# ============================================================

@bp.route('/view-teacher/<int:teacher_id>')
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
    
    # Normalize date fields to strings
    def _fmt_date(value):
        try:
            if value is None:
                return None
            from datetime import date, datetime as _dt
            if isinstance(value, (date, _dt)):
                return value.strftime('%Y-%m-%d')
            return str(value)
        except Exception:
            return None

    # Grades taught may be stored as JSON string
    grades_taught_str = None
    try:
        if teacher.grades_taught:
            if isinstance(teacher.grades_taught, str):
                grades_taught_str = teacher.grades_taught
            else:
                import json as _json
                grades_taught_str = _json.dumps(teacher.grades_taught)
    except Exception:
        grades_taught_str = None

    return jsonify({
        'id': teacher.id,
        'first_name': teacher.first_name,
        'middle_initial': getattr(teacher, 'middle_initial', None),
        'last_name': teacher.last_name,
        'staff_id': teacher.staff_id,
        'dob': _fmt_date(getattr(teacher, 'dob', None)),
        'role': role,
        'assigned_role': getattr(teacher, 'assigned_role', None),
        'employment_type': getattr(teacher, 'employment_type', None),
        'subject': getattr(teacher, 'subject', None),
        'email': teacher.email,
        'google_workspace_email': teacher.user.google_workspace_email if teacher.user else None,
        'username': teacher.user.username if teacher.user else None,
        'department': teacher.department,
        'position': teacher.position,
        'hire_date': _fmt_date(teacher.hire_date),
        'phone': teacher.phone,
        'street': teacher.street,
        'apt_unit': teacher.apt_unit,
        'city': teacher.city,
        'state': teacher.state,
        'zip_code': teacher.zip_code,
        'address': address,
        'emergency_contact': emergency_contact,
        'emergency_first_name': getattr(teacher, 'emergency_first_name', None),
        'emergency_last_name': getattr(teacher, 'emergency_last_name', None),
        'emergency_email': getattr(teacher, 'emergency_email', None),
        'emergency_phone': getattr(teacher, 'emergency_phone', None),
        'emergency_relationship': getattr(teacher, 'emergency_relationship', None),
        'grades_taught': grades_taught_str or '',
        'assigned_classes': [{'id': c.id, 'name': c.name, 'subject': c.subject} for c in assigned_classes],
        'total_students': total_students
    })



# ============================================================
# Route: /edit-teacher/<int:teacher_id>', methods=['POST']
# Function: edit_teacher
# ============================================================

@bp.route('/edit-teacher/<int:teacher_id>', methods=['POST'])
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
            
            # Update Google Workspace email
            google_workspace_email = request.form.get('google_workspace_email', '').strip()
            if google_workspace_email:
                # Check if this email is already used by another user
                existing_user = User.query.filter_by(google_workspace_email=google_workspace_email).first()
                if existing_user and existing_user.id != teacher.user.id:
                    return jsonify({'success': False, 'message': f'Google Workspace email {google_workspace_email} is already in use by another user.'}), 400
                
                teacher.user.google_workspace_email = google_workspace_email
            else:
                # Clear the Google Workspace email if field is empty
                teacher.user.google_workspace_email = None
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Teacher/Staff updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


