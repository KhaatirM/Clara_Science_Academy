"""
Communications routes for teachers - includes 360° Feedback, Reflection Journals, and Conflict Resolution.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (db, Message, Announcement, Notification, Class, Student, Enrollment,
                    Feedback360, Feedback360Response, GroupConflict, 
                    ConflictResolution, StudentGroup)
from datetime import datetime

bp = Blueprint('communications', __name__)

@bp.route('/communications')
@login_required
@teacher_required
def communications_hub():
    """Main communications hub for teachers."""
    flash("Communications features are currently under development. Check back soon!", "info")
    return redirect(url_for('teacher.dashboard.teacher_dashboard'))

# 360° Feedback routes have been moved to teacher_routes/feedback360.py
# The route is now handled by teacher.feedback360.class_feedback360

# Reflection Journals routes have been moved to teacher_routes/reflection_journals.py
# The route is now handled by teacher.reflection_journals.class_reflection_journals

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

