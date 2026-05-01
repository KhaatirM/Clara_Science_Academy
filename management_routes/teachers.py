"""
Teachers routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import db, TeacherStaff, User, SchoolYear, TeacherWorkDay, Assignment, Attendance, Submission, GroupGrade, Class, Student
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import json
from services.google_directory_service import create_google_user


def _parse_dt_ymd(s):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d')
    except Exception:
        return None


def _filter_by_date_range(qry, col, start_dt, end_dt):
    if start_dt:
        qry = qry.filter(col >= start_dt)
    if end_dt:
        qry = qry.filter(col < (end_dt + timedelta(days=1)))
    return qry


bp = Blueprint('teachers', __name__)

# Note: The /add-teacher-staff route is registered in management_routes/__init__.py
# to ensure the endpoint name is 'management.add_teacher_staff' for backward compatibility


# ============================================================
# Route: /add-teacher-staff', methods=['GET', 'POST']
# Function: add_teacher_staff
# NOTE: This route is registered in management_routes/__init__.py with endpoint 'add_teacher_staff'
# to maintain backward compatibility. The function implementation remains here.
# ============================================================

# Route removed - now registered in management_routes/__init__.py
# @bp.route('/add-teacher-staff', methods=['GET', 'POST'])
# @login_required
# @management_required
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
        # Permissions (only meaningful for Administration department + non-admin roles)
        permissions = request.form.getlist('permissions')
        permissions_json = json.dumps(permissions) if permissions else None
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
            # Tech users implicitly get the tech-only experience; permissions not used here
            permissions_json = None
        
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
            
            # Temporary access fields
            is_temporary = request.form.get('is_temporary') == 'on'
            teacher_staff.is_temporary = is_temporary
            
            if is_temporary:
                access_expires_str = request.form.get('access_expires_at', '').strip()
                if access_expires_str:
                    try:
                        from datetime import datetime, timezone
                        # Parse the datetime string (naive datetime from form)
                        access_expires_at = datetime.strptime(access_expires_str, '%Y-%m-%dT%H:%M')
                        # Make it timezone-aware (UTC) for consistent storage
                        access_expires_at = access_expires_at.replace(tzinfo=timezone.utc)
                        teacher_staff.access_expires_at = access_expires_at
                    except ValueError:
                        flash('Invalid expiration date format. Please use the date picker.', 'warning')
                        return redirect(request.url)
                else:
                    flash('Expiration date is required for temporary staff.', 'danger')
                    return redirect(request.url)
            else:
                teacher_staff.access_expires_at = None
            
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
            user.permissions = permissions_json
            
            db.session.add(user)
            db.session.commit()

            # Create Google Workspace account (non-blocking)
            try:
                if generated_workspace_email:
                    created = create_google_user(
                        {
                            "primaryEmail": generated_workspace_email,
                            "name": {"givenName": teacher_staff.first_name, "familyName": teacher_staff.last_name},
                            "password": "Welcome2CSA!",
                            "orgUnitPath": "/Staff",
                            "changePasswordAtNextLogin": True,
                        }
                    )
                    if not created:
                        flash(
                            f"{assigned_role} created locally, but Google account creation failed for {generated_workspace_email}. "
                            "Please verify the account does not already exist and that Directory permissions are configured.",
                            "warning",
                        )
                else:
                    flash(
                        f"{assigned_role} created locally, but no Google Workspace email was generated, so no Google account was created.",
                        "warning",
                    )
            except Exception as e:
                current_app.logger.error(f"Failed to auto-create Google staff account: {e}")
                flash(
                    f"{assigned_role} created locally, but Google account creation encountered an error. Check logs for details.",
                    "warning",
                )
            
            # Show success message with credentials
            success_msg = f'{assigned_role} added successfully! Username: {username}, Password: {password}, Staff ID: {teacher_staff.staff_id}.'
            if generated_workspace_email:
                success_msg += f' Google Workspace Email: {generated_workspace_email}.'
            success_msg += ' User will be required to change password on first login.'
            if is_temporary and teacher_staff.access_expires_at:
                from datetime import datetime
                expires_str = teacher_staff.access_expires_at.strftime('%Y-%m-%d %I:%M %p')
                success_msg += f' TEMPORARY ACCESS: Access will expire on {expires_str}.'
            flash(success_msg, 'success')
            return redirect(url_for('management.teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding {assigned_role.lower()}: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('management/add_teacher_staff.html', staff_permissions=[])



# ============================================================
# Route: /edit-teacher-staff/<int:staff_id>
# Function: edit_teacher_staff
# ============================================================

@bp.route('/edit-teacher-staff/<int:staff_id>', methods=['GET', 'POST'])
@login_required
@management_required
def edit_teacher_staff(staff_id):
    """Edit a teacher or staff member"""
    teacher_staff = TeacherStaff.query.get_or_404(staff_id)
    
    if request.method == 'POST':
        # Check if this is an AJAX request (from the modal)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        
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
        employment_status = (request.form.get('employment_status', '') or '').strip() or 'Active'
        marked_for_removal = request.form.get('marked_for_removal') == 'on'
        removal_note = (request.form.get('removal_note', '') or '').strip()
        # Handle multiple department selections
        departments = request.form.getlist('department')
        department = ', '.join(departments) if departments else ''
        # Permissions (only meaningful for Administration department + non-admin roles)
        permissions = request.form.getlist('permissions')
        permissions_json = json.dumps(permissions) if permissions else None
        position = request.form.get('position', '').strip()
        subject = request.form.get('subject', '').strip()
        employment_type = request.form.get('employment_type', '').strip()
        
        # Handle multiple grades taught selections
        grades_taught = request.form.getlist('grades_taught')
        grades_taught_json = json.dumps(grades_taught) if grades_taught else ''
        
        # Validate required fields
        if not all([first_name, last_name, email]):
            if is_ajax:
                return jsonify({'success': False, 'message': 'First name, last name, and email are required.'})
            flash('First name, last name, and email are required.', 'danger')
            return render_template('management/add_teacher_staff.html', teacher_staff=teacher_staff, editing=True)
        
        # Validate email format
        if '@' not in email or '.' not in email:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Please enter a valid email address.'})
            flash('Please enter a valid email address.', 'danger')
            return render_template('management/add_teacher_staff.html', teacher_staff=teacher_staff, editing=True)
        
        # Check if email already exists (excluding current staff)
        existing_staff = TeacherStaff.query.filter_by(email=email).first()
        if existing_staff and existing_staff.id != staff_id:
            if is_ajax:
                return jsonify({'success': False, 'message': 'A teacher/staff member with this email already exists.'})
            flash('A teacher/staff member with this email already exists.', 'danger')
            return render_template('management/add_teacher_staff.html', teacher_staff=teacher_staff, editing=True)
        
        try:
            # Update teacher/staff record
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
            teacher_staff.employment_status = employment_status
            teacher_staff.marked_for_removal = marked_for_removal
            teacher_staff.removal_note = removal_note or None
            teacher_staff.status_updated_at = datetime.utcnow()
            teacher_staff.department = department
            teacher_staff.position = position
            teacher_staff.subject = subject
            teacher_staff.employment_type = employment_type
            teacher_staff.grades_taught = grades_taught_json
            
            # Temporary access fields
            is_temporary = request.form.get('is_temporary') == 'on'
            teacher_staff.is_temporary = is_temporary
            
            if is_temporary:
                access_expires_str = request.form.get('access_expires_at', '').strip()
                if access_expires_str:
                    try:
                        from datetime import timezone
                        access_expires_at = datetime.strptime(access_expires_str, '%Y-%m-%dT%H:%M')
                        access_expires_at = access_expires_at.replace(tzinfo=timezone.utc)
                        teacher_staff.access_expires_at = access_expires_at
                    except ValueError:
                        if is_ajax:
                            return jsonify({'success': False, 'message': 'Invalid expiration date format. Please use the date picker.'})
                        flash('Invalid expiration date format. Please use the date picker.', 'warning')
                        return render_template('management/add_teacher_staff.html', teacher_staff=teacher_staff, editing=True)
                else:
                    if is_ajax:
                        return jsonify({'success': False, 'message': 'Expiration date is required for temporary staff.'})
                    flash('Expiration date is required for temporary staff.', 'danger')
                    return render_template('management/add_teacher_staff.html', teacher_staff=teacher_staff, editing=True)
            else:
                teacher_staff.access_expires_at = None
            
            # Address fields
            teacher_staff.street = request.form.get('street_address', '').strip()
            teacher_staff.apt_unit = request.form.get('apt_unit_suite', '').strip()
            teacher_staff.city = request.form.get('city', '').strip()
            teacher_staff.state = request.form.get('state', '').strip()
            teacher_staff.zip_code = request.form.get('zip_code', '').strip()
            
            # Emergency contact fields
            teacher_staff.emergency_first_name = request.form.get('emergency_contact_name', '').strip()
            teacher_staff.emergency_last_name = request.form.get('emergency_contact_last_name', '').strip()
            teacher_staff.emergency_email = request.form.get('emergency_contact_email', '').strip()
            teacher_staff.emergency_phone = request.form.get('emergency_contact_phone', '').strip()
            teacher_staff.emergency_relationship = request.form.get('emergency_contact_relationship', '').strip()
            
            # Update user account if it exists
            user = User.query.filter_by(teacher_staff_id=staff_id).first()
            if user:
                user.email = email
                user.role = assigned_role
                user.permissions = permissions_json
            
            db.session.commit()
            
            if is_ajax:
                return jsonify({'success': True, 'message': f'{assigned_role} updated successfully!'})
            
            flash(f'{assigned_role} updated successfully!', 'success')
            return redirect(url_for('management.teachers'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = f'Error updating {assigned_role.lower()}: {str(e)}'
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg})
            flash(error_msg, 'danger')
            return render_template('management/add_teacher_staff.html', teacher_staff=teacher_staff, editing=True)
    
    staff_permissions = []
    try:
        if teacher_staff.user and getattr(teacher_staff.user, 'permissions', None):
            raw = teacher_staff.user.permissions
            staff_permissions = json.loads(raw) if isinstance(raw, str) else (list(raw) if raw else [])
            if not isinstance(staff_permissions, list):
                staff_permissions = []
    except Exception:
        staff_permissions = []

    return render_template(
        'management/add_teacher_staff.html',
        teacher_staff=teacher_staff,
        editing=True,
        staff_permissions=staff_permissions
    )



# ============================================================
# Route: /remove-teacher-staff/<int:staff_id>', methods=['POST']
# Function: remove_teacher_staff
# ============================================================

def _remove_staff_wants_json():
    """AJAX remove from dashboard: return JSON instead of redirect so the UI can refresh reliably."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    accept = (request.headers.get('Accept') or '').lower()
    return 'application/json' in accept


