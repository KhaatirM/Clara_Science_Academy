"""
Notification creation helpers. Used by management, teachers, etc.
Creates in-app notifications and sends matching emails via donotrespond@clarascienceacademy.org.
"""

from flask import has_request_context, request

from extensions import db
from models import Notification, Student, TeacherStaff, User


def create_notification(user_id, notification_type, title, message, link=None):
    """Create a notification for one user and send an email to their school email."""
    notification = Notification()
    notification.user_id = user_id
    notification.type = notification_type
    notification.title = title
    notification.message = message
    notification.link = link
    db.session.add(notification)
    db.session.commit()

    # Send email to the user's school email (google_workspace_email or email)
    try:
        user = User.query.get(user_id)
        if user:
            from .email_service import send_notification_email
            # Use absolute URL for links in email so they work when clicked
            email_link = link
            if link and link.startswith('/') and has_request_context():
                base = getattr(request, 'url_root', '') or ''
                email_link = (base.rstrip('/') + link) if base else link
            send_notification_email(user, title, message, link=email_link)
    except Exception as e:
        # Don't fail notification creation if email fails (e.g. MAIL_PASSWORD not set)
        from flask import current_app
        current_app.logger.warning('Could not send notification email to user %s: %s', user_id, e)

    return notification


def create_notifications_for_users(user_ids, notification_type, title, message, link=None):
    """Create notifications for multiple users."""
    notifications = []
    for user_id in user_ids:
        notification = create_notification(user_id, notification_type, title, message, link)
        notifications.append(notification)
    return notifications


def create_notification_for_students_in_class(class_id, notification_type, title, message, link=None):
    """Create notifications for students in a class. Uses Enrollment when available."""
    from models import Enrollment
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    user_ids = [e.student.user.id for e in enrollments if e.student and getattr(e.student, 'user', None)]
    if not user_ids:
        # Fallback: all students (legacy behavior when enrollment not used)
        students = Student.query.all()
        user_ids = [s.user.id for s in students if getattr(s, 'user', None)]
    return create_notifications_for_users(user_ids, notification_type, title, message, link)


def create_notification_for_all_students(notification_type, title, message, link=None):
    """Create notifications for all students."""
    students = Student.query.all()
    user_ids = [s.user.id for s in students if s.user]
    return create_notifications_for_users(user_ids, notification_type, title, message, link)


def create_notification_for_all_teachers(notification_type, title, message, link=None):
    """Create notifications for all teachers."""
    teachers = TeacherStaff.query.all()
    user_ids = [t.user.id for t in teachers if t.user]
    return create_notifications_for_users(user_ids, notification_type, title, message, link)


def create_digest_notifications(user_counts, notification_type, title_single, title_plural_fmt,
                                message_single, message_plural_fmt, link=None):
    """
    Create one notification per user, summarizing multiple events (digest).
    Use this instead of creating N separate notifications when one user has many updates.

    Args:
        user_counts: dict mapping user_id -> count (e.g. {user_id: 3} means "3 updates for this user").
        notification_type: type string for Notification.
        title_single: title when count == 1.
        title_plural_fmt: format string when count > 1, e.g. "You have {count} grade updates".
        message_single: message when count == 1.
        message_plural_fmt: format string when count > 1, e.g. "You have {count} new grade(s).".
        link: optional link for the notification.

    Returns:
        List of created Notification objects.
    """
    notifications = []
    for user_id, count in user_counts.items():
        if count <= 0:
            continue
        if count == 1:
            title, message = title_single, message_single
        else:
            title = title_plural_fmt.format(count=count)
            message = message_plural_fmt.format(count=count)
        notification = create_notification(user_id, notification_type, title, message, link)
        notifications.append(notification)
    return notifications


def create_grade_update_digest(student_user_ids, assignment_title=None, link=None):
    """
    Create one digest notification per student for grade updates on an assignment.
    Call this after bulk-saving grades instead of one notification per grade.

    Args:
        student_user_ids: list of user_ids for students who received a grade update.
        assignment_title: optional title for the assignment (for message text).
        link: optional link (e.g. url_for('student.student_assignments') or assignment-specific URL).

    Returns:
        List of created Notification objects.
    """
    counts = {}
    for uid in student_user_ids:
        counts[uid] = counts.get(uid, 0) + 1
    title_single = "Grade updated"
    title_plural_fmt = "You have {count} grade updates"
    message_single = f"Your grade was updated for {assignment_title or 'an assignment'}."
    message_plural_fmt = "You have {count} grade update(s) for this assignment."
    return create_digest_notifications(
        counts, "grade_update", title_single, title_plural_fmt,
        message_single, message_plural_fmt, link
    )
