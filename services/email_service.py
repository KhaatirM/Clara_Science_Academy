"""
Email sending service. Uses Flask-Mail with Google Workspace SMTP.
"""

from flask import current_app
from extensions import mail


def send_email(to_email, subject, body_text, body_html=None):
    """
    Send an email via the configured SMTP (donotrespond@clarascienceacademy.org).

    Args:
        to_email: Recipient email address (str or list of str).
        subject: Email subject line.
        body_text: Plain-text body.
        body_html: Optional HTML body. If provided, a multipart message is sent.

    Returns:
        True if sent successfully, False otherwise (e.g. MAIL_PASSWORD not set).
    """
    if not current_app.config.get('MAIL_PASSWORD'):
        current_app.logger.warning('MAIL_PASSWORD not set; skipping email to %s', to_email)
        return False
    try:
        from flask_mail import Message
        msg = Message(
            subject=subject,
            recipients=[to_email] if isinstance(to_email, str) else to_email,
            body=body_text,
            html=body_html,
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error('Failed to send email to %s: %s', to_email, e, exc_info=True)
        return False


def send_notification_email(user, title, message, link=None):
    """
    Send a notification email to a user. Uses email or google_workspace_email.

    Args:
        user: User model (must have .email or .google_workspace_email).
        title: Email subject / notification title.
        message: Plain-text body.
        link: Optional URL to include in the email.

    Returns:
        True if sent, False otherwise.
    """
    to = getattr(user, 'google_workspace_email', None) or getattr(user, 'email', None)
    if not to:
        return False
    body = message
    if link:
        body += f"\n\nView: {link}"
    return send_email(to, title, body)