def _actor_user_id_for_staff_removal(excluded_user_ids):
    """Account that will own reassigned records after removing staff user row(s)."""
    excluded = {int(x) for x in excluded_user_ids if x is not None}
    uid = getattr(current_user, 'id', None)
    if uid is not None and uid not in excluded:
        return uid
    q = User.query
    if excluded:
        q = q.filter(~User.id.in_(excluded))
    alt = q.order_by(User.id).first()
    return alt.id if alt else None


def _detach_user_references_before_delete(user_id, fallback_user_id):
    """
    Reassign NOT NULL FKs that point at user_id, and delete membership-style rows.
    Required before deleting a User; otherwise SQLAlchemy emits SET NULL updates that
    violate NOT NULL (e.g. message_group.created_by).
    """
    from models import (
        Announcement,
        AnnouncementReadReceipt,
        BugReport,
        GradeHistory,
        Message,
        MessageGroup,
        MessageGroupMember,
        MessageReaction,
        Notification,
        QuestionBank,
        ScheduledAnnouncement,
    )

    if fallback_user_id is None or int(user_id) == int(fallback_user_id):
        raise ValueError('Invalid fallback user for detaching references')

    uid = int(user_id)
    fb = int(fallback_user_id)

    MessageGroup.query.filter_by(created_by=uid).update(
        {MessageGroup.created_by: fb}, synchronize_session=False
    )
    QuestionBank.query.filter_by(created_by=uid).update(
        {QuestionBank.created_by: fb}, synchronize_session=False
    )
    GradeHistory.query.filter_by(changed_by=uid).update(
        {GradeHistory.changed_by: fb}, synchronize_session=False
    )
    Announcement.query.filter_by(sender_id=uid).update(
        {Announcement.sender_id: fb}, synchronize_session=False
    )
    ScheduledAnnouncement.query.filter_by(sender_id=uid).update(
        {ScheduledAnnouncement.sender_id: fb}, synchronize_session=False
    )
    BugReport.query.filter_by(user_id=uid).update(
        {BugReport.user_id: fb}, synchronize_session=False
    )
    Message.query.filter_by(sender_id=uid).update(
        {Message.sender_id: fb}, synchronize_session=False
    )
    Message.query.filter_by(recipient_id=uid).update(
        {Message.recipient_id: fb}, synchronize_session=False
    )

    Notification.query.filter_by(user_id=uid).delete(synchronize_session=False)
    MessageGroupMember.query.filter_by(user_id=uid).delete(synchronize_session=False)
    MessageReaction.query.filter_by(user_id=uid).delete(synchronize_session=False)
    AnnouncementReadReceipt.query.filter_by(user_id=uid).delete(synchronize_session=False)


