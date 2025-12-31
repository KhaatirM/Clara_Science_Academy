"""
API endpoints for communications hub functionality.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import (
    db, Message, MessageGroup, MessageGroupMember, Announcement,
    Class, Enrollment, Student, TeacherStaff, User, Notification, MessageReaction
)
from datetime import datetime
from sqlalchemy import or_, and_
from shared_communications import (
    get_user_channels, get_direct_messages, get_user_announcements,
    ensure_class_channel_exists
)
from communications_helpers import get_user_full_name

api_bp = Blueprint('communications_api', __name__)

@api_bp.route('/communications/api/channel/<int:channel_id>/messages')
@login_required
def get_channel_messages(channel_id):
    """Get messages for a channel."""
    try:
        # Verify user has access to this channel
        group = MessageGroup.query.get_or_404(channel_id)
        member = MessageGroupMember.query.filter_by(
            group_id=channel_id,
            user_id=current_user.id
        ).first()
        
        # Teachers cannot access student-created groups
        if group.group_type == 'student' and current_user.role != 'Student' and current_user.role not in ['Director', 'School Administrator', 'Tech', 'IT Support']:
            return jsonify({'success': False, 'message': 'Access denied: Teachers cannot access student groups'}), 403
        
        if not member and group.created_by != current_user.id:
            # Check if user is teacher/admin of the class
            if group.class_id:
                class_obj = Class.query.get(group.class_id)
                if class_obj:
                    if current_user.role in ['Director', 'School Administrator']:
                        pass  # Admins can access
                    elif 'Teacher' in current_user.role and class_obj.teacher and class_obj.teacher.user_id == current_user.id:
                        pass  # Teacher can access
                    else:
                        return jsonify({'success': False, 'message': 'Access denied'}), 403
                else:
                    return jsonify({'success': False, 'message': 'Channel not found'}), 404
            elif group.group_type == 'student':
                # Student groups - only students and tech can access
                if current_user.role != 'Student' and current_user.role not in ['Director', 'School Administrator', 'Tech', 'IT Support']:
                    return jsonify({'success': False, 'message': 'Access denied: Only students can access student groups'}), 403
            else:
                return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get messages
        messages = Message.query.filter_by(
            group_id=channel_id
        ).order_by(Message.created_at.asc()).limit(100).all()
        
        # Mark as read
        Message.query.filter_by(
            group_id=channel_id,
            recipient_id=current_user.id,
            is_read=False
        ).update({'is_read': True, 'read_at': datetime.utcnow()})
        db.session.commit()
        
        # Get participants
        members = MessageGroupMember.query.filter_by(group_id=channel_id).all()
        participants = []
        for mem in members:
            user = User.query.get(mem.user_id)
            if user:
                participants.append({
                    'id': user.id,
                    'name': get_user_full_name(user)
                })
        
        # Get reactions for each message
        message_data = []
        for msg in messages:
            reactions = MessageReaction.query.filter_by(message_id=msg.id).all()
            reaction_counts = {}
            user_reactions = []
            for reaction in reactions:
                emoji = reaction.emoji
                if emoji not in reaction_counts:
                    reaction_counts[emoji] = 0
                reaction_counts[emoji] += 1
                if reaction.user_id == current_user.id:
                    user_reactions.append(emoji)
            
            # Get reply count safely
            reply_count = 0
            try:
                if hasattr(Message, 'parent_message_id'):
                    reply_count = Message.query.filter_by(parent_message_id=msg.id).count()
            except:
                pass
            
            message_data.append({
                'id': msg.id,
                'sender_id': msg.sender_id,
                'sender_name': get_user_full_name(msg.sender) if msg.sender else 'Unknown',
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'updated_at': msg.updated_at.isoformat() if msg.updated_at else msg.created_at.isoformat(),
                'is_edited': getattr(msg, 'is_edited', False),
                'parent_message_id': getattr(msg, 'parent_message_id', None),
                'reactions': reaction_counts if reaction_counts else {},
                'user_reactions': user_reactions,
                'reply_count': reply_count
            })
        
        return jsonify({
            'success': True,
            'messages': message_data,
            'channel_info': {
                'title': group.name,
                'description': group.description or ''
            },
            'participants': participants
        })
    except Exception as e:
        current_app.logger.error(f"Error getting channel messages: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/direct-message/<int:other_user_id>')
@login_required
def get_direct_message_conversation(other_user_id):
    """Get or create direct message conversation."""
    try:
        # Get messages between current user and other user (both direct type and NULL group_id for virtual DMs)
        messages = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.recipient_id == other_user_id),
                and_(Message.sender_id == other_user_id, Message.recipient_id == current_user.id)
            ),
            or_(
                Message.message_type == 'direct',
                and_(Message.group_id.is_(None), Message.recipient_id.isnot(None))
            )
        ).order_by(Message.created_at.asc()).limit(100).all()
        
        # Mark as read (both direct type and NULL group_id)
        Message.query.filter(
            Message.sender_id == other_user_id,
            Message.recipient_id == current_user.id,
            Message.is_read == False,
            or_(
                Message.message_type == 'direct',
                and_(Message.group_id.is_(None), Message.recipient_id.isnot(None))
            )
        ).update({'is_read': True, 'read_at': datetime.utcnow()})
        db.session.commit()
        
        other_user = User.query.get(other_user_id)
        
        # Get reactions for each message
        message_data = []
        for msg in messages:
            reactions = MessageReaction.query.filter_by(message_id=msg.id).all()
            reaction_counts = {}
            user_reactions = []
            for reaction in reactions:
                emoji = reaction.emoji
                if emoji not in reaction_counts:
                    reaction_counts[emoji] = 0
                reaction_counts[emoji] += 1
                if reaction.user_id == current_user.id:
                    user_reactions.append(emoji)
            
            # Get reply count safely
            reply_count = 0
            try:
                if hasattr(Message, 'parent_message_id'):
                    reply_count = Message.query.filter_by(parent_message_id=msg.id).count()
            except:
                pass
            
            message_data.append({
                'id': msg.id,
                'sender_id': msg.sender_id,
                'sender_name': get_user_full_name(msg.sender) if msg.sender else 'Unknown',
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'updated_at': msg.updated_at.isoformat() if msg.updated_at else msg.created_at.isoformat(),
                'is_edited': getattr(msg, 'is_edited', False),
                'parent_message_id': getattr(msg, 'parent_message_id', None),
                'reactions': reaction_counts if reaction_counts else {},
                'user_reactions': user_reactions,
                'reply_count': reply_count
            })
        
        return jsonify({
            'success': True,
            'messages': message_data,
            'other_user_id': other_user_id,
            'other_user_name': get_user_full_name(other_user) if other_user else 'Unknown'
        })
    except Exception as e:
        current_app.logger.error(f"Error getting DM conversation: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/announcements')
@login_required
def get_announcements_api():
    """Get announcements for current user."""
    try:
        announcements = get_user_announcements(current_user.id, current_user.role)
        return jsonify({
            'success': True,
            'announcements': announcements
        })
    except Exception as e:
        current_app.logger.error(f"Error getting announcements: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/send-message', methods=['POST'])
@login_required
def send_message_api():
    """Send a message."""
    try:
        data = request.get_json()
        channel_id = data.get('channel_id')
        channel_type = data.get('channel_type')
        content = data.get('content', '').strip()
        recipient_id = data.get('recipient_id')
        
        if not content:
            return jsonify({'success': False, 'message': 'Message content is required'}), 400
        
        if channel_type == 'direct':
            if not recipient_id:
                return jsonify({'success': False, 'message': 'Recipient is required'}), 400
            
            # Create direct message
            message = Message(
                sender_id=current_user.id,
                recipient_id=recipient_id,
                content=content,
                message_type='direct'
            )
            db.session.add(message)
            
            # Create notification
            notification = Notification(
                user_id=recipient_id,
                type='message',
                title='New Message',
                message=f"You received a message from {current_user.username}",
                link=f"/communications"
            )
            db.session.add(notification)
            
        elif channel_type in ['class', 'staff']:
            if not channel_id:
                return jsonify({'success': False, 'message': 'Channel ID is required'}), 400
            
            # Verify access
            member = MessageGroupMember.query.filter_by(
                group_id=channel_id,
                user_id=current_user.id
            ).first()
            
            if not member:
                group = MessageGroup.query.get(channel_id)
                if group and group.class_id:
                    class_obj = Class.query.get(group.class_id)
                    if class_obj:
                        if current_user.role in ['Director', 'School Administrator']:
                            pass
                        elif 'Teacher' in current_user.role and class_obj.teacher and class_obj.teacher.user and class_obj.teacher.user.id == current_user.id:
                            pass
                        else:
                            return jsonify({'success': False, 'message': 'Access denied'}), 403
                    else:
                        return jsonify({'success': False, 'message': 'Channel not found'}), 404
                else:
                    return jsonify({'success': False, 'message': 'Access denied'}), 403
            
            # Get the group to verify it exists
            group = MessageGroup.query.get(channel_id)
            if not group:
                return jsonify({'success': False, 'message': 'Channel not found'}), 404
            
            # For group messages, recipient_id is required by the model
            # We'll use sender_id as a placeholder since group messages don't have a single recipient
            # The actual recipients are all group members
            message = Message(
                sender_id=current_user.id,
                recipient_id=current_user.id,  # Placeholder - actual recipients are group members
                group_id=channel_id,
                content=content,
                message_type='group'
            )
            db.session.add(message)
            
            # Create notifications for all members except sender
            members = MessageGroupMember.query.filter_by(
                group_id=channel_id
            ).filter(MessageGroupMember.user_id != current_user.id).all()
            
            for mem in members:
                notification = Notification(
                    user_id=mem.user_id,
                    type='message',
                    title='New Message',
                    message=f"New message in {group.name if group else 'channel'}",
                    link=f"/communications"
                )
                db.session.add(notification)
        else:
            return jsonify({'success': False, 'message': 'Invalid channel type'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': message.id,
            'other_user_id': recipient_id if channel_type == 'direct' else None
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error sending message: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/create-announcement', methods=['POST'])
@login_required
def create_announcement():
    """Create a new announcement."""
    try:
        if current_user.role not in ['Director', 'School Administrator'] and 'Teacher' not in current_user.role:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        title = request.form.get('title', '').strip()
        message_text = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        is_important = request.form.get('is_important') == 'on'
        
        if not title or not message_text:
            return jsonify({'success': False, 'message': 'Title and message are required'}), 400
        
        # For teachers, validate they can only create announcements for their classes
        is_teacher = 'Teacher' in current_user.role and current_user.role not in ['Director', 'School Administrator']
        if is_teacher:
            # Teachers can only send to specific classes
            if target_group != 'class' or not class_id:
                return jsonify({'success': False, 'message': 'Teachers can only send announcements to specific classes'}), 400
            
            # Verify teacher teaches this class
            teacher = TeacherStaff.query.filter_by(user_id=current_user.id).first()
            if not teacher:
                return jsonify({'success': False, 'message': 'Teacher profile not found'}), 403
            
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return jsonify({'success': False, 'message': 'Class not found'}), 404
            
            if class_obj.teacher_id != teacher.id:
                return jsonify({'success': False, 'message': 'You can only send announcements to classes you teach'}), 403
        
        announcement = Announcement(
            title=title,
            message=message_text,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id if target_group == 'class' else None,
            is_important=is_important
        )
        db.session.add(announcement)
        db.session.commit()
        
        # Create notifications for target users
        if target_group == 'all_students':
            students = Student.query.all()
            for student in students:
                if student.user:
                    notification = Notification(
                        user_id=student.user.id,
                        type='announcement',
                        title=title,
                        message=message_text[:100],
                        link='/communications'
                    )
                    db.session.add(notification)
        elif target_group == 'class' and class_id:
            enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
            for enrollment in enrollments:
                if enrollment.student and enrollment.student.user:
                    notification = Notification(
                        user_id=enrollment.student.user.id,
                        type='announcement',
                        title=title,
                        message=message_text[:100],
                        link='/communications'
                    )
                    db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({'success': True, 'announcement_id': announcement.id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating announcement: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/edit-message/<int:message_id>', methods=['POST'])
@login_required
def edit_message(message_id):
    """Edit a message (only own messages)."""
    try:
        message = Message.query.get_or_404(message_id)
        
        # Verify user owns this message
        if message.sender_id != current_user.id:
            return jsonify({'success': False, 'message': 'You can only edit your own messages'}), 403
        
        data = request.get_json()
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return jsonify({'success': False, 'message': 'Message content is required'}), 400
        
        # Update message
        message.content = new_content
        message.is_edited = True
        message.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message_id': message.id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error editing message: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/react-message/<int:message_id>', methods=['POST'])
@login_required
def react_to_message(message_id):
    """Add or remove a reaction to a message."""
    try:
        message = Message.query.get_or_404(message_id)
        
        data = request.get_json()
        emoji = data.get('emoji', '').strip()
        
        if not emoji:
            return jsonify({'success': False, 'message': 'Emoji is required'}), 400
        
        # Check if reaction already exists
        existing_reaction = MessageReaction.query.filter_by(
            message_id=message_id,
            user_id=current_user.id,
            emoji=emoji
        ).first()
        
        if existing_reaction:
            # Remove reaction
            db.session.delete(existing_reaction)
            action = 'removed'
        else:
            # Add reaction
            reaction = MessageReaction(
                message_id=message_id,
                user_id=current_user.id,
                emoji=emoji
            )
            db.session.add(reaction)
            action = 'added'
        
        db.session.commit()
        
        # Get updated reaction counts
        reactions = MessageReaction.query.filter_by(message_id=message_id).all()
        reaction_counts = {}
        for reaction in reactions:
            emoji_key = reaction.emoji
            if emoji_key not in reaction_counts:
                reaction_counts[emoji_key] = 0
            reaction_counts[emoji_key] += 1
        
        return jsonify({
            'success': True,
            'action': action,
            'reactions': reaction_counts
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reacting to message: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/reply-message', methods=['POST'])
@login_required
def reply_to_message():
    """Reply to a message (create a threaded reply)."""
    try:
        data = request.get_json()
        parent_message_id = data.get('parent_message_id', type=int)
        content = data.get('content', '').strip()
        channel_id = data.get('channel_id')
        channel_type = data.get('channel_type')
        
        if not parent_message_id:
            return jsonify({'success': False, 'message': 'Parent message ID is required'}), 400
        
        if not content:
            return jsonify({'success': False, 'message': 'Message content is required'}), 400
        
        # Verify parent message exists
        parent_message = Message.query.get_or_404(parent_message_id)
        
        # Determine recipient_id and group_id based on parent message
        if parent_message.message_type == 'direct':
            # For direct messages, reply to the other person
            recipient_id = parent_message.sender_id if parent_message.sender_id != current_user.id else parent_message.recipient_id
            group_id = None
        else:
            # For group messages, use the same group
            recipient_id = current_user.id  # Placeholder
            group_id = parent_message.group_id
        
        # Create reply message
        reply = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            content=content,
            message_type=parent_message.message_type,
            group_id=group_id,
            parent_message_id=parent_message_id
        )
        db.session.add(reply)
        
        # Create notifications for parent message sender and group members
        if parent_message.message_type == 'direct':
            notification = Notification(
                user_id=parent_message.sender_id,
                type='message',
                title='New Reply',
                message=f"{get_user_full_name(current_user)} replied to your message",
                link='/communications'
            )
            db.session.add(notification)
        else:
            # Notify group members
            members = MessageGroupMember.query.filter_by(
                group_id=group_id
            ).filter(MessageGroupMember.user_id != current_user.id).all()
            
            for mem in members:
                notification = Notification(
                    user_id=mem.user_id,
                    type='message',
                    title='New Reply',
                    message=f"New reply in {parent_message.group.name if parent_message.group else 'channel'}",
                    link='/communications'
                )
                db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': reply.id,
            'parent_message_id': parent_message_id
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error replying to message: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/mute-student/<int:group_id>/<int:user_id>', methods=['POST'])
@login_required
def mute_student(group_id, user_id):
    """Mute a student in a channel for a specified duration (teachers only)."""
    try:
        # Check if user is a teacher
        is_teacher = 'Teacher' in current_user.role or current_user.role in ['Director', 'School Administrator']
        if not is_teacher:
            return jsonify({'success': False, 'message': 'Only teachers can mute students'}), 403
        
        # Get the group
        group = MessageGroup.query.get_or_404(group_id)
        
        # Verify teacher has access to this class channel
        if group.group_type == 'class' and group.class_id:
            class_obj = Class.query.get(group.class_id)
            if class_obj:
                teacher = TeacherStaff.query.filter_by(user_id=current_user.id).first()
                if teacher and class_obj.teacher_id != teacher.id and current_user.role not in ['Director', 'School Administrator']:
                    return jsonify({'success': False, 'message': 'You can only mute students in your own classes'}), 403
        
        # Get mute duration from request
        data = request.get_json() or {}
        duration_hours = data.get('duration_hours', 24)  # Default 24 hours
        
        # Calculate mute expiration
        from datetime import timedelta
        muted_until = datetime.utcnow() + timedelta(hours=duration_hours)
        
        # Get or create member record
        member = MessageGroupMember.query.filter_by(
            group_id=group_id,
            user_id=user_id
        ).first()
        
        if not member:
            member = MessageGroupMember(
                group_id=group_id,
                user_id=user_id,
                is_muted=True,
                muted_until=muted_until
            )
            db.session.add(member)
        else:
            member.is_muted = True
            member.muted_until = muted_until
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'muted_until': muted_until.isoformat(),
            'duration_hours': duration_hours
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error muting student: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/unmute-student/<int:group_id>/<int:user_id>', methods=['POST'])
@login_required
def unmute_student(group_id, user_id):
    """Unmute a student in a channel (teachers only)."""
    try:
        # Check if user is a teacher
        is_teacher = 'Teacher' in current_user.role or current_user.role in ['Director', 'School Administrator']
        if not is_teacher:
            return jsonify({'success': False, 'message': 'Only teachers can unmute students'}), 403
        
        # Get the group
        group = MessageGroup.query.get_or_404(group_id)
        
        # Verify teacher has access to this class channel
        if group.group_type == 'class' and group.class_id:
            class_obj = Class.query.get(group.class_id)
            if class_obj:
                teacher = TeacherStaff.query.filter_by(user_id=current_user.id).first()
                if teacher and class_obj.teacher_id != teacher.id and current_user.role not in ['Director', 'School Administrator']:
                    return jsonify({'success': False, 'message': 'You can only unmute students in your own classes'}), 403
        
        # Get member record
        member = MessageGroupMember.query.filter_by(
            group_id=group_id,
            user_id=user_id
        ).first()
        
        if member:
            member.is_muted = False
            member.muted_until = None
            db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unmuting student: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/delete-message/<int:message_id>', methods=['POST'])
@login_required
def delete_message(message_id):
    """Delete a message (teachers can delete any message in their class channels)."""
    try:
        message = Message.query.get_or_404(message_id)
        
        # Check if user is the sender (can always delete own messages)
        is_owner = message.sender_id == current_user.id
        
        # Check if user is a teacher with access to this channel
        is_teacher = 'Teacher' in current_user.role or current_user.role in ['Director', 'School Administrator']
        is_authorized = False
        
        if is_teacher and message.group_id:
            group = MessageGroup.query.get(message.group_id)
            if group and group.group_type == 'class' and group.class_id:
                class_obj = Class.query.get(group.class_id)
                if class_obj:
                    teacher = TeacherStaff.query.filter_by(user_id=current_user.id).first()
                    if teacher and class_obj.teacher_id == teacher.id:
                        is_authorized = True
                    elif current_user.role in ['Director', 'School Administrator']:
                        is_authorized = True
        
        if not is_owner and not is_authorized:
            return jsonify({'success': False, 'message': 'You do not have permission to delete this message'}), 403
        
        # Soft delete: mark as deleted instead of actually deleting
        # We'll add a deleted_at field or use a flag
        # For now, we'll actually delete it
        db.session.delete(message)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting message: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/available-students', methods=['GET'])
@login_required
def get_available_students():
    """Get list of students available for group creation (students only)."""
    try:
        if current_user.role != 'Student':
            return jsonify({'success': False, 'message': 'Only students can create groups'}), 403
        
        # Get current user's student record to exclude it
        current_student_id = current_user.student_id
        
        # Get all students that have a User account, excluding current user
        # Join with User to filter only students with accounts
        students = Student.query.join(User, Student.id == User.student_id).filter(
            User.role == 'Student',
            Student.id != current_student_id
        ).all()
        
        student_list = []
        for student in students:
            if student.user:
                student_list.append({
                    'id': student.user.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'username': student.user.username
                })
        
        return jsonify({
            'success': True,
            'students': student_list
        })
    except Exception as e:
        current_app.logger.error(f"Error getting available students: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/create-group', methods=['POST'])
@login_required
def create_student_group():
    """Create a new student group."""
    try:
        if current_user.role != 'Student':
            return jsonify({'success': False, 'message': 'Only students can create groups'}), 403
        
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        member_ids = data.get('member_ids', [])
        
        if not name:
            return jsonify({'success': False, 'message': 'Group name is required'}), 400
        
        # Create the group
        group = MessageGroup(
            name=name,
            description=description,
            group_type='student',
            created_by=current_user.id,
            is_active=True
        )
        db.session.add(group)
        db.session.flush()
        
        # Add creator as admin member
        creator_member = MessageGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.session.add(creator_member)
        
        # Add selected members
        for member_id in member_ids:
            if member_id != current_user.id:  # Don't add creator twice
                # Verify it's a student
                member_user = User.query.get(member_id)
                if member_user and member_user.role == 'Student':
                    member = MessageGroupMember(
                        group_id=group.id,
                        user_id=member_id,
                        is_admin=False
                    )
                    db.session.add(member)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'group_id': group.id,
            'message': 'Group created successfully'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating group: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/leave-group/<int:group_id>', methods=['POST'])
@login_required
def leave_group(group_id):
    """Leave a student-created group."""
    try:
        if current_user.role != 'Student':
            return jsonify({'success': False, 'message': 'Only students can leave groups'}), 403
        
        # Verify group exists and is a student group
        group = MessageGroup.query.get_or_404(group_id)
        if group.group_type != 'student':
            return jsonify({'success': False, 'message': 'You can only leave student-created groups'}), 403
        
        # Check if user is a member
        member = MessageGroupMember.query.filter_by(
            group_id=group_id,
            user_id=current_user.id
        ).first()
        
        if not member:
            return jsonify({'success': False, 'message': 'You are not a member of this group'}), 404
        
        # Prevent creators from leaving - they must delete the group instead
        if group.created_by == current_user.id:
            return jsonify({
                'success': False, 
                'message': 'Group creators cannot leave. Please delete the group instead if you want to remove it.'
            }), 403
        
        # Remove member
        db.session.delete(member)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'You have left the group'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error leaving group: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/communications/api/delete-group/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    """Delete a student-created group (only by creator)."""
    try:
        if current_user.role != 'Student':
            return jsonify({'success': False, 'message': 'Only students can delete groups'}), 403
        
        # Verify group exists and is a student group
        group = MessageGroup.query.get_or_404(group_id)
        if group.group_type != 'student':
            return jsonify({'success': False, 'message': 'You can only delete student-created groups'}), 403
        
        # Only creator can delete
        if group.created_by != current_user.id:
            return jsonify({'success': False, 'message': 'Only the group creator can delete the group'}), 403
        
        # Delete all messages in the group
        Message.query.filter_by(group_id=group_id).delete()
        
        # Delete all members
        MessageGroupMember.query.filter_by(group_id=group_id).delete()
        
        # Delete the group
        db.session.delete(group)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Group deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting group: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

