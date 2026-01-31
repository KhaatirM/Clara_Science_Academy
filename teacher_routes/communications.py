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
    # Get all messages for the teacher (both sent and received)
    messages = Message.query.filter(
        (Message.recipient_id == current_user.id) |
        (Message.sender_id == current_user.id)
    ).order_by(Message.created_at.desc()).limit(50).all()
    
    # Get user's groups
    from models import MessageGroupMember, MessageGroup
    user_groups = MessageGroupMember.query.filter_by(user_id=current_user.id).all()
    groups = [mg.group for mg in user_groups if mg.group and mg.group.is_active]
    
    # Get announcements
    # Teachers can see announcements for their classes or all announcements
    teacher = get_teacher_or_admin()
    class_ids = []
    if teacher and not is_admin():
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in classes]
    
    if is_admin():
        announcements = Announcement.query.order_by(Announcement.timestamp.desc()).limit(20).all()
    else:
        announcements = Announcement.query.filter(
            (Announcement.target_group.in_(['all', 'all_teachers', 'all_staff'])) |
            ((Announcement.target_group == 'class') & (Announcement.class_id.in_(class_ids)))
        ).order_by(Announcement.timestamp.desc()).limit(20).all()
    
    return render_template('teachers/teacher_communications.html',
                         messages=messages,
                         groups=groups,
                         announcements=announcements,
                         teacher=teacher)

# 360° Feedback routes have been moved to teacher_routes/feedback360.py
# The route is now handled by teacher.feedback360.class_feedback360

# Reflection Journals routes have been moved to teacher_routes/reflection_journals.py
# The route is now handled by teacher.reflection_journals.class_reflection_journals

# Conflict Resolution routes have been moved to teacher_routes/conflict_resolution.py
# The route is now handled by teacher.conflict_resolution.class_conflicts

@bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
@teacher_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    from flask import request, abort
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    
    flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('teacher.dashboard.teacher_dashboard'))