"""
Communications routes for teachers - includes 360° Feedback, Reflection Journals, and Conflict Resolution.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (db, Message, Announcement, Notification, Class, Student, Enrollment,
                    Feedback360, Feedback360Response, ReflectionJournal, GroupConflict, 
                    ConflictResolution, StudentGroup)
from datetime import datetime

bp = Blueprint('communications', __name__)

@bp.route('/communications')
@login_required
@teacher_required
def communications_hub():
    """Main communications hub for teachers."""
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
    
    return render_template('teachers/teacher_communications_hub.html', classes=classes)

@bp.route('/feedback360/class/<int:class_id>')
@login_required
@teacher_required
def class_feedback360(class_id):
    """View 360° feedback sessions for a class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view feedback for this class.", "danger")
        return redirect(url_for('teacher.communications.communications_hub'))
    
    # Get feedback sessions for this class
    feedback_sessions = Feedback360.query.filter_by(class_id=class_id).all()
    
    # Get enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [e.student for e in enrollments if e.student]
    
    return render_template('teachers/teacher_feedback360.html',
                         class_item=class_obj,
                         feedback_sessions=feedback_sessions,
                         students=students)

@bp.route('/journals/class/<int:class_id>')
@login_required
@teacher_required
def class_journals(class_id):
    """View reflection journals for a class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view journals for this class.", "danger")
        return redirect(url_for('teacher.communications.communications_hub'))
    
    # Get student groups for this class
    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
    
    # Get journals
    all_journals = []
    for group in groups:
        journals = ReflectionJournal.query.filter_by(group_id=group.id).all()
        for journal in journals:
            journal.group_name = group.name
            all_journals.append(journal)
    
    return render_template('teachers/teacher_journals.html',
                         class_item=class_obj,
                         journals=all_journals)

@bp.route('/conflicts/class/<int:class_id>')
@login_required
@teacher_required
def class_conflicts(class_id):
    """View and manage conflicts for a class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view conflicts for this class.", "danger")
        return redirect(url_for('teacher.communications.communications_hub'))
    
    # Get groups for this class
    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
    group_ids = [g.id for g in groups]
    
    # Get conflicts
    conflicts = GroupConflict.query.filter(GroupConflict.group_id.in_(group_ids)).all()
    
    # Add group names
    for conflict in conflicts:
        group = next((g for g in groups if g.id == conflict.group_id), None)
        conflict.group_name = group.name if group else "Unknown"
    
    return render_template('teachers/teacher_conflicts.html',
                         class_item=class_obj,
                         conflicts=conflicts)