@bp.route('/remove-teacher-staff/<int:staff_id>', methods=['POST'])
@login_required
@management_required
def remove_teacher_staff(staff_id):
    """
    Soft delete a teacher or staff member.
    - Marks the teacher as deleted (preserves all data they created)
    - Deletes the associated user account
    - All assignments, grades, and other data remain intact with the deleted teacher's ID
    """
    from models import User
    from datetime import datetime
    
    teacher_staff = TeacherStaff.query.get_or_404(staff_id)
    
    # Check if already deleted
    if teacher_staff.is_deleted:
        msg = 'This teacher/staff member has already been deleted.'
        if _remove_staff_wants_json():
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'warning')
        return redirect(url_for('management.teachers'))
    
    try:
        # If this staff member is assigned as primary teacher for any class,
        # reassign those classes to a placeholder so class workflows keep working.
        from models import Class
        placeholder_email = 'unassigned.teacher@clarascienceacademy.org'
        placeholder = TeacherStaff.query.filter_by(email=placeholder_email).first()
        if not placeholder:
            placeholder = TeacherStaff(
                first_name='Unassigned',
                last_name='Teacher',
                email=placeholder_email,
                assigned_role='Unassigned (system)',
                employment_status='Inactive',
                is_deleted=True,
            )
            db.session.add(placeholder)
            db.session.flush()

        # Move primary-teacher classes away from the removed account.
        primary_classes = Class.query.filter_by(teacher_id=staff_id).all()
        for c in primary_classes:
            c.teacher_id = placeholder.id

        # Remove from additional/substitute teacher mappings to avoid showing deleted staff in class rosters.
        try:
            from models import class_additional_teachers, class_substitute_teachers
            db.session.execute(class_additional_teachers.delete().where(class_additional_teachers.c.teacher_id == staff_id))
            db.session.execute(class_substitute_teachers.delete().where(class_substitute_teachers.c.teacher_id == staff_id))
        except Exception:
            pass

        # Soft delete: Mark teacher as deleted instead of actually deleting
        teacher_staff.is_deleted = True
        teacher_staff.deleted_at = datetime.utcnow()
        
        # Store the teacher's name for display purposes (in case needed)
        # The name fields remain intact, just marked as deleted
        
        # Delete associated User account(s) - this removes login access
        user_accounts = User.query.filter_by(teacher_staff_id=staff_id).all()
        if user_accounts:
            uids = [u.id for u in user_accounts]
            fallback_uid = _actor_user_id_for_staff_removal(uids)
            if not fallback_uid:
                raise ValueError(
                    'No user account is available to reassign messaging and audit references. '
                    'Cannot remove this staff login safely.'
                )
            for user in user_accounts:
                _detach_user_references_before_delete(user.id, fallback_uid)
                db.session.delete(user)
        
        # IMPORTANT: Do NOT modify class assignments, assignments, grades, or any other data
        # All foreign key references to this teacher remain intact
        # This preserves the historical record of who created/graded what
        # The teacher will simply not appear in active teacher lists due to is_deleted flag
        
        db.session.commit()
        success_msg = (
            f'Teacher/Staff member "{teacher_staff.first_name} {teacher_staff.last_name}" has been removed. '
            'Their account has been deleted, but all their work (assignments, grades, etc.) has been preserved.'
        )
        if _remove_staff_wants_json():
            return jsonify({'success': True, 'message': success_msg})
        flash(success_msg, 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting teacher/staff: {str(e)}")
        err_msg = f'Error removing teacher/staff member: {str(e)}'
        if _remove_staff_wants_json():
            return jsonify({'success': False, 'message': err_msg}), 500
        flash(err_msg, 'danger')

    return redirect(url_for('management.teachers'))

# Report Card Generation - API endpoint to get classes for a student


# ============================================================
# Staff directory (current + former) — embedded on Teachers & Staff for
# Directors & School Administrators only (see teachers_view=directory)
# ============================================================

def _staff_directory_context():
    """Template variables for current/former lists; callers must enforce role."""
    tab = (request.args.get('staff_dir_tab') or request.args.get('tab', 'current')).strip()
    if tab not in ('current', 'former'):
        tab = 'current'
    q = (request.args.get('staff_dir_q') or request.args.get('q', '')).strip()

    def _search_filter():
        if not q:
            return None
        like = f'%{q}%'
        return db.or_(
            TeacherStaff.first_name.ilike(like),
            TeacherStaff.last_name.ilike(like),
            TeacherStaff.middle_initial.ilike(like),
            TeacherStaff.email.ilike(like),
            TeacherStaff.staff_id.ilike(like),
            TeacherStaff.assigned_role.ilike(like),
            TeacherStaff.department.ilike(like),
            TeacherStaff.position.ilike(like),
            TeacherStaff.subject.ilike(like),
            TeacherStaff.phone.ilike(like),
        )

    current_base = TeacherStaff.query.filter(
        TeacherStaff.is_deleted == False,
        db.or_(
            TeacherStaff.employment_status.in_(['Active', 'On Leave']),
            TeacherStaff.employment_status == '',
            TeacherStaff.employment_status.is_(None),
        ),
    )
    former_base = TeacherStaff.query.filter(
        db.or_(
            TeacherStaff.is_deleted == True,
            TeacherStaff.employment_status == 'Inactive',
        ),
    )

    sf = _search_filter()
    current_count = current_base.count()
    former_count = former_base.count()

    q_current = current_base
    q_former = former_base
    if sf is not None:
        q_current = q_current.filter(sf)
        q_former = q_former.filter(sf)

    current_staff = q_current.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()
    former_staff = q_former.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()

    return {
        'staff_dir_tab': tab,
        'staff_dir_q': q,
        'staff_dir_current_staff': current_staff,
        'staff_dir_former_staff': former_staff,
        'staff_dir_current_count': current_count,
        'staff_dir_former_count': former_count,
    }


# ============================================================
# Route: /teachers
# Function: teachers
# ============================================================

@bp.route('/teachers')
@login_required
@management_required
def teachers():
    teachers_view = request.args.get('teachers_view', 'manage')
    if teachers_view not in ('manage', 'directory'):
        teachers_view = 'manage'
    if teachers_view == 'directory' and current_user.role not in ['School Administrator', 'Director']:
        teachers_view = 'manage'

    if teachers_view == 'directory':
        ctx = _staff_directory_context()
        return render_template(
            'management/role_dashboard.html',
            section='teachers',
            active_tab='teachers',
            teachers_view='directory',
            teachers=[],
            search_query='',
            search_type='all',
            department_filter='',
            role_filter='',
            employment_filter='',
            sort_by='name',
            sort_order='asc',
            total_teachers=0,
            teachers_with_accounts=0,
            teachers_without_accounts=0,
            **ctx,
        )

    # Get search parameters
    search_query = request.args.get('search', '').strip()
    search_type = request.args.get('search_type', 'all')
    department_filter = request.args.get('department', '')
    role_filter = request.args.get('role', '')
    employment_filter = request.args.get('employment', '')
    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'asc')
    
    # Build the query - exclude deleted teachers
    query = TeacherStaff.query.filter(TeacherStaff.is_deleted == False)
    
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
                         active_tab='teachers',
                         teachers_view='manage')



