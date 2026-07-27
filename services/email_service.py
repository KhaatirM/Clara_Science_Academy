"""
Email sending service. Uses Flask-Mail with Google Workspace SMTP.

Deliverability: From must match the authenticated MAIL_USERNAME. For spam issues, also verify
Google Admin → Apps → Google Workspace → Gmail → Authenticate email (DKIM), and DNS SPF/DMARC
for the domain. Optional MAIL_REPLY_TO (monitored inbox) often helps versus pure no-reply.
"""

import html
from email.utils import make_msgid

from flask import current_app, has_request_context, url_for
from extensions import mail


def _staff_login_url() -> str:
    """Absolute URL to the website login page (for emails outside request context)."""
    if has_request_context():
        try:
            return url_for("auth.login", _external=True)
        except Exception:
            pass
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    return f"{base}/login" if base else ""


def _default_sender_email() -> str:
    """Envelope From address string (must match Google SMTP auth user)."""
    return (current_app.config.get('MAIL_USERNAME') or '').strip()


def _message_id_domain() -> str:
    explicit = current_app.config.get('MAIL_MESSAGE_ID_DOMAIN')
    if explicit:
        return str(explicit).strip().lstrip('@')
    addr = _default_sender_email()
    if '@' in addr:
        return addr.rsplit('@', 1)[-1].strip().rstrip('>')
    return 'local'


def _transactional_extra_headers() -> dict:
    """Headers that help classify mail as system-generated (not bulk marketing).

    Do not set Message-ID here — Flask-Mail sets it from msg.msgId; adding another
    via extra_headers violates RFC 5322 and Gmail rejects the message.
    """
    return {
        'Auto-Submitted': 'auto-generated',
        # Reduces auto-reply / OOF loops to donotrespond@ (Exchange / Outlook)
        'X-Auto-Response-Suppress': 'OOF, AutoReply',
    }


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

        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        auth_user = _default_sender_email().lower()
        if isinstance(sender, (tuple, list)) and len(sender) == 2:
            sender_email = str(sender[1]).strip().lower()
            if auth_user and sender_email and sender_email != auth_user:
                current_app.logger.warning(
                    'MAIL_DEFAULT_SENDER email (%s) does not match MAIL_USERNAME (%s); '
                    'fix env/config for better deliverability',
                    sender[1],
                    current_app.config.get('MAIL_USERNAME'),
                )
        elif isinstance(sender, str) and auth_user:
            if sender.strip().lower() != auth_user:
                current_app.logger.warning(
                    'MAIL_DEFAULT_SENDER does not match MAIL_USERNAME; fix env/config for better deliverability'
                )

        reply_to = current_app.config.get('MAIL_REPLY_TO')
        extra = _transactional_extra_headers()

        msg = Message(
            subject=subject,
            sender=sender,
            recipients=[to_email] if isinstance(to_email, str) else to_email,
            body=body_text,
            html=body_html,
            reply_to=reply_to,
            extra_headers=extra,
        )
        domain = _message_id_domain()
        if domain:
            msg.msgId = make_msgid(domain=domain)

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
    google_initial_password: str,
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
  {google_initial_password}
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
<p>First Google sign-in with that address uses this initial password (change when prompted): <strong>{esc(google_initial_password)}</strong></p>
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


def notify_school_admins_parent_logins(
    credentials: list[dict],
    *,
    context_note: str | None = None,
) -> int:
    """
    Email Directors / School Administrators with newly created or re-issued parent portal passwords.
    ``credentials`` items should include parent_name, student_name, username, portal_password, email.
    Returns count of successful sends.
    """
    rows = [r for r in (credentials or []) if r.get("portal_password") and r.get("username")]
    if not rows:
        return 0

    recipients = _school_admin_recipient_emails()
    if not recipients:
        current_app.logger.warning("notify_school_admins_parent_logins: no admin emails found")
        return 0

    esc = html.escape
    count = len(rows)
    subject = (
        f"Parent portal login ready ({count} account{'s' if count != 1 else ''})"
        if count
        else "Parent portal login ready"
    )
    note_block = f"\n\nNote: {context_note}" if context_note else ""

    lines = []
    html_rows = []
    for row in rows:
        parent = (row.get("parent_name") or "Parent").strip()
        child = (row.get("student_name") or "—").strip()
        username = row.get("username") or "—"
        password = row.get("portal_password") or "—"
        email = row.get("email") or "—"
        status = "new" if row.get("created_new") else "temporary password re-issued"
        lines.append(
            f"- {parent} (child: {child}) [{status}]\n"
            f"  Email: {email}\n"
            f"  Username: {username}\n"
            f"  Temporary password: {password}"
        )
        html_rows.append(
            "<li>"
            f"<strong>{esc(parent)}</strong> — child: {esc(child)} "
            f"<em>({esc(status)})</em><br/>"
            f"Email: {esc(email)}<br/>"
            f"Username: <code>{esc(username)}</code><br/>"
            f"Temporary password: <code>{esc(password)}</code>"
            "</li>"
        )

    body_text = f"""Parent portal login credentials were just created or re-issued in the Clara Science Academy app.

Each parent was also emailed their own username and temporary password (only theirs — not other families').

{chr(10).join(lines)}{note_block}

— Automated message from Clara Science Academy
"""
    body_html = f"""<p>Parent portal login credentials were just created or re-issued.</p>
<p>Each parent was also emailed <strong>only their own</strong> username and temporary password.</p>
<ul>
{''.join(html_rows)}
</ul>
{f"<p><em>{esc(context_note)}</em></p>" if context_note else ""}
<p style="color:#666;font-size:0.9em;">— Clara Science Academy</p>
"""

    sent = 0
    for to in recipients:
        if send_email(to, subject, body_text, body_html=body_html):
            sent += 1
    return sent


