"""
Shared communications functionality for all user roles.
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import (
    db, Message, MessageGroup, MessageGroupMember, Announcement, 
    Class, Enrollment, Student, TeacherStaff, User, Notification
)
from datetime import datetime
from sqlalchemy import or_, and_

def get_user_channels(user_id, user_role):
    """Get all channels/groups accessible to a user."""
    channels = []
    
    # Get class channels
    if user_role == 'Student':
        enrollments = Enrollment.query.filter_by(
            student_id=current_user.student_id,
            is_active=True
        ).all()
        class_ids = [e.class_id for e in enrollments]
        
        # Get class channels
        class_groups = MessageGroup.query.filter(
            MessageGroup.class_id.in_(class_ids),
            MessageGroup.group_type == 'class',
            MessageGroup.is_active == True
        ).all()
        
        for group in class_groups:
            unread = Message.query.filter(
                Message.group_id == group.id,
                Message.sender_id != user_id,
                Message.is_read == False
            ).count()
            
            channels.append({
                'id': group.id,
                'name': group.name or group.class_info.name if group.class_info else 'Unnamed',
                'type': 'class',
                'unread_count': unread
            })
        
        # Get student-created groups (only visible to students)
        student_groups = MessageGroup.query.filter(
            MessageGroup.group_type == 'student',
            MessageGroup.is_active == True
        ).all()
        
        for group in student_groups:
            # Check if user is a member
            member = MessageGroupMember.query.filter_by(
                group_id=group.id,
                user_id=user_id
            ).first()
            
            if member:
                unread = Message.query.filter(
                    Message.group_id == group.id,
                    Message.sender_id != user_id,
                    Message.is_read == False
                ).count()
                
                channels.append({
                    'id': group.id,
                    'name': group.name,
                    'type': 'student',
                    'unread_count': unread
                })
    
    elif user_role in ['Director', 'School Administrator'] or 'Teacher' in user_role:
        # Teachers/Admins see all class channels they teach/administer
        if user_role in ['Director', 'School Administrator']:
            classes = Class.query.filter_by(is_active=True).all()
        else:
            # Find TeacherStaff record by user_id - User has teacher_staff_id
            user = User.query.get(user_id)
            if user and user.teacher_staff_id:
                teacher = TeacherStaff.query.get(user.teacher_staff_id)
                if teacher:
                    classes = Class.query.filter_by(teacher_id=teacher.id, is_active=True).all()
                else:
                    classes = []
            else:
                classes = []
        
        class_ids = [c.id for c in classes]
        
        class_groups = MessageGroup.query.filter(
            MessageGroup.class_id.in_(class_ids),
            MessageGroup.group_type == 'class',
            MessageGroup.is_active == True
        ).all()
        
        for group in class_groups:
            unread = Message.query.filter(
                Message.group_id == group.id,
                Message.sender_id != user_id,
                Message.is_read == False
            ).count()
            
            channels.append({
                'id': group.id,
                'name': group.name or group.class_info.name if group.class_info else 'Unnamed',
                'type': 'class',
                'unread_count': unread
            })
        
        # Staff channels
        staff_groups = MessageGroup.query.filter(
            MessageGroup.group_type == 'staff',
            MessageGroup.is_active == True
        ).all()
        
        for group in staff_groups:
            # Check if user is a member
            member = MessageGroupMember.query.filter_by(
                group_id=group.id,
                user_id=user_id
            ).first()
            
            if member:
                unread = Message.query.filter(
                    Message.group_id == group.id,
                    Message.sender_id != user_id,
                    Message.is_read == False
                ).count()
                
                channels.append({
                    'id': group.id,
                    'name': group.name,
                    'type': 'staff',
                    'unread_count': unread
                })
    
    return channels

def get_direct_messages(user_id, user_role=None):
    """Get all direct message conversations for a user."""
    # Get all messages where user is sender or recipient (both direct type and NULL group_id)
    # This handles both explicit direct messages and messages in virtual DM channels
    sent_messages = Message.query.filter(
        Message.sender_id == user_id,
        or_(
            Message.message_type == 'direct',
            and_(Message.group_id.is_(None), Message.recipient_id.isnot(None))
        )
    ).all()
    
    received_messages = Message.query.filter(
        Message.recipient_id == user_id,
        or_(
            Message.message_type == 'direct',
            and_(Message.group_id.is_(None), Message.sender_id.isnot(None))
        )
    ).all()
    
    # Get unique conversation partners
    conversation_partners = set()
    for msg in sent_messages:
        if msg.recipient_id:
            conversation_partners.add(msg.recipient_id)
    for msg in received_messages:
        if msg.sender_id:
            conversation_partners.add(msg.sender_id)
    
    dms = []
    for partner_id in conversation_partners:
        # Filter: Teachers cannot see student-to-student DMs
        if user_role and 'Teacher' in user_role and user_role not in ['Director', 'School Administrator']:
            partner = User.query.get(partner_id)
            if partner and partner.role == 'Student':
                # Check if current user is also a student (shouldn't happen, but safety check)
                current_user_obj = User.query.get(user_id)
                if current_user_obj and current_user_obj.role == 'Student':
                    pass  # Students can see student DMs
                else:
                    # Skip student DMs for teachers
                    continue
        
        # Get latest message (check both direct type and NULL group_id for virtual DMs)
        latest_msg = Message.query.filter(
            or_(
                and_(Message.sender_id == user_id, Message.recipient_id == partner_id),
                and_(Message.sender_id == partner_id, Message.recipient_id == user_id)
            ),
            or_(
                Message.message_type == 'direct',
                and_(Message.group_id.is_(None), Message.recipient_id.isnot(None))
            )
        ).order_by(Message.created_at.desc()).first()
        
        if latest_msg:
            other_user = User.query.get(partner_id)
            if other_user:
                # Count unread messages (both direct type and NULL group_id)
                unread = Message.query.filter(
                    Message.sender_id == partner_id,
                    Message.recipient_id == user_id,
                    Message.is_read == False,
                    or_(
                        Message.message_type == 'direct',
                        and_(Message.group_id.is_(None), Message.recipient_id.isnot(None))
                    )
                ).count()
                
                dms.append({
                    'id': latest_msg.id,
                    'other_user_id': partner_id,
                    'other_user_name': other_user.username,
                    'unread_count': unread
                })
    
    return dms

def get_user_announcements(user_id, user_role):
    """Get announcements relevant to the user."""
    announcements = []
    
    if user_role == 'Student':
        # Find Student by user_id - User has student_id
        user = User.query.get(user_id)
        student = Student.query.get(user.student_id) if user and user.student_id else None
        if student:
            enrollments = Enrollment.query.filter_by(
                student_id=student.id,
                is_active=True
            ).all()
            class_ids = [e.class_id for e in enrollments]
            
            # Get announcements for student's classes or all students
            announcements_query = Announcement.query.filter(
                or_(
                    Announcement.target_group == 'all_students',
                    Announcement.target_group == 'all',
                    and_(
                        Announcement.target_group == 'class',
                        Announcement.class_id.in_(class_ids)
                    )
                )
            ).order_by(Announcement.timestamp.desc()).limit(50).all()
            
            announcements = []
            for ann in announcements_query:
                class_name = None
                if ann.target_group == 'class' and ann.class_id:
                    class_obj = Class.query.get(ann.class_id)
                    if class_obj:
                        class_name = class_obj.name
                
                announcements.append({
                    'id': ann.id,
                    'title': ann.title,
                    'message': ann.message,
                    'timestamp': ann.timestamp.isoformat(),
                    'sender_name': ann.sender.username if ann.sender else 'Unknown',
                    'is_important': ann.is_important,
                    'target_group': ann.target_group,
                    'class_name': class_name
                })
    
    elif user_role in ['Director', 'School Administrator'] or 'Teacher' in user_role:
        # Get all announcements (they can see everything)
        announcements_query = Announcement.query.order_by(
            Announcement.timestamp.desc()
        ).limit(100).all()
        
        announcements = []
        for ann in announcements_query:
            class_name = None
            if ann.target_group == 'class' and ann.class_id:
                class_obj = Class.query.get(ann.class_id)
                if class_obj:
                    class_name = class_obj.name
            
            announcements.append({
                'id': ann.id,
                'title': ann.title,
                'message': ann.message,
                'timestamp': ann.timestamp.isoformat(),
                'sender_name': ann.sender.username if ann.sender else 'Unknown',
                'is_important': ann.is_important,
                'target_group': ann.target_group,
                'class_name': class_name
            })
    
    return announcements

def ensure_class_channel_exists(class_id):
    """Ensure a message group exists for a class."""
    existing = MessageGroup.query.filter_by(
        class_id=class_id,
        group_type='class'
    ).first()
    
    if existing:
        return existing
    
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None
    
    # Get teacher's user_id if teacher exists
    teacher_user_id = None
    if class_obj.teacher and class_obj.teacher.user:
        teacher_user_id = class_obj.teacher.user.id
    
    # Create new group
    new_group = MessageGroup(
        name=class_obj.name,
        description=f"Class channel for {class_obj.name}",
        group_type='class',
        class_id=class_id,
        created_by=teacher_user_id,
        is_active=True
    )
    
    db.session.add(new_group)
    db.session.flush()
    
    # Add all enrolled students and teacher
    enrollments = Enrollment.query.filter_by(
        class_id=class_id,
        is_active=True
    ).all()
    
    for enrollment in enrollments:
        if enrollment.student and enrollment.student.user:
            member = MessageGroupMember(
                group_id=new_group.id,
                user_id=enrollment.student.user.id,
                is_admin=False
            )
            db.session.add(member)
    
    # Add teacher
    if class_obj.teacher and class_obj.teacher.user:
        teacher_member = MessageGroupMember(
            group_id=new_group.id,
            user_id=class_obj.teacher.user.id,
            is_admin=True
        )
        db.session.add(teacher_member)
    
    db.session.commit()
    return new_group