# ============================================================
# Route: /api/teachers
# Function: api_teachers
# ============================================================

@bp.route('/api/teachers')
@login_required
@management_required
def api_teachers():
    """API endpoint to get teachers for dropdowns."""
    teachers = TeacherStaff.query.filter(TeacherStaff.is_deleted == False).all()
    return jsonify([{
        'id': teacher.id,
        'first_name': teacher.first_name,
        'last_name': teacher.last_name,
        'role': teacher.user.role if teacher.user else 'No Role'
        ,
        'permissions': teacher.user.permissions if teacher.user and hasattr(teacher.user, 'permissions') else None
    } for teacher in teachers])



# ============================================================
# Route: /calendar/teacher-work-days
# Function: teacher_work_days
# ============================================================

# NOTE: This route is now registered in management_routes/__init__.py with endpoint 'teacher_work_days'
# to maintain backward compatibility. The route decorator is commented out here to avoid conflicts.
# @bp.route('/calendar/teacher-work-days')
# @login_required
# @management_required
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
            return redirect(url_for('management.calendar'))
        
        # Get active school year
        active_year = SchoolYear.query.filter_by(is_active=True).first()
        if not active_year:
            flash('No active school year found.', 'danger')
            return redirect(url_for('management.calendar'))
        
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
    
    month = request.form.get('redirect_month')
    year = request.form.get('redirect_year')
    if month and year:
        return redirect(url_for('management.calendar', month=month, year=year))
    return redirect(url_for('management.calendar'))




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
    
    month = request.form.get('redirect_month')
    year = request.form.get('redirect_year')
    if month and year:
        return redirect(url_for('management.calendar', month=month, year=year))
    return redirect(url_for('management.calendar'))


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
    try:
        teacher = TeacherStaff.query.get_or_404(teacher_id)
    except Exception as e:
        current_app.logger.error(f"Error loading teacher {teacher_id}: {str(e)}")
        return jsonify({'error': 'Could not load teacher/staff details.'}), 500
    
    try:
        # Get assigned classes
        from models import Class
        assigned_classes = Class.query.filter_by(teacher_id=teacher.id).all()
        
        # Count students in all assigned classes
        total_students = 0
        try:
            from models import Enrollment
            for class_info in assigned_classes:
                enrollment_count = Enrollment.query.filter_by(class_id=class_info.id, is_active=True).count()
                total_students += enrollment_count
        except Exception as e:
            current_app.logger.warning(f"Error counting students for teacher {teacher_id}: {str(e)}")
            total_students = 0
        
        # Get role from user account
        try:
            role = teacher.user.role if teacher.user else "No Account"
        except AttributeError:
            role = "No Account"
    except Exception as e:
        current_app.logger.error(f"Error processing teacher data {teacher_id}: {str(e)}")
        return jsonify({'error': 'Could not load teacher/staff details.'}), 500
    
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

    try:
        return jsonify({
            'id': teacher.id,
            'first_name': teacher.first_name,
            'middle_initial': getattr(teacher, 'middle_initial', None),
            'last_name': teacher.last_name,
            'staff_id': teacher.staff_id,
            'dob': _fmt_date(getattr(teacher, 'dob', None)),
            'staff_ssn': getattr(teacher, 'staff_ssn', None),
            'role': role,
            'assigned_role': getattr(teacher, 'assigned_role', None),
            'employment_type': getattr(teacher, 'employment_type', None),
            'employment_status': getattr(teacher, 'employment_status', 'Active'),
            'marked_for_removal': bool(getattr(teacher, 'marked_for_removal', False)),
            'removal_note': getattr(teacher, 'removal_note', None),
            'subject': getattr(teacher, 'subject', None),
            'email': teacher.email,
            'google_workspace_email': teacher.user.google_workspace_email if teacher.user and hasattr(teacher.user, 'google_workspace_email') else None,
            'username': teacher.user.username if teacher.user and hasattr(teacher.user, 'username') else None,
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
            'total_students': total_students,
            'is_temporary': getattr(teacher, 'is_temporary', False),
            'access_expires_at': _fmt_date(getattr(teacher, 'access_expires_at', None))
        })
    except Exception as e:
        current_app.logger.error(f"Error serializing teacher data {teacher_id}: {str(e)}")
        return jsonify({'error': 'Could not load teacher/staff details.'}), 500


