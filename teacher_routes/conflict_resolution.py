"""
Conflict Resolution routes for teachers - standalone module removed from communications.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin
from models import (db, Class, Student, Enrollment, GroupConflict, ConflictResolution, 
                    ConflictParticipant, GroupAssignment, StudentGroup)
from datetime import datetime
import json

bp = Blueprint('conflict_resolution', __name__)

# Redirect old URL pattern to new one for backwards compatibility
@bp.route('/conflicts/class/<int:class_id>')
@login_required
@teacher_required
def redirect_old_conflicts(class_id):
    """Redirect old URL pattern to new one."""
    return redirect(url_for('teacher.conflict_resolution.class_conflicts', class_id=class_id))

@bp.route('/class/<int:class_id>/conflict-resolution')
@login_required
@teacher_required
def class_conflicts(class_id):
    """View conflicts for a specific class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_id))
    
    # Get all conflicts for this class
    conflicts = GroupConflict.query.join(GroupAssignment).filter(
        GroupAssignment.class_id == class_id
    ).order_by(GroupConflict.reported_at.desc()).all()
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    # Calculate statistics
    total_conflicts = len(conflicts)
    pending = len([c for c in conflicts if c.status == 'open'])
    in_progress = len([c for c in conflicts if c.status == 'in_progress'])
    resolved = len([c for c in conflicts if c.status == 'resolved'])
    
    return render_template('teachers/teacher_class_conflicts.html',
                         class_obj=class_obj,
                         conflicts=conflicts,
                         students=students,
                         total_conflicts=total_conflicts,
                         pending=pending,
                         in_progress=in_progress,
                         resolved=resolved)

@bp.route('/conflict/<int:conflict_id>')
@login_required
@teacher_required
def view_conflict(conflict_id):
    """View a specific conflict."""
    teacher = get_teacher_or_admin()
    conflict = GroupConflict.query.get_or_404(conflict_id)
    class_obj = Class.query.get_or_404(conflict.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this conflict.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    # Get resolution steps
    resolution_steps = ConflictResolution.query.filter_by(conflict_id=conflict_id).order_by(ConflictResolution.implemented_at.asc()).all()
    
    # Get participants
    participants = ConflictParticipant.query.filter_by(conflict_id=conflict_id).all()
    
    return render_template('teachers/teacher_view_conflict.html',
                         conflict=conflict,
                         class_obj=class_obj,
                         resolution_steps=resolution_steps,
                         participants=participants)

@bp.route('/conflict/<int:conflict_id>/resolve', methods=['GET', 'POST'])
@login_required
@teacher_required
def resolve_conflict(conflict_id):
    """Resolve a conflict."""
    teacher = get_teacher_or_admin()
    conflict = GroupConflict.query.get_or_404(conflict_id)
    class_obj = Class.query.get_or_404(conflict.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this conflict.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    if request.method == 'POST':
        try:
            resolution_notes = request.form.get('resolution_notes')
            new_status = request.form.get('status')
            
            # Update conflict status
            conflict.status = new_status
            conflict.resolution_notes = resolution_notes
            conflict.resolved_by = teacher.id
            
            if new_status == 'resolved':
                conflict.resolved_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Conflict resolution updated successfully!', 'success')
            return redirect(url_for('teacher.conflict_resolution.view_conflict', conflict_id=conflict_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating conflict resolution: {str(e)}', 'danger')
    
    return render_template('teachers/teacher_resolve_conflict.html',
                         conflict=conflict,
                         class_obj=class_obj)

@bp.route('/conflict/<int:conflict_id>/add-resolution-step', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_conflict_resolution_step(conflict_id):
    """Add a resolution step to a conflict."""
    teacher = get_teacher_or_admin()
    conflict = GroupConflict.query.get_or_404(conflict_id)
    class_obj = Class.query.get_or_404(conflict.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this conflict.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    if request.method == 'POST':
        try:
            resolution_step = request.form.get('resolution_step')
            step_description = request.form.get('step_description')
            step_type = request.form.get('step_type')
            outcome = request.form.get('outcome')
            follow_up_date = request.form.get('follow_up_date')
            follow_up_notes = request.form.get('follow_up_notes')
            
            if not all([resolution_step, step_description, step_type]):
                flash('Resolution step, description, and type are required.', 'danger')
                return render_template('teachers/teacher_add_conflict_resolution_step.html',
                                     conflict=conflict,
                                     class_obj=class_obj)
            
            # Parse follow-up date if provided
            follow_up_datetime = None
            if follow_up_date:
                try:
                    follow_up_datetime = datetime.strptime(follow_up_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid follow-up date format.', 'danger')
                    return render_template('teachers/teacher_add_conflict_resolution_step.html',
                                         conflict=conflict,
                                         class_obj=class_obj)
            
            # Create resolution step
            resolution = ConflictResolution(
                conflict_id=conflict_id,
                resolution_step=resolution_step,
                step_description=step_description,
                step_type=step_type,
                outcome=outcome or 'pending',
                follow_up_date=follow_up_datetime,
                follow_up_notes=follow_up_notes,
                implemented_by=teacher.id,
                implemented_at=datetime.utcnow()
            )
            
            db.session.add(resolution)
            db.session.commit()
            
            flash('Resolution step added successfully!', 'success')
            return redirect(url_for('teacher.conflict_resolution.view_conflict', conflict_id=conflict_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding resolution step: {str(e)}', 'danger')
    
    return render_template('teachers/teacher_add_conflict_resolution_step.html',
                         conflict=conflict,
                         class_obj=class_obj)

@bp.route('/conflict/<int:conflict_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_conflict(conflict_id):
    """Delete a conflict."""
    teacher = get_teacher_or_admin()
    conflict = GroupConflict.query.get_or_404(conflict_id)
    class_obj = Class.query.get_or_404(conflict.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this conflict.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    try:
        # Delete associated resolution steps and participants first
        ConflictResolution.query.filter_by(conflict_id=conflict_id).delete()
        ConflictParticipant.query.filter_by(conflict_id=conflict_id).delete()
        
        # Delete the conflict
        db.session.delete(conflict)
        db.session.commit()
        
        flash('Conflict deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting conflict: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.conflict_resolution.class_conflicts', class_id=class_obj.id))

