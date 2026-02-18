"""
Communications routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import (
    db, Message, MessageGroup, MessageGroupMember, Announcement, ScheduledAnnouncement,
    Notification, User, Class, StudentGroup, StudentGroupMember, Enrollment
)
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import json

bp = Blueprint('communications', __name__)


# ============================================================
# Route: /communications
# Function: communications
# ============================================================

@bp.route('/communications')
@login_required
@management_required
def communications():
    """Communications hub for management."""
    # Get all messages for the user
    messages = Message.query.filter(
        (Message.recipient_id == current_user.id) |
        (Message.sender_id == current_user.id)
    ).order_by(Message.created_at.desc()).limit(20).all()
    
    # Get user's groups
    user_groups = MessageGroupMember.query.filter_by(user_id=current_user.id).all()
    groups = [mg.group for mg in user_groups if mg.group and mg.group.is_active]
    
    # Get all announcements
    announcements = Announcement.query.order_by(Announcement.timestamp.desc()).limit(20).all()
    
    # Get scheduled announcements
    scheduled = ScheduledAnnouncement.query.filter_by(sender_id=current_user.id).order_by(ScheduledAnnouncement.scheduled_for.desc()).all()
    
    return render_template('management/management_communications.html',
                         messages=messages,
                         groups=groups,
                         announcements=announcements,
                         scheduled=scheduled,
                         section='communications',
                         active_tab='communications')




# ============================================================
# Route: /communications/messages
# Function: management_messages
# ============================================================

@bp.route('/communications/messages')
@login_required
@management_required
def management_messages():
    """View all messages for management."""
    # Get all messages for the admin
    messages = Message.query.filter(
        (Message.recipient_id == current_user.id) |
        (Message.sender_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    
    return render_template('management/management_messages.html',
                         messages=messages,
                         section='communications',
                         active_tab='messages')




# ============================================================
# Route: /communications/messages/send', methods=['GET', 'POST']
# Function: management_send_message
# ============================================================

@bp.route('/communications/messages/send', methods=['GET', 'POST'])
@login_required
@management_required
def management_send_message():
    """Send a new message."""
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id', type=int)
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        
        if not recipient_id or not subject or not content:
            flash('Recipient, subject, and content are required.', 'error')
            return redirect(url_for('management.management_send_message'))
        
        # Create message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            message_type='direct'
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Create notification for recipient
        notification = Notification(
            user_id=recipient_id,
            type='new_message',
            title=f'New message from {current_user.username}',
            message=subject,
            message_id=message.id
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('management.management_messages'))
    
    # Get all users for recipient selection
    users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('management/management_send_message.html',
                         users=users,
                         section='communications',
                         active_tab='messages')




# ============================================================
# Route: /communications/messages/<int:message_id>
# Function: management_view_message
# ============================================================

@bp.route('/communications/messages/<int:message_id>')
@login_required
@management_required
def management_view_message(message_id):
    """View a specific message."""
    message = Message.query.get_or_404(message_id)
    
    # Ensure the user is the sender or recipient
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        abort(403)
    
    # Mark as read if user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('management/management_view_message.html',
                         message=message,
                         section='communications',
                         active_tab='messages')




# ============================================================
# Route: /communications/messages/<int:message_id>/reply', methods=['POST']
# Function: management_reply_to_message
# ============================================================

@bp.route('/communications/messages/<int:message_id>/reply', methods=['POST'])
@login_required
@management_required
def management_reply_to_message(message_id):
    """Reply to a message."""
    original_message = Message.query.get_or_404(message_id)
    
    # Ensure the user is the sender or recipient
    if original_message.sender_id != current_user.id and original_message.recipient_id != current_user.id:
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Reply content is required.', 'error')
        return redirect(url_for('management.management_view_message', message_id=message_id))
    
    # Determine recipient (reply to the other person in the conversation)
    recipient_id = original_message.sender_id if original_message.recipient_id == current_user.id else original_message.recipient_id
    
    # Create reply message
    reply = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        subject=f'Re: {original_message.subject}',
        content=content,
        message_type='direct',
        parent_message_id=message_id
    )
    
    db.session.add(reply)
    db.session.commit()
    
    # Create notification for recipient
    notification = Notification(
        user_id=recipient_id,
        type='new_message',
        title=f'Reply from {current_user.username}',
        message=content[:100] + '...' if len(content) > 100 else content,
        message_id=reply.id
    )
    db.session.add(notification)
    db.session.commit()
    
    flash('Reply sent successfully!', 'success')
    return redirect(url_for('management.management_view_message', message_id=message_id))




# ============================================================
# Route: /communications/groups
# Function: management_groups
# ============================================================

@bp.route('/communications/groups')
@login_required
@management_required
def management_groups():
    """View and manage message groups."""
    # Get all groups
    groups = MessageGroup.query.filter_by(is_active=True).all()
    
    # Get user's group memberships
    memberships = MessageGroupMember.query.filter_by(user_id=current_user.id).all()
    
    return render_template('management/management_groups.html',
                         groups=groups,
                         memberships=memberships,
                         section='communications',
                         active_tab='groups')




# ============================================================
# Route: /communications/groups/create', methods=['GET', 'POST']
# Function: management_create_group
# ============================================================

@bp.route('/communications/groups/create', methods=['GET', 'POST'])
@login_required
@management_required
def management_create_group():
    """Create a new message group."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        member_ids = request.form.getlist('members')
        
        if not name:
            flash('Group name is required.', 'error')
            return redirect(url_for('management.management_create_group'))
        
        # Create group
        group = MessageGroup(
            name=name,
            description=description,
            created_by=current_user.id,
            is_active=True
        )
        db.session.add(group)
        db.session.flush()
        
        # Add creator as member
        creator_member = MessageGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            role='admin'
        )
        db.session.add(creator_member)
        
        # Add other members
        for member_id in member_ids:
            if int(member_id) != current_user.id:
                member = MessageGroupMember(
                    group_id=group.id,
                    user_id=int(member_id),
                    role='member'
                )
                db.session.add(member)
        
        db.session.commit()
        
        flash('Group created successfully!', 'success')
        return redirect(url_for('management.management_groups'))
    
    # Get all users for member selection
    users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('management/management_create_group.html',
                         users=users,
                         section='communications',
                         active_tab='groups')