@bp.route('/staff-activity-record/<int:teacher_id>')
@login_required
@management_required
def staff_activity_record(teacher_id):
    """
    Print-friendly activity record for a staff member.
    Includes: assignments created, attendance taken, manual submission marks, group grades given.
    """
    if current_user.role not in ['Director', 'School Administrator']:
        abort(403)

    teacher = TeacherStaff.query.get_or_404(teacher_id)

    start = _parse_dt_ymd(request.args.get('start'))
    end = _parse_dt_ymd(request.args.get('end'))
    if not start and not end:
        # default: last 180 days
        end = datetime.utcnow()
        start = end - timedelta(days=180)

    # Assignments created: handle both normal created_by(User.id) and historical created_by(TeacherStaff.id).
    user_ids = [u.id for u in User.query.filter_by(teacher_staff_id=teacher_id).all()]
    created_assignments_q = Assignment.query
    if user_ids:
        created_assignments_q = created_assignments_q.filter(
            db.or_(Assignment.created_by.in_(user_ids), Assignment.created_by == teacher_id)
        )
    else:
        created_assignments_q = created_assignments_q.filter(Assignment.created_by == teacher_id)
    created_assignments_q = _filter_by_date_range(created_assignments_q, Assignment.created_at, start, end)
    created_assignments = created_assignments_q.order_by(Assignment.created_at.desc()).limit(5000).all()

    # Attendance taken (per-student class attendance)
    attendance_q = Attendance.query.filter(Attendance.teacher_id == teacher_id)
    attendance_q = _filter_by_date_range(attendance_q, Attendance.created_at, start, end)
    attendance_records = attendance_q.order_by(Attendance.created_at.desc()).limit(5000).all()

    # Manual submission marks
    marked_submissions_q = Submission.query.filter(Submission.marked_by == teacher_id)
    marked_submissions_q = _filter_by_date_range(marked_submissions_q, Submission.marked_at, start, end)
    marked_submissions = marked_submissions_q.order_by(Submission.marked_at.desc()).limit(5000).all()

    # Group grades given
    group_grades_q = GroupGrade.query.filter(GroupGrade.graded_by == teacher_id)
    group_grades_q = _filter_by_date_range(group_grades_q, GroupGrade.graded_at, start, end)
    group_grades = group_grades_q.order_by(GroupGrade.graded_at.desc()).limit(5000).all()

    return render_template(
        'management/staff_activity_record.html',
        teacher=teacher,
        start=start.date().isoformat() if start else '',
        end=end.date().isoformat() if end else '',
        created_assignments=created_assignments,
        attendance_records=attendance_records,
        marked_submissions=marked_submissions,
        group_grades=group_grades,
    )


