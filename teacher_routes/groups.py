"""
Group management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import db, Class, StudentGroup, StudentGroupMember, GroupAssignment, Enrollment, Student
from datetime import datetime

bp = Blueprint('groups', __name__)

@bp.route('/groups')
@login_required
@teacher_required
def groups_hub():
    """Main groups hub for teachers."""
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Get classes for the current teacher/admin
    if is_admin():
        classes = Class.query.all()
    else:
        if teacher is None:
            classes = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    # Get all groups for these classes
    all_groups = []
    for class_obj in classes:
        groups = StudentGroup.query.filter_by(class_id=class_obj.id, is_active=True).all()
        for group in groups:
            # Count members
            member_count = StudentGroupMember.query.filter_by(group_id=group.id).count()
            group.member_count = member_count
            group.class_name = class_obj.class_name
            all_groups.append(group)
    
    return render_template('teachers/teacher_groups_hub.html',
                         classes=classes,
                         groups=all_groups)

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
    
    # Add member info to each group
    for group in groups:
        members = StudentGroupMember.query.filter_by(group_id=group.id).all()
        group.members_list = [m.student for m in members if m.student]
        group.member_count = len(group.members_list)
    
    # Get enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [e.student for e in enrollments if e.student]
    
    return render_template('teachers/teacher_class_groups.html',
                         class_item=class_obj,
                         groups=groups,
                         students=students)

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

@bp.route('/groups/<int:group_id>/add-member', methods=['POST'])
@login_required
@teacher_required
def add_member(group_id):
    """Add a student to a group."""
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check authorization
    if not is_authorized_for_class(group.class_info):
        flash("You are not authorized to modify this group.", "danger")
        return redirect(url_for('teacher.groups.groups_hub'))
    
    student_id = request.form.get('student_id', type=int)
    is_leader = request.form.get('is_leader') == 'on'
    
    if not student_id:
        flash("Please select a student.", "danger")
        return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))
    
    # Check if already a member
    existing = StudentGroupMember.query.filter_by(group_id=group_id, student_id=student_id).first()
    if existing:
        flash("Student is already in this group.", "warning")
        return redirect(url_for('teacher.groups.class_groups', class_id=group.class_id))
    
    try:
        new_member = StudentGroupMember(
            group_id=group_id,
            student_id=student_id,
            is_leader=is_leader
        )
        db.session.add(new_member)
        db.session.commit()
        
        flash("Student added to group successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding student: {str(e)}", "danger")
    
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

