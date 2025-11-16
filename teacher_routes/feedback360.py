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

@bp.route('/feedback360')
@login_required
@teacher_required
def feedback360_hub():
    """Main 360° Feedback hub for teachers - shows all classes with feedback sessions."""
    teacher = get_teacher_or_admin()
    
    # Get all classes for this teacher
    if is_admin():
        classes = Class.query.all()
    else:
        if teacher is None:
            classes = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    # Get feedback session counts for each class
    class_data = []
    for class_obj in classes:
        session_count = Feedback360.query.filter_by(class_id=class_obj.id).count()
        active_count = Feedback360.query.filter_by(class_id=class_obj.id, is_active=True).count()
        
        # Get enrolled students count
        student_count = Enrollment.query.filter_by(class_id=class_obj.id, is_active=True).count()
        
        class_data.append({
            'class': class_obj,
            'session_count': session_count,
            'active_count': active_count,
            'student_count': student_count
        })
    
    return render_template('teachers/feedback360_hub.html',
                         classes=class_data)

@bp.route('/feedback360/class/<int:class_id>')
@login_required
@teacher_required
def class_feedback360(class_id):
    """View 360° feedback sessions for a specific class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.feedback360.feedback360_hub'))
    
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

