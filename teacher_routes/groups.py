"""
Group management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import db, Class, StudentGroup, StudentGroupMember, GroupAssignment, Enrollment, Student, SchoolYear
from datetime import datetime
from werkzeug.utils import secure_filename
import json
import os

def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'xls', 'xlsx', 'ppt', 'pptx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

bp = Blueprint('groups', __name__)

@bp.route('/groups')
@login_required
@teacher_required
def groups_hub():
    """Redirect to My Classes - groups should be managed from class view."""
    flash("Please select a class first to manage its groups.", "info")
    return redirect(url_for('teacher.dashboard.my_classes'))

@bp.route('/groups/class/<int:class_id>')
@login_required
@teacher_required
def class_groups(class_id):
    """View and manage groups for a specific class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to manage groups for this class.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    # Get groups for this class
    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
    
    # Add member info to each group (including leader status)
    for group in groups:
        members = StudentGroupMember.query.filter_by(group_id=group.id).all()
        group.members_list = []
        for m in members:
            if m.student:
                member_data = {
                    'student': m.student,
                    'is_leader': m.is_leader
                }
                group.members_list.append(member_data)
        group.member_count = len(group.members_list)
    
    # Get enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [e.student for e in enrollments if e.student]
    
    return render_template('teachers/teacher_class_groups.html',
                         class_obj=class_obj,
                         groups=groups,
                         students=students,
                         enrolled_students=students)

@bp.route('/groups/create/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def create_group(class_id):
    """Create a new group for a class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to create groups for this class.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    max_students = request.form.get('max_students', type=int)
    
    if not name:
        flash("Group name is required.", "danger")
        return redirect(url_for('teacher.groups.class_groups', class_id=class_id))
    
    try:
        teacher = get_teacher_or_admin()
        new_group = StudentGroup(
            name=name,
            description=description,
            class_id=class_id,
            created_by=teacher.id if teacher else current_user.teacher_staff_id,
            max_students=max_students if max_students else None,
            is_active=True
        )
        db.session.add(new_group)
        db.session.commit()
        
        flash(f"Group '{name}' created successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating group: {str(e)}", "danger")
    
    return redirect(url_for('teacher.groups.class_groups', class_id=class_id))

def _get_class_group_size_max(class_id):
    """Return the smallest group_size_max across all group assignments for this class (most restrictive)."""
    assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
    if not assignments:
        return None
    return min(ga.group_size_max for ga in assignments if ga.group_size_max is not None)


@bp.route('/groups/<int:group_id>/add-member', methods=['POST'])
@login_required
@teacher_required
def add_member(group_id):
    """Add one or more students to a group."""
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check authorization
    if not is_authorized_for_class(group.class_info):
        flash("You are not authorized to modify this group.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    # Get multiple student IDs (can be single or multiple)
    student_ids = request.form.getlist('student_ids')
    leader_id = request.form.get('leader_id', type=int)  # Single leader ID
    
    if not student_ids:
        flash("Please select at least one student.", "danger")
        return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))
    
    # Enforce group size from group assignment settings
    max_allowed = _get_class_group_size_max(group.class_id)
    if max_allowed is not None:
        current_count = StudentGroupMember.query.filter_by(group_id=group_id).count()
        new_members_count = sum(
            1 for sid in student_ids
            if not StudentGroupMember.query.filter_by(group_id=group_id, student_id=int(sid)).first()
        )
        if current_count + new_members_count > max_allowed:
            flash(
                f"Group size cannot exceed {max_allowed} students (set by group assignment settings). "
                f"Current: {current_count}, trying to add: {new_members_count}.",
                "danger"
            )
            return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))
    
    added_count = 0
    skipped_count = 0
    
    try:
        for student_id_str in student_ids:
            student_id = int(student_id_str)
            
            # Check if already a member
            existing = StudentGroupMember.query.filter_by(group_id=group_id, student_id=student_id).first()
            if existing:
                # Update leader status if this student is the selected leader
                if leader_id == student_id and not existing.is_leader:
                    existing.is_leader = True
                    added_count += 1
                else:
                    skipped_count += 1
                continue
            
            # Determine if this student should be leader
            is_leader = (leader_id == student_id)
            
            new_member = StudentGroupMember(
                group_id=group_id,
                student_id=student_id,
                is_leader=is_leader
            )
            db.session.add(new_member)
            added_count += 1
        
        # If a leader was selected, ensure only one leader exists
        if leader_id:
            # Remove leader status from other members
            StudentGroupMember.query.filter_by(group_id=group_id).filter(
                StudentGroupMember.student_id != leader_id
            ).update({'is_leader': False}, synchronize_session=False)
        
        db.session.commit()
        
        if added_count > 0:
            flash(f"{added_count} student(s) added to group successfully!", "success")
        if skipped_count > 0:
            flash(f"{skipped_count} student(s) were already in the group.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding students: {str(e)}", "danger")
    
    return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))

@bp.route('/groups/<int:group_id>/remove-member/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def remove_member(group_id, student_id):
    """Remove a student from a group."""
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check authorization
    if not is_authorized_for_class(group.class_info):
        flash("You are not authorized to modify this group.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    try:
        member = StudentGroupMember.query.filter_by(group_id=group_id, student_id=student_id).first()
        if member:
            db.session.delete(member)
            db.session.commit()
            flash("Student removed from group successfully!", "success")
        else:
            flash("Student not found in this group.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Error removing student: {str(e)}", "danger")
    
    return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))

@bp.route('/groups/<int:group_id>/edit', methods=['POST'])
@login_required
@teacher_required
def edit_group(group_id):
    """Edit a group's name and description."""
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check authorization
    if not is_authorized_for_class(group.class_info):
        flash("You are not authorized to edit this group.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    max_students = request.form.get('max_students', type=int)
    
    if not name:
        flash("Group name is required.", "danger")
        return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))
    
    try:
        group.name = name
        group.description = description
        if max_students:
            group.max_students = max_students
        else:
            group.max_students = None
        db.session.commit()
        
        flash(f"Group '{name}' updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating group: {str(e)}", "danger")
    
    return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))

