"""
Failed login tracking and tech alerts after repeated wrong passwords.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from flask import url_for

from extensions import db
from models import ActivityLog, User
from services.activity_log import log_activity
from services.notifications import create_notifications_for_users

FAILED_LOGIN_THRESHOLD = 5
FAILED_LOGIN_WINDOW_MINUTES = 30
ALERT_COOLDOWN_MINUTES = 60

_FAILED_LOGIN_ACTIONS = ('login_failed', 'login_failed_maintenance')


def _normalize_username(username: str | None) -> str:
    return (username or '').strip()


def _details_username(log_entry: ActivityLog) -> str | None:
    if not log_entry.details:
        return None
    try:
        payload = json.loads(log_entry.details)
    except (TypeError, json.JSONDecodeError):
        return None
    username = payload.get('username')
    return _normalize_username(username) if username else None


def count_recent_failed_logins(username: str, *, window_minutes: int = FAILED_LOGIN_WINDOW_MINUTES) -> int:
    """Count failed login attempts for ``username`` within the sliding window."""
    normalized = _normalize_username(username)
    if not normalized:
        return 0

    since = datetime.utcnow() - timedelta(minutes=window_minutes)
    logs = (
        ActivityLog.query.filter(
            ActivityLog.action.in_(_FAILED_LOGIN_ACTIONS),
            ActivityLog.success.is_(False),
            ActivityLog.timestamp >= since,
        )
        .order_by(ActivityLog.timestamp.desc())
        .limit(100)
        .all()
    )
    return sum(1 for entry in logs if _details_username(entry) == normalized)


def _alert_recently_sent(username: str) -> bool:
    normalized = _normalize_username(username)
    if not normalized:
        return False

    since = datetime.utcnow() - timedelta(minutes=ALERT_COOLDOWN_MINUTES)
    logs = (
        ActivityLog.query.filter(
            ActivityLog.action == 'login_brute_force_alert',
            ActivityLog.timestamp >= since,
        )
        .order_by(ActivityLog.timestamp.desc())
        .limit(20)
        .all()
    )
    return any(_details_username(entry) == normalized for entry in logs)


def _tech_user_ids() -> list[int]:
    tech_users = User.query.filter(User.role.in_(['Tech', 'IT Support'])).all()
    return [user.id for user in tech_users if user.id]


def notify_tech_users_of_failed_logins(
    username: str,
    *,
    attempt_count: int,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    """Create in-app notifications and send donotrespond emails to tech staff."""
    tech_ids = _tech_user_ids()
    if not tech_ids:
        return

    normalized = _normalize_username(username) or '(unknown)'
    ip_display = ip_address or 'unknown'
    title = f'Login alert: {attempt_count} failed attempts for {normalized}'
    message = (
        f'There have been {attempt_count} failed login attempts for username "{normalized}" '
        f'in the last {FAILED_LOGIN_WINDOW_MINUTES} minutes.\n'
        f'IP address: {ip_display}'
    )
    if user_agent:
        message += f'\nUser agent: {user_agent[:300]}'

    try:
        link = url_for('tech.activity_log', action='login_failed')
    except Exception:
        link = '/tech/activity-log?action=login_failed'

    create_notifications_for_users(
        tech_ids,
        'security',
        title,
        message,
        link=link,
    )

    log_activity(
        user_id=None,
        action='login_brute_force_alert',
        details={
            'username': normalized,
            'attempt_count': attempt_count,
            'ip_address': ip_address,
        },
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
    )


def handle_failed_login(username: str, *, ip_address: str | None = None, user_agent: str | None = None) -> None:
    """
    After a failed login has been logged, check whether tech staff should be notified.
    """
    count = count_recent_failed_logins(username)
    if count < FAILED_LOGIN_THRESHOLD:
        return
    if _alert_recently_sent(username):
        return

    try:
        notify_tech_users_of_failed_logins(
            username,
            attempt_count=count,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception as exc:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error('Failed to notify tech users about login attempts: %s', exc)
