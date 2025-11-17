"""
Communications routes for teachers - includes 360° Feedback, Reflection Journals, and Conflict Resolution.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (db, Message, Announcement, Notification, Class, Student, Enrollment,
                    Feedback360, Feedback360Response, StudentGroup)
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

# Conflict Resolution routes have been moved to teacher_routes/conflict_resolution.py
# The route is now handled by teacher.conflict_resolution.class_conflicts