# ============================================================
# Route: /communications/groups/<int:group_id>
# Function: management_view_group
# ============================================================

@bp.route('/communications/groups/<int:group_id>')
@login_required
@management_required
def management_view_group(group_id):
    """View a specific group and its messages."""
    group = MessageGroup.query.get_or_404(group_id)
    
    # Check if user is member of this group
    membership = MessageGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        abort(403)
    
    # Get group messages
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.created_at.desc()).all()
    
    # Get group members
    members = MessageGroupMember.query.filter_by(group_id=group_id).all()
    
    return render_template('management/management_view_group.html',
                         group=group,
                         messages=messages,
                         members=members,
                         membership=membership,
                         section='communications',
                         active_tab='groups')




# ============================================================
# Route: /communications/groups/<int:group_id>/send', methods=['POST']
# Function: management_send_group_message
# ============================================================

@bp.route('/communications/groups/<int:group_id>/send', methods=['POST'])
@login_required
@management_required
def management_send_group_message(group_id):
    """Send a message to a group."""
    group = MessageGroup.query.get_or_404(group_id)
    
    # Check if user is member of this group
    membership = MessageGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Message content is required.', 'error')
        return redirect(url_for('management.management_view_group', group_id=group_id))
    
    # Create group message
    message = Message(
        sender_id=current_user.id,
        content=content,
        message_type='group',
        group_id=group_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Create notifications for all group members except sender
    members = MessageGroupMember.query.filter_by(group_id=group_id).all()
    for member in members:
        if member.user_id != current_user.id and not member.is_muted:
            notification = Notification(
                user_id=member.user_id,
                type='group_message',
                title=f'New message in {group.name}',
                message=content[:100] + '...' if len(content) > 100 else content,
                message_id=message.id
            )
            db.session.add(notification)
    
    db.session.commit()
    
    flash('Message sent to group!', 'success')
    return redirect(url_for('management.management_view_group', group_id=group_id))




# ============================================================
# Route: /communications/announcements/create', methods=['GET', 'POST']
# Function: management_create_announcement
# ============================================================

@bp.route('/communications/announcements/create', methods=['GET', 'POST'])
@login_required
@management_required
def management_create_announcement():
    """Create a new announcement."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        is_important = request.form.get('is_important', type=bool)
        requires_confirmation = request.form.get('requires_confirmation', type=bool)
        rich_content = request.form.get('rich_content', '')
        
        if not title or not message:
            flash('Title and message are required.', 'error')
            return redirect(url_for('management.management_create_announcement'))
        
        # Create announcement
        announcement = Announcement(
            title=title,
            message=message,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id,
            is_important=is_important,
            requires_confirmation=requires_confirmation,
            rich_content=rich_content
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement created successfully!', 'success')
        return redirect(url_for('management.communications'))
    
    classes = Class.query.all()
    
    return render_template('management/management_create_announcement.html',
                         classes=classes,
                         section='communications',
                         active_tab='announcements')




# ============================================================
# Route: /communications/announcements/schedule', methods=['GET', 'POST']
# Function: management_schedule_announcement
# ============================================================

@bp.route('/communications/announcements/schedule', methods=['GET', 'POST'])
@login_required
@management_required
def management_schedule_announcement():
    """Schedule an announcement for future delivery."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        scheduled_for = request.form.get('scheduled_for')
        
        if not title or not message or not scheduled_for:
            flash('Title, message, and scheduled time are required.', 'error')
            return redirect(url_for('management.management_schedule_announcement'))
        
        try:
            scheduled_datetime = datetime.strptime(scheduled_for, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'error')
            return redirect(url_for('management.management_schedule_announcement'))
        
        # Create scheduled announcement
        scheduled = ScheduledAnnouncement(
            title=title,
            message=message,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id,
            scheduled_for=scheduled_datetime
        )
        
        db.session.add(scheduled)
        db.session.commit()
        
        flash('Announcement scheduled successfully!', 'success')
        return redirect(url_for('management.communications'))
    
    classes = Class.query.all()
    
    return render_template('management/management_schedule_announcement.html',
                         classes=classes,
                         section='communications',
                         active_tab='announcements')




# ============================================================
# Route: /communications/notifications/mark-read/<int:notification_id>', methods=['POST']
# Function: management_mark_notification_read
# ============================================================

@bp.route('/communications/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
@management_required
def management_mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    
    flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('management.communications'))




# ============================================================
# Route: /communications/messages/mark-read/<int:message_id>', methods=['POST']
# Function: management_mark_message_read
# ============================================================

@bp.route('/communications/messages/mark-read/<int:message_id>', methods=['POST'])
@login_required
@management_required
def management_mark_message_read(message_id):
    """Mark a message as read."""
    message = Message.query.get_or_404(message_id)
    
    # Ensure the message belongs to the current user
    if message.recipient_id != current_user.id:
        abort(403)
    
    message.is_read = True
    message.read_at = datetime.utcnow()
    db.session.commit()
    
    flash('Message marked as read.', 'success')
    return redirect(request.referrer or url_for('management.management_messages'))




# ============================================================
# Route: /group/<int:group_id>/manage', methods=['GET', 'POST']
# Function: admin_manage_group
# ============================================================

@bp.route('/group/<int:group_id>/manage', methods=['GET', 'POST'])
@login_required
@management_required
def admin_manage_group(group_id):
    """Manage students in a specific group (Administrator access)."""
    try:
        group = StudentGroup.query.get_or_404(group_id)
        class_obj = group.class_info
        
        # Get current group members
        current_members = StudentGroupMember.query.filter_by(group_id=group_id).all()
        current_member_ids = [member.student_id for member in current_members]
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=class_obj.id, is_active=True).all()
        enrolled_students = [enrollment.student for enrollment in enrollments]
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add_student':
                # Handle multiple student_ids (from checkboxes) or single student_id
                student_ids = request.form.getlist('student_ids')
                if not student_ids:
                    student_id = request.form.get('student_id')
                    if student_id:
                        student_ids = [student_id]
                
                leader_id = request.form.get('leader_id', type=int)
                
                if student_ids:
                    added_count = 0
                    skipped_count = 0
                    
                    for student_id_str in student_ids:
                        student_id = int(student_id_str)
                        
                        # Check if student is already in the group
                        existing_member = StudentGroupMember.query.filter_by(
                            group_id=group_id,
                            student_id=student_id
                        ).first()
                        
                        if not existing_member:
                            # Determine if this student should be leader
                            is_leader = (leader_id == student_id)
                            
                            member = StudentGroupMember(
                                group_id=group_id,
                                student_id=student_id,
                                is_leader=is_leader
                            )
                            db.session.add(member)
                            added_count += 1
                        else:
                            # Update leader status if this student is the selected leader
                            if leader_id == student_id and not existing_member.is_leader:
                                existing_member.is_leader = True
                                added_count += 1
                            else:
                                skipped_count += 1
                    
                    # If a leader was selected, ensure only one leader exists
                    if leader_id:
                        StudentGroupMember.query.filter_by(group_id=group_id).filter(
                            StudentGroupMember.student_id != leader_id
                        ).update({'is_leader': False}, synchronize_session=False)
                    
                    db.session.commit()
                    
                    if added_count > 0:
                        flash(f'{added_count} student(s) added to group successfully!', 'success')
                    if skipped_count > 0:
                        flash(f'{skipped_count} student(s) were already in the group.', 'info')
                    
                    return redirect(url_for('management.admin_class_groups', class_id=class_obj.id))
                else:
                    flash('Please select at least one student.', 'warning')
            
            elif action == 'remove_student':
                student_id = request.form.get('student_id')
                if student_id:
                    member = StudentGroupMember.query.filter_by(
                        group_id=group_id,
                        student_id=int(student_id)
                    ).first()
                    if member:
                        db.session.delete(member)
                        db.session.commit()
                        flash('Student removed from group successfully!', 'success')
                        return redirect(url_for('management.admin_manage_group', group_id=group_id))
            
            elif action == 'set_leader':
                student_id = request.form.get('student_id')
                if student_id:
                    # Remove leader status from all members
                    StudentGroupMember.query.filter_by(group_id=group_id).update({'is_leader': False})
                    
                    # Set new leader
                    member = StudentGroupMember.query.filter_by(
                        group_id=group_id,
                        student_id=int(student_id)
                    ).first()
                    if member:
                        member.is_leader = True
                        db.session.commit()
                        flash('Group leader updated successfully!', 'success')
                        return redirect(url_for('management.admin_manage_group', group_id=group_id))
            
            elif action == 'edit_group':
                name = request.form.get('name')
                description = request.form.get('description', '')
                max_students = request.form.get('max_students', type=int)
                
                if name:
                    group.name = name
                if description is not None:
                    group.description = description
                if max_students is not None:
                    group.max_students = max_students
                
                db.session.commit()
                flash('Group updated successfully!', 'success')
                return redirect(url_for('management.admin_class_groups', class_id=group.class_id))
        
        return render_template('teachers/teacher_manage_group.html',
                             group=group,
                             current_members=current_members,
                             enrolled_students=enrolled_students,
                             current_member_ids=current_member_ids,
                             role_prefix=True)
    
    except Exception as e:
        print(f"Error managing group: {e}")
        flash('Error managing group. Please try again.', 'error')
        return redirect(url_for('management.admin_class_groups', class_id=group.class_id))