def send_parent_portal_welcome_email(
    *,
    to_email: str,
    parent_name: str,
    username: str,
    temporary_password: str,
    student_names: list[str] | None = None,
) -> bool:
    """
    Email one parent their Family Portal login via donotrespond SMTP.
    Never includes other parents' credentials.
    """
    if not (to_email and to_email.strip() and "@" in to_email):
        return False
    if not (username and temporary_password):
        return False

    login_url = _staff_login_url()
    safe_name = (parent_name or "Parent").strip() or "Parent"
    children = [n.strip() for n in (student_names or []) if n and str(n).strip()]
    if children:
        if len(children) == 1:
            child_line = f"This login is linked to: {children[0]}."
        else:
            child_line = "This login is linked to: " + ", ".join(children) + "."
    else:
        child_line = "This login is for the Clara Science Academy Family Portal."

    subject = "Your Clara Science Academy Family Portal login"

    body_text = f"""Dear {safe_name},

Your Family Portal account is ready. This message was sent automatically from a no-reply address; please do not reply to this email.

{child_line}

Sign in to the school website with:
  Login page: {login_url or "(open the school website and choose Sign in)"}
  Username: {username}
  Temporary password: {temporary_password}

You will be asked to change your password on first sign-in. Store this information securely and do not share it with others.

— Clara Science Academy
"""

    esc = html.escape
    login_link = (
        f'<a href="{esc(login_url)}">{esc(login_url)}</a>'
        if login_url
        else esc("(open the school website and choose Sign in)")
    )

    body_html = f"""<p>Dear {esc(safe_name)},</p>
<p>Your <strong>Family Portal</strong> account is ready. This message was sent automatically from a no-reply address; please do not reply to this email.</p>
<p>{esc(child_line)}</p>
<p>Sign in to the school website with:</p>
<ul>
<li><strong>Login page:</strong> {login_link}</li>
<li><strong>Username:</strong> {esc(username)}</li>
<li><strong>Temporary password:</strong> {esc(temporary_password)}</li>
</ul>
<p>You will be asked to change your password on first sign-in. Store this information securely and do not share it with others.</p>
<p style="color:#666;font-size:0.9em;">— Clara Science Academy</p>
"""

    return send_email(to_email.strip(), subject, body_text, body_html=body_html)


def notify_parents_portal_logins(credentials: list[dict]) -> int:
    """
    Email each parent only their own portal credentials.

    Deduplicates by email so a parent linked to multiple students in one bulk run
    receives a single message (with all linked student names when available).
    Returns count of successful sends.
    """
    # email_lower -> aggregated payload
    by_email: dict[str, dict] = {}
    for row in credentials or []:
        password = row.get("portal_password")
        username = row.get("username")
        email = (row.get("email") or "").strip()
        if not password or not username or not email or "@" not in email:
            continue
        key = email.lower()
        entry = by_email.get(key)
        child = (row.get("student_name") or "").strip()
        if entry is None:
            by_email[key] = {
                "email": email,
                "parent_name": (row.get("parent_name") or "Parent").strip(),
                "username": username,
                "portal_password": password,
                "student_names": [child] if child else [],
            }
        else:
            # Prefer the first password/username issued in this batch for this email.
            if child and child not in entry["student_names"]:
                entry["student_names"].append(child)

    sent = 0
    for entry in by_email.values():
        try:
            ok = send_parent_portal_welcome_email(
                to_email=entry["email"],
                parent_name=entry["parent_name"],
                username=entry["username"],
                temporary_password=entry["portal_password"],
                student_names=entry["student_names"],
            )
            if ok:
                sent += 1
        except Exception as exc:
            current_app.logger.warning(
                "Parent portal welcome email failed for %s: %s",
                entry.get("email"),
                exc,
            )
    return sent


def notify_parent_login_credentials(
    credentials: list[dict],
    *,
    context_note: str | None = None,
) -> dict[str, int]:
    """
    Email each parent their own credentials, and email school admins a full copy.
    Returns counts: parents_emailed, admins_emailed.
    """
    parents_emailed = notify_parents_portal_logins(credentials)
    admins_emailed = notify_school_admins_parent_logins(
        credentials,
        context_note=context_note,
    )
    return {
        "parents_emailed": parents_emailed,
        "admins_emailed": admins_emailed,
    }
