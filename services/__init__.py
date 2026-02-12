"""
Business logic and services. Keeps app.py as glue-only (config, blueprints, extensions).
"""

from .grade_calculation import (
    get_grade_for_student,
    calculate_and_get_grade_for_student,
)
from .notifications import (
    create_notification,
    create_notifications_for_users,
    create_notification_for_students_in_class,
    create_notification_for_all_students,
    create_notification_for_all_teachers,
    create_digest_notifications,
    create_grade_update_digest,
)
from .activity_log import log_activity, get_user_activity_log
from .attendance_on_login import record_school_day_attendance_on_login

__all__ = [
    'get_grade_for_student',
    'calculate_and_get_grade_for_student',
    'create_notification',
    'create_notifications_for_users',
    'create_notification_for_students_in_class',
    'create_notification_for_all_students',
    'create_notification_for_all_teachers',
    'create_digest_notifications',
    'create_grade_update_digest',
    'log_activity',
    'get_user_activity_log',
    'record_school_day_attendance_on_login',
]
