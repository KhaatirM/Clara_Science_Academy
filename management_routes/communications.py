"""
Communications management routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import management_required
from models import db, Message, Announcement

bp = Blueprint('communications', __name__)

@bp.route('/communications')
@login_required
@management_required
def communications_hub():
    """Main communications hub for management."""
    from shared_communications import get_user_channels, get_direct_messages, get_user_announcements, ensure_class_channel_exists, get_dm_conversations
    from models import Class
    
    # Get all classes for admins
    classes = Class.query.filter_by(is_active=True).all()
    
    # Ensure channels exist
    for class_obj in classes:
        ensure_class_channel_exists(class_obj.id)
    
    # Get channels
    class_channels = get_user_channels(current_user.id, current_user.role)
    # Directors/Admins can see all DMs (including student DMs for monitoring)
    direct_messages = get_direct_messages(current_user.id, current_user.role)
    # Get DM conversations for sidebar injection
    dm_conversations = get_dm_conversations(current_user.id, current_user.role)
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
        if member:
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
                         dm_conversations=dm_conversations,
                         announcements=announcements,
                         unread_announcements_count=unread_announcements,
                         available_classes=classes,
                         active_channel_id=None,
                         active_view='hub',
                         active_tab='hub',
                         staff_channels=staff_channels,
                         student_groups=[])  # Management users don't have student groups

# Placeholder for communications management routes
# This module will contain all communications management functionality
# from the original managementroutes.py file