@bp.route('/groups/<int:group_id>/set-leader', methods=['POST'])
@login_required
@teacher_required
def set_leader(group_id):
    """Set or change the group leader."""
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check authorization
    if not is_authorized_for_class(group.class_info):
        flash("You are not authorized to modify this group.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    student_id = request.form.get('student_id', type=int)
    
    if not student_id:
        flash("Student ID required.", "danger")
        return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))
    
    # Verify student is a member
    member = StudentGroupMember.query.filter_by(group_id=group_id, student_id=student_id).first()
    if not member:
        flash("Student is not a member of this group.", "warning")
        return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))
    
    try:
        # Remove leader status from all members
        StudentGroupMember.query.filter_by(group_id=group_id).update({'is_leader': False}, synchronize_session=False)
        
        # Set new leader
        member.is_leader = True
        db.session.commit()
        
        flash("Group leader updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating group leader: {str(e)}", "danger")
    
    return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))

@bp.route('/groups/<int:group_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_group(group_id):
    """Delete a group."""
    group = StudentGroup.query.get_or_404(group_id)
    class_id = group.class_id
    
    # Check authorization
    if not is_authorized_for_class(group.class_info):
        flash("You are not authorized to delete this group.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    try:
        # Delete all members first
        StudentGroupMember.query.filter_by(group_id=group_id).delete()
        # Mark group as inactive
        group.is_active = False
        db.session.commit()
        
        flash(f"Group '{group.name}' deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting group: {str(e)}", "danger")
    
    return redirect(url_for('teacher.groups.class_groups', class_id=class_id))

@bp.route('/group-assignment/select-class')
@login_required
@teacher_required
def group_assignment_select_class():
    """Select a class for group assignment creation."""
    teacher = get_teacher_or_admin()
    
    # Get classes for the current teacher/admin
    if is_admin():
        classes = Class.query.all()
    else:
        if teacher is None:
            classes = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    # If teacher has only 1 class, skip selection and go directly to creation
    if not is_admin() and len(classes) == 1:
        return redirect(url_for('teacher.groups.create_group_assignment', class_id=classes[0].id))
    
    return render_template('teachers/teacher_group_assignment_select_class.html', classes=classes)

@bp.route('/group-assignment/create/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_group_assignment(class_id):
    """Create a group assignment for a specific class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to create group assignments for this class.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    # Get groups for this class
    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
    
    # Add member info to each group
    for group in groups:
        members = StudentGroupMember.query.filter_by(group_id=group.id).all()
        group.members_list = [m.student for m in members if m.student]
        group.member_count = len(group.members_list)
    
    if not groups:
        flash("No groups found for this class. Please create groups first.", "warning")
        return redirect(url_for('teacher.groups.class_groups', class_id=class_id))
    
    return render_template('teachers/teacher_create_group_assignment.html',
                         class_item=class_obj,
                         groups=groups)

@bp.route('/group-assignment/save/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def save_group_assignment(class_id):
    """Save a new group assignment."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to create group assignments for this class.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        instructions = request.form.get('instructions', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        open_date_str = request.form.get('open_date', '').strip()
        close_date_str = request.form.get('close_date', '').strip()
        quarter = request.form.get('quarter', '').strip()
        assignment_status = request.form.get('assignment_status', 'Active').strip()
        assignment_category = request.form.get('assignment_category', '').strip()
        
        # Handle total_points as float (can be decimal like 50.5)
        total_points_str = request.form.get('total_points', '100').strip()
        try:
            total_points = float(total_points_str) if total_points_str else 100.0
        except (ValueError, TypeError):
            total_points = 100.0
        
        # Handle category_weight as float
        category_weight_str = request.form.get('category_weight', '0').strip()
        try:
            category_weight = float(category_weight_str) if category_weight_str else 0.0
        except (ValueError, TypeError):
            category_weight = 0.0
        
        # Advanced grading options
        allow_extra_credit = request.form.get('allow_extra_credit') == 'on'
        max_extra_credit_points_str = request.form.get('max_extra_credit_points', '0').strip()
        try:
            max_extra_credit_points = float(max_extra_credit_points_str) if max_extra_credit_points_str else 0.0
        except (ValueError, TypeError):
            max_extra_credit_points = 0.0
        
        late_penalty_enabled = request.form.get('late_penalty_enabled') == 'on'
        late_penalty_per_day_str = request.form.get('late_penalty_per_day', '0').strip()
        try:
            late_penalty_per_day = float(late_penalty_per_day_str) if late_penalty_per_day_str else 0.0
        except (ValueError, TypeError):
            late_penalty_per_day = 0.0
        
        late_penalty_max_days_str = request.form.get('late_penalty_max_days', '0').strip()
        try:
            late_penalty_max_days = int(late_penalty_max_days_str) if late_penalty_max_days_str else 0
        except (ValueError, TypeError):
            late_penalty_max_days = 0
        
        grade_scale_preset = request.form.get('grade_scale_preset', '').strip()
        grade_scale = None
        if grade_scale_preset == 'standard':
            grade_scale = json.dumps({"A": 90, "B": 80, "C": 70, "D": 60, "F": 0, "use_plus_minus": False})
        elif grade_scale_preset == 'strict':
            grade_scale = json.dumps({"A": 93, "B": 85, "C": 77, "D": 70, "F": 0, "use_plus_minus": False})
        elif grade_scale_preset == 'lenient':
            grade_scale = json.dumps({"A": 88, "B": 78, "C": 68, "D": 58, "F": 0, "use_plus_minus": False})
        
        selected_groups = request.form.getlist('groups')  # List of group IDs
        
        # Check if this is admin view
        admin_view = request.args.get('admin_view') == 'true'
        
        if not title or not due_date_str or not selected_groups or not quarter:
            flash("Title, due date, quarter, and at least one group are required.", "danger")
            return redirect(url_for('teacher.groups.create_group_assignment', class_id=class_id, admin_view=admin_view))
        
        # Parse dates
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        open_date = datetime.strptime(open_date_str, '%Y-%m-%dT%H:%M') if open_date_str else None
        close_date = datetime.strptime(close_date_str, '%Y-%m-%dT%H:%M') if close_date_str else None
        
        # Get current school year
        current_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_year:
            flash("No active school year found. Please contact administrator.", "danger")
            return redirect(url_for('teacher.groups.create_group_assignment', class_id=class_id, admin_view=admin_view))
        
        # Create group assignment
        teacher = get_teacher_or_admin()
        # Get assignment context from form or query parameter
        assignment_context = request.form.get('assignment_context', 'homework')
        
        new_assignment = GroupAssignment(
            title=title,
            description=description,
            class_id=class_id,
            due_date=due_date,
            open_date=open_date,
            close_date=close_date,
            quarter=quarter,
            school_year_id=current_year.id,
            assignment_type='pdf',
            assignment_context=assignment_context,
            total_points=total_points,
            assignment_category=assignment_category if assignment_category else None,
            category_weight=category_weight,
            allow_extra_credit=allow_extra_credit,
            max_extra_credit_points=max_extra_credit_points,
            late_penalty_enabled=late_penalty_enabled,
            late_penalty_per_day=late_penalty_per_day,
            late_penalty_max_days=late_penalty_max_days,
            grade_scale=grade_scale,
            selected_group_ids=json.dumps(selected_groups),  # Store as JSON
            created_by=current_user.id,
            status=assignment_status
        )
        db.session.add(new_assignment)
        db.session.flush()  # Get the ID for file path
        
        # Handle file upload
        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                unique_filename = timestamp + filename
                
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'group_assignments')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, unique_filename)
                file.save(filepath)
                
                new_assignment.attachment_filename = unique_filename
                new_assignment.attachment_original_filename = filename
                new_assignment.attachment_file_path = filepath
                new_assignment.attachment_file_size = os.path.getsize(filepath)
                new_assignment.attachment_mime_type = file.content_type
        
        db.session.commit()
        flash(f"Group assignment '{title}' created successfully for {len(selected_groups)} group(s)!", "success")
        
        # Redirect to appropriate page based on user role
        if admin_view:
            return redirect(url_for('management.admin_class_group_assignments', class_id=class_id))
        else:
            return redirect(url_for('teacher.dashboard.assignments_and_grades'))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating group assignment: {str(e)}", "danger")
        admin_view = request.args.get('admin_view') == 'true'
        return redirect(url_for('teacher.groups.create_group_assignment', class_id=class_id, admin_view=admin_view))

