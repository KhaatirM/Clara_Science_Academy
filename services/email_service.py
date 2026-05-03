"""
Email sending service. Uses Flask-Mail with Google Workspace SMTP.
"""

import html

from flask import current_app, has_request_context, url_for
from extensions import mail

from services.google_sync_tasks import DEFAULT_TEMP_PASSWORD


def _staff_login_url() -> str:
    """Absolute URL to the website login page (for emails outside request context)."""
    if has_request_context():
        try:
            return url_for("auth.login", _external=True)
        except Exception:
            pass
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    return f"{base}/login" if base else ""


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


def send_staff_welcome_email(
    personal_email: str,
    display_name: str,
    *,
    username: str,
    temporary_password: str,
    school_email: str | None,
) -> bool:
    """
    Email website login + school (@clarascienceacademy.org) details to the staff
    member's personal email via donotrespond SMTP (MAIL_USERNAME / MAIL_PASSWORD).
    """
    if not (personal_email and personal_email.strip() and "@" in personal_email):
        return False

    login_url = _staff_login_url()
    safe_name = (display_name or "Staff").strip()
    se = (school_email or "").strip() or None

    subject = "Your Clara Science Academy website login and school email"

    body_text = f"""Dear {safe_name},

Your Clara Science Academy accounts are ready. This message was sent automatically from a no-reply address; please do not reply to this email.

WEBSITE (portal only — different from Google sign-in below)
Sign in to the school website with:
  Login page: {login_url or "(open the school website and choose Sign in)"}
  Username: {username}
  Temporary password: {temporary_password}
You will be asked to change your password on first sign-in.

SCHOOL EMAIL (Google — Gmail, Classroom, Drive)
Your official school email address:
  {se or "(if missing, contact IT — it may still be provisioning)"}
First sign-in with Google using that address uses this initial password (you must change it when prompted):
  {DEFAULT_TEMP_PASSWORD}
(This Google password is separate from your website portal password above.)

Store this information securely.

— Clara Science Academy
"""

    esc = html.escape
    se_html = esc(se) if se else "<em>(if missing, contact IT — it may still be provisioning)</em>"
    login_link = (
        f'<a href="{esc(login_url)}">{esc(login_url)}</a>'
        if login_url
        else esc("(open the school website and choose Sign in)")
    )

    body_html = f"""<p>Dear {esc(safe_name)},</p>
<p>Your Clara Science Academy accounts are ready. This message was sent automatically from a no-reply address; please do not reply to this email.</p>
<h3 style="margin:1.25em 0 0.5em;">Website (portal only)</h3>
<p>Sign in to the <strong>school website</strong> with:</p>
<ul>
<li><strong>Login page:</strong> {login_link}</li>
<li><strong>Username:</strong> {esc(username)}</li>
<li><strong>Temporary password:</strong> {esc(temporary_password)}</li>
</ul>
<p>You will be asked to change your password on first sign-in.</p>
<h3 style="margin:1.25em 0 0.5em;">School email (Google)</h3>
<p>Your official school email address (Gmail, Classroom, Drive):</p>
<p style="font-size:1.1em;"><strong>{se_html}</strong></p>
<p>First Google sign-in with that address uses this initial password (change when prompted): <strong>{esc(DEFAULT_TEMP_PASSWORD)}</strong></p>
<p style="font-size:0.95em;color:#444;">That Google password is separate from your website portal password above.</p>
<p>Store this information securely.</p>
<p style="color:#666;font-size:0.9em;">— Clara Science Academy</p>
"""

    return send_email(personal_email.strip(), subject, body_text, body_html=body_html)
