"""
Activity logging for auditing and security.
"""

import json
from flask import current_app
from extensions import db
from models import ActivityLog


def log_activity(user_id, action, details=None, ip_address=None, user_agent=None, success=True, error_message=None):
    """Log one activity entry."""
    try:
        log_entry = ActivityLog()
        log_entry.user_id = user_id
        log_entry.action = action
        log_entry.ip_address = ip_address
        log_entry.user_agent = user_agent
        log_entry.success = success
        log_entry.error_message = error_message
        if details:
            log_entry.details = json.dumps(details)
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log activity: {str(e)}")


def get_user_activity_log(user_id=None, action=None, start_date=None, end_date=None, limit=100):
    """Retrieve activity log entries with optional filters."""
    query = ActivityLog.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter_by(action=action)
    if start_date:
        query = query.filter(ActivityLog.timestamp >= start_date)
    if end_date:
        query = query.filter(ActivityLog.timestamp <= end_date)
    return query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
