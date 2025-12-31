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
    from shared_communications import get_user_channels, get_direct_messages, get_user_announcements, ensure_class_channel_exists
    from models import Class, Enrollment, MessageGroup, MessageGroupMember, Message
    
    # Get teacher's classes
    teacher = get_teacher_or_admin()
    if teacher and hasattr(teacher, 'id'):
        classes = Class.query.filter_by(teacher_id=teacher.id, is_active=True).all()
    elif is_admin():
        classes = Class.query.filter_by(is_active=True).all()
    else:
        classes = []
    
    # Ensure channels exist for classes
    for class_obj in classes:
        ensure_class_channel_exists(class_obj.id)
    
    # Get channels (teachers don't see student groups)
    class_channels = get_user_channels(current_user.id, current_user.role)
    # Teachers cannot see student DMs or student groups
    direct_messages = get_direct_messages(current_user.id, current_user.role)
    announcements = get_user_announcements(current_user.id, current_user.role)
    unread_announcements = len([a for a in announcements if not a.get('read', False)])
    
    # Get staff channels
    staff_channels = []
    staff_groups = MessageGroup.query.filter_by(
        group_type='staff',
        is_active=True
    ).all()
    for group in staff_groups:
        member = MessageGroupMember.query.filter_by(
            group_id=group.id,
            user_id=current_user.id
        ).first()
        if member or is_admin():
            unread = Message.query.filter(
                Message.group_id == group.id,
                Message.sender_id != current_user.id,
                Message.is_read == False
            ).count()
            staff_channels.append({
                'id': group.id,
                'name': group.name,
                'type': 'staff',
                'unread_count': unread
            })
    
    return render_template('shared/communications_hub.html',
                         class_channels=class_channels,
                         direct_messages=direct_messages,
                         announcements=announcements,
                         unread_announcements_count=unread_announcements,
                         available_classes=classes,
                         active_channel_id=None,
                         active_view=None,
                         staff_channels=staff_channels,
                         student_groups=[])  # Teachers don't have student groups

# 360° Feedback routes have been moved to teacher_routes/feedback360.py
# The route is now handled by teacher.feedback360.class_feedback360

# Reflection Journals routes have been moved to teacher_routes/reflection_journals.py
# The route is now handled by teacher.reflection_journals.class_reflection_journals

# Conflict Resolution routes have been moved to teacher_routes/conflict_resolution.py
# The route is now handled by teacher.conflict_resolution.class_conflicts

