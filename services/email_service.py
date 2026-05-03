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


def _school_admin_recipient_emails():
    """Personal or Workspace addresses for Directors and School Administrators."""
    from models import User
    from utils.user_roles import canonical_role_label

    seen = set()
    out = []
    for u in User.query.all():
        if canonical_role_label(getattr(u, "role", None)) not in ("Director", "School Administrator"):
            continue
        raw = (getattr(u, "email", None) or getattr(u, "google_workspace_email", None) or "").strip()
        if not raw or "@" not in raw:
            continue
        key = raw.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(raw)
    return out


def notify_school_admins_new_student_login(
    *,
    student_name: str,
    student_id: str,
    username: str,
    portal_password: str,
    school_email: str | None,
    google_initial_password: str,
    context_note: str | None = None,
) -> int:
    """
    Email Directors / School Administrators when a student account is first provisioned
    (e.g. promoted to 3rd grade). Returns count of successfully queued sends.
    """
    recipients = _school_admin_recipient_emails()
    if not recipients:
        current_app.logger.warning("notify_school_admins_new_student_login: no admin emails found")
        return 0

    esc = html.escape
    subject = f"Student portal ready: {student_name.strip()}"
    note_block = f"\n\nNote: {context_note}" if context_note else ""
    body_text = f"""A student website login and school email were just created in the Clara Science Academy app.

Student: {student_name}
State / internal student ID: {student_id or '—'}
Website username: {username}
Website temporary password: {portal_password}
School email (Google): {school_email or '—'}
First Google sign-in password: {google_initial_password}

Share these with the family through a secure channel. The website password and Google password are different.{note_block}

— Automated message from Clara Science Academy
"""

    se = school_email or "—"
    body_html = f"""<p>A student website login and school email were just created.</p>
<ul>
<li><strong>Student:</strong> {esc(student_name)}</li>
<li><strong>Student ID:</strong> {esc(student_id or '—')}</li>
<li><strong>Website username:</strong> {esc(username)}</li>
<li><strong>Website temporary password:</strong> {esc(portal_password)}</li>
<li><strong>School email:</strong> {esc(se)}</li>
<li><strong>First Google password:</strong> {esc(google_initial_password)}</li>
</ul>
<p>Share with the family securely. Portal and Google passwords are <strong>different</strong>.</p>
{f"<p><em>{esc(context_note)}</em></p>" if context_note else ""}
<p style="color:#666;font-size:0.9em;">— Clara Science Academy</p>
"""

    sent = 0
    for to in recipients:
        if send_email(to, subject, body_text, body_html=body_html):
            sent += 1
    return sent
