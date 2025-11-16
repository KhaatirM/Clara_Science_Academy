"""
360° Feedback routes for teachers - standalone module removed from communications.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin
from models import (db, Class, Student, Enrollment, Feedback360, Feedback360Response, 
                    Feedback360Criteria, TeacherStaff)
from datetime import datetime
import json

bp = Blueprint('feedback360', __name__)

# Redirect old URL pattern to new one for backwards compatibility
@bp.route('/feedback360/class/<int:class_id>')
@login_required
@teacher_required
def redirect_old_feedback360(class_id):
    """Redirect old URL pattern to new one."""
    return redirect(url_for('teacher.feedback360.class_feedback360', class_id=class_id))

@bp.route('/class/<int:class_id>/360-feedback')
@login_required
@teacher_required
def class_feedback360(class_id):
    """View 360° feedback sessions for a specific class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_id))
    
    # Get all 360-degree feedback sessions for this class
    feedback_sessions = Feedback360.query.filter_by(class_id=class_id).order_by(Feedback360.created_at.desc()).all()
    
    # Get enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [e.student for e in enrollments if e.student]
    
    # Calculate statistics
    total_sessions = len(feedback_sessions)
    active_sessions = len([s for s in feedback_sessions if s.is_active])
    total_responses = sum(len(s.responses) for s in feedback_sessions)
    
    return render_template('teachers/teacher_class_360_feedback.html',
                         class_obj=class_obj,
                         feedback_sessions=feedback_sessions,
                         students=students,
                         total_sessions=total_sessions,
                         active_sessions=active_sessions,
                         total_responses=total_responses)

@bp.route('/class/<int:class_id>/360-feedback/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_360_feedback(class_id):
    """Create a new 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_id))
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            target_student_id = request.form.get('target_student_id')
            feedback_type = request.form.get('feedback_type')
            due_date = request.form.get('due_date')
            
            if not all([title, target_student_id, feedback_type]):
                flash('Title, target student, and feedback type are required.', 'danger')
                return render_template('teachers/teacher_create_360_feedback.html',
                                     class_obj=class_obj,
                                     students=students)
            
            # Parse due date if provided
            due_datetime = None
            if due_date:
                try:
                    due_datetime = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid due date format.', 'danger')
                    return render_template('teachers/teacher_create_360_feedback.html',
                                         class_obj=class_obj,
                                         students=students)
            
            # Create feedback session
            feedback_session = Feedback360(
                title=title,
                description=description,
                class_id=class_id,
                target_student_id=target_student_id,
                feedback_type=feedback_type,
                due_date=due_datetime,
                created_by=teacher.id
            )
            
            db.session.add(feedback_session)
            db.session.commit()
            
            flash('360-degree feedback session created successfully!', 'success')
            return redirect(url_for('teacher.feedback360.view_360_feedback', session_id=feedback_session.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating feedback session: {str(e)}', 'danger')
    
    return render_template('teachers/teacher_create_360_feedback.html',
                         class_obj=class_obj,
                         students=students)

@bp.route('/360-feedback/<int:session_id>')
@login_required
@teacher_required
def view_360_feedback(session_id):
    """View a specific 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    feedback_session = Feedback360.query.get_or_404(session_id)
    class_obj = Class.query.get_or_404(feedback_session.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this feedback session.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    # Get all responses for this session
    responses = Feedback360Response.query.filter_by(feedback360_id=session_id).all()
    
    # Get criteria for this session
    criteria = Feedback360Criteria.query.filter_by(feedback360_id=session_id).order_by(Feedback360Criteria.order_index).all()
    
    # Get students in the class for potential respondents
    enrollments = Enrollment.query.filter_by(class_id=feedback_session.class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    return render_template('teachers/teacher_view_360_feedback.html',
                         feedback_session=feedback_session,
                         class_obj=class_obj,
                         responses=responses,
                         criteria=criteria,
                         students=students)

@bp.route('/360-feedback/<int:session_id>/criteria/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_360_feedback_criteria(session_id):
    """Create criteria for a 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    feedback_session = Feedback360.query.get_or_404(session_id)
    class_obj = Class.query.get_or_404(feedback_session.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this feedback session.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    if request.method == 'POST':
        try:
            criteria_name = request.form.get('criteria_name')
            criteria_description = request.form.get('criteria_description')
            criteria_type = request.form.get('criteria_type')
            scale_min = request.form.get('scale_min', 1)
            scale_max = request.form.get('scale_max', 5)
            is_required = request.form.get('is_required') == 'on'
            order_index = request.form.get('order_index', 0)
            
            if not criteria_name:
                flash('Criteria name is required.', 'danger')
                return render_template('teachers/teacher_create_360_feedback_criteria.html',
                                     feedback_session=feedback_session,
                                     class_obj=class_obj)
            
            # Create criteria
            criteria = Feedback360Criteria(
                feedback360_id=session_id,
                criteria_name=criteria_name,
                criteria_description=criteria_description,
                criteria_type=criteria_type,
                scale_min=int(scale_min),
                scale_max=int(scale_max),
                is_required=is_required,
                order_index=int(order_index)
            )
            
            db.session.add(criteria)
            db.session.commit()
            
            flash('Feedback criteria created successfully!', 'success')
            return redirect(url_for('teacher.feedback360.view_360_feedback', session_id=session_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating criteria: {str(e)}', 'danger')
    
    return render_template('teachers/teacher_create_360_feedback_criteria.html',
                         feedback_session=feedback_session,
                         class_obj=class_obj)

@bp.route('/360-feedback/<int:session_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_360_feedback(session_id):
    """Delete a 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    feedback_session = Feedback360.query.get_or_404(session_id)
    class_obj = Class.query.get_or_404(feedback_session.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this feedback session.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    try:
        # Delete all responses and criteria first
        Feedback360Response.query.filter_by(feedback360_id=session_id).delete()
        Feedback360Criteria.query.filter_by(feedback360_id=session_id).delete()
        
        # Delete the session
        db.session.delete(feedback_session)
        db.session.commit()
        
        flash('360-degree feedback session deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting feedback session: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.feedback360.class_feedback360', class_id=class_obj.id))

@bp.route('/360-feedback/<int:session_id>/toggle', methods=['POST'])
@login_required
@teacher_required
def toggle_360_feedback(session_id):
    """Toggle active status of a 360-degree feedback session."""
    teacher = get_teacher_or_admin()
    feedback_session = Feedback360.query.get_or_404(session_id)
    class_obj = Class.query.get_or_404(feedback_session.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this feedback session.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    try:
        feedback_session.is_active = not feedback_session.is_active
        db.session.commit()
        
        status = 'activated' if feedback_session.is_active else 'deactivated'
        flash(f'360-degree feedback session {status} successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error toggling feedback session: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.feedback360.view_360_feedback', session_id=session_id))