# ============================================================
# Route: /group/<int:group_id>/delete', methods=['POST']
# Function: admin_delete_group
# ============================================================

@bp.route('/group/<int:group_id>/delete', methods=['POST'])
@login_required
@management_required
def admin_delete_group(group_id):
    """Delete a student group (Administrator access). Preserves existing grades and submissions by nulling group_id."""
    try:
        from models import GroupGrade, GroupSubmission, GroupQuizAnswer
        group = StudentGroup.query.get_or_404(group_id)
        class_id = group.class_id

        # Preserve grades and submissions: set group_id to NULL so they remain tied to assignment + student
        GroupGrade.query.filter_by(group_id=group_id).update({GroupGrade.group_id: None})
        GroupSubmission.query.filter_by(group_id=group_id).update({GroupSubmission.group_id: None})
        GroupQuizAnswer.query.filter_by(group_id=group_id).update({GroupQuizAnswer.group_id: None})

        # Delete all group members first
        StudentGroupMember.query.filter_by(group_id=group_id).delete()

        # Delete the group (may still fail if other tables with non-nullable group_id have rows)
        db.session.delete(group)
        db.session.commit()

        flash('Group deleted successfully. Existing grades for that group were kept and remain associated with each student and assignment.', 'success')
        return redirect(url_for('management.admin_class_groups', class_id=class_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting group")
        flash('Could not delete group. It may have related data (e.g. contracts, peer evaluations). Try again or contact support.', 'error')
        return redirect(url_for('management.admin_class_groups', class_id=class_id))

# Additional admin group management routes


# ============================================================
# Route: /group/<int:group_id>/contract/create', methods=['GET', 'POST']
# Function: admin_create_group_contract
# ============================================================

@bp.route('/group/<int:group_id>/contract/create', methods=['GET', 'POST'])
@login_required
@management_required
def admin_create_group_contract(group_id):
    """Create a group contract (Administrator access)."""
    try:
        group = StudentGroup.query.get_or_404(group_id)
        class_obj = group.class_info
        
        if request.method == 'POST':
            # Handle contract creation logic here
            flash('Group contract functionality coming soon!', 'info')
            return redirect(url_for('management.admin_manage_group', group_id=group_id))
        
        return render_template('teachers/teacher_create_group_contract.html',
                             group=group,
                             class_obj=class_obj,
                             role_prefix=True)
    except Exception as e:
        print(f"Error creating group contract: {e}")
        flash('Error accessing group contract creation.', 'error')
        return redirect(url_for('management.admin_class_groups', class_id=group.class_id))

# def store_calendar_data(calendar_data, school_year_id, pdf_filename):
#     """Store extracted calendar data in the database."""
#     # PDF processing temporarily disabled due to import issues
#     pass

# ============================================================================
# GROUP ASSIGNMENT MANAGEMENT ROUTES
# ============================================================================