@bp.route('/staff-activity-record/<int:teacher_id>/export.csv')
@login_required
@management_required
def export_staff_activity_record_csv(teacher_id):
    """CSV export for the staff activity record."""
    if current_user.role not in ['Director', 'School Administrator']:
        abort(403)

    teacher = TeacherStaff.query.get_or_404(teacher_id)
    start = _parse_dt_ymd(request.args.get('start'))
    end = _parse_dt_ymd(request.args.get('end'))
    if not start and not end:
        end = datetime.utcnow()
        start = end - timedelta(days=180)

    user_ids = [u.id for u in User.query.filter_by(teacher_staff_id=teacher_id).all()]
    created_assignments_q = Assignment.query
    if user_ids:
        created_assignments_q = created_assignments_q.filter(
            db.or_(Assignment.created_by.in_(user_ids), Assignment.created_by == teacher_id)
        )
    else:
        created_assignments_q = created_assignments_q.filter(Assignment.created_by == teacher_id)
    created_assignments_q = _filter_by_date_range(created_assignments_q, Assignment.created_at, start, end)
    created_assignments = created_assignments_q.order_by(Assignment.created_at.desc()).limit(20000).all()

    attendance_q = Attendance.query.filter(Attendance.teacher_id == teacher_id)
    attendance_q = _filter_by_date_range(attendance_q, Attendance.created_at, start, end)
    attendance_records = attendance_q.order_by(Attendance.created_at.desc()).limit(20000).all()

    marked_submissions_q = Submission.query.filter(Submission.marked_by == teacher_id)
    marked_submissions_q = _filter_by_date_range(marked_submissions_q, Submission.marked_at, start, end)
    marked_submissions = marked_submissions_q.order_by(Submission.marked_at.desc()).limit(20000).all()

    group_grades_q = GroupGrade.query.filter(GroupGrade.graded_by == teacher_id)
    group_grades_q = _filter_by_date_range(group_grades_q, GroupGrade.graded_at, start, end)
    group_grades = group_grades_q.order_by(GroupGrade.graded_at.desc()).limit(20000).all()

    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['SECTION', 'timestamp', 'class', 'item', 'details'])

    for a in created_assignments:
        cls = a.class_info.name if a.class_info else ''
        w.writerow(['assignment_created', a.created_at.isoformat() if a.created_at else '', cls, a.title, a.assignment_type])

    for r in attendance_records:
        cls = r.class_info.name if r.class_info else ''
        stu = f"{r.student.first_name} {r.student.last_name}" if r.student else ''
        w.writerow(['attendance_taken', r.created_at.isoformat() if r.created_at else '', cls, stu, f"{r.date} {r.status}"])

    for s in marked_submissions:
        cls = s.assignment.class_info.name if s.assignment and s.assignment.class_info else ''
        item = s.assignment.title if s.assignment else f"assignment_id={s.assignment_id}"
        w.writerow(['submission_marked', s.marked_at.isoformat() if s.marked_at else '', cls, item, f"{s.submission_type} {s.submission_notes or ''}"])

    for g in group_grades:
        cls = g.group_assignment.class_info.name if g.group_assignment and g.group_assignment.class_info else ''
        item = g.group_assignment.title if g.group_assignment else f"group_assignment_id={g.group_assignment_id}"
        stu = f"{g.student.first_name} {g.student.last_name}" if g.student else f"student_id={g.student_id}"
        w.writerow(['group_grade_given', g.graded_at.isoformat() if g.graded_at else '', cls, item, stu])

    out = buf.getvalue().encode('utf-8')
    return Response(
        out,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=staff_activity_{teacher.id}.csv'},
    )


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
        
        # Temporary access fields
        is_temporary = request.form.get('is_temporary') == 'on'
        teacher.is_temporary = is_temporary
        
        if is_temporary:
            access_expires_str = request.form.get('access_expires_at', '').strip()
            if access_expires_str:
                try:
                    from datetime import datetime, timezone
                    access_expires_at = datetime.strptime(access_expires_str, '%Y-%m-%dT%H:%M')
                    access_expires_at = access_expires_at.replace(tzinfo=timezone.utc)
                    teacher.access_expires_at = access_expires_at
                except ValueError:
                    return jsonify({'success': False, 'message': 'Invalid expiration date format.'}), 400
        else:
            teacher.access_expires_at = None
        
        # Update user role if user account exists
        if teacher.user:
            # Auto-assign role for Tech users
            if current_user.role in ['Tech', 'IT Support']:
                teacher.user.role = 'IT Support'
            else:
                teacher.user.role = request.form.get('assigned_role', teacher.user.role)
                # Permissions update (if provided)
                perms = request.form.getlist('permissions')
                teacher.user.permissions = json.dumps(perms) if perms else None
            
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


