"""Privileged-role session timeout helpers."""

from __future__ import annotations

import time
from typing import Optional

from flask import session
from flask_login import current_user

from utils.user_roles import user_has_management_entry_access, user_has_tech_route_access


def is_privileged_session_user(user=None) -> bool:
    user = user or current_user
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user_has_tech_route_access(user):
        return True
    if user_has_management_entry_access(user):
        return True
    return False


def mark_privileged_session_started(user=None) -> None:
    if is_privileged_session_user(user):
        session['_privileged_session_started'] = time.time()
    else:
        session.pop('_privileged_session_started', None)


def privileged_session_expired(timeout_seconds: int) -> bool:
    if timeout_seconds <= 0:
        return False
    if not is_privileged_session_user():
        return False
    started = session.get('_privileged_session_started')
    if started is None:
        session['_privileged_session_started'] = time.time()
        return False
    try:
        return (time.time() - float(started)) > timeout_seconds
    except (TypeError, ValueError):
        session['_privileged_session_started'] = time.time()
        return False


def clear_privileged_session_marker() -> None:
    session.pop('_privileged_session_started', None)
