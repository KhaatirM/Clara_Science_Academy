"""
Management Routes Package

This package contains all management-related routes organized by functional area.
Each module focuses on a specific aspect of management functionality.
"""

from flask import Blueprint, redirect, url_for
from flask_login import login_required
from decorators import management_required

# Create the main management blueprint
management_blueprint = Blueprint('management', __name__)

# Import all route modules to register their routes
from . import (
    dashboard,
    students,
    teachers,
    classes,
    assignments,
    attendance,
    calendar,
    communications,
    reports,
    administration
)

# Register all blueprints with the main management blueprint
management_blueprint.register_blueprint(dashboard.bp, url_prefix='')
management_blueprint.register_blueprint(students.bp, url_prefix='')
management_blueprint.register_blueprint(teachers.bp, url_prefix='')
management_blueprint.register_blueprint(classes.bp, url_prefix='')
management_blueprint.register_blueprint(assignments.bp, url_prefix='')
management_blueprint.register_blueprint(attendance.bp, url_prefix='')
management_blueprint.register_blueprint(calendar.bp, url_prefix='')
management_blueprint.register_blueprint(communications.bp, url_prefix='')
management_blueprint.register_blueprint(reports.bp, url_prefix='')
management_blueprint.register_blueprint(administration.bp, url_prefix='')

# Add route aliases directly to main blueprint for backward compatibility
# These ensure endpoints like 'management.calendar' work (not 'management.calendar.calendar')
from flask_login import login_required
from decorators import management_required

# Import the actual functions to call them
from .dashboard import management_dashboard as management_dashboard_func
from .calendar import calendar as calendar_func
from .students import students as students_func, student_jobs as student_jobs_func, add_student as add_student_func
from .teachers import teachers as teachers_func, add_teacher_staff as add_teacher_staff_func
from .classes import classes as classes_func, add_class as add_class_func
from .assignments import assignments_and_grades as assignments_and_grades_func
from .attendance import unified_attendance as unified_attendance_func
from .reports import report_cards as report_cards_func
from .communications import (
    communications as communications_func,
    management_messages as management_messages_func,
    management_groups as management_groups_func,
    management_create_group as management_create_group_func,
    management_view_group as management_view_group_func,
    management_send_message as management_send_message_func,
    management_view_message as management_view_message_func,
    management_create_announcement as management_create_announcement_func,
    management_schedule_announcement as management_schedule_announcement_func
)
from .administration import settings as settings_func, billing as billing_func

# Register main routes on main blueprint with correct endpoint names for backward compatibility
@management_blueprint.route('/dashboard', endpoint='management_dashboard')
@login_required
@management_required
def management_dashboard_route():
    """Management dashboard route - delegates to dashboard module"""
    return management_dashboard_func()

@management_blueprint.route('/students', endpoint='students')
@login_required
@management_required
def students_route():
    """Students route - delegates to students module"""
    return students_func()

@management_blueprint.route('/teachers', endpoint='teachers')
@login_required
@management_required
def teachers_route():
    """Teachers route - delegates to teachers module"""
    return teachers_func()

@management_blueprint.route('/classes', endpoint='classes')
@login_required
@management_required
def classes_route():
    """Classes route - delegates to classes module"""
    return classes_func()

@management_blueprint.route('/assignments-and-grades', endpoint='assignments_and_grades')
@login_required
@management_required
def assignments_and_grades_route():
    """Assignments and grades route - delegates to assignments module"""
    return assignments_and_grades_func()

@management_blueprint.route('/unified-attendance', endpoint='unified_attendance')
@login_required
@management_required
def unified_attendance_route():
    """Unified attendance route - delegates to attendance module"""
    return unified_attendance_func()

@management_blueprint.route('/report-cards', endpoint='report_cards')
@login_required
@management_required
def report_cards_route():
    """Report cards route - delegates to reports module"""
    return report_cards_func()

@management_blueprint.route('/billing', endpoint='billing')
@login_required
@management_required
def billing_route():
    """Billing route - delegates to administration module"""
    return billing_func()

# Add aliases for common action routes
@management_blueprint.route('/add-student', methods=['GET', 'POST'], endpoint='add_student')
@login_required
@management_required
def add_student_route():
    """Add student route - delegates to students module"""
    return add_student_func()

@management_blueprint.route('/add-teacher-staff', methods=['GET', 'POST'], endpoint='add_teacher')
@login_required
@management_required
def add_teacher_route():
    """Add teacher route - delegates to teachers module"""
    return add_teacher_staff_func()

@management_blueprint.route('/add-class', methods=['GET', 'POST'], endpoint='add_class')
@login_required
@management_required
def add_class_route():
    """Add class route - delegates to classes module"""
    return add_class_func()

# Register routes on main blueprint with correct endpoint names
@management_blueprint.route('/calendar', endpoint='calendar')
@login_required
@management_required
def calendar_route():
    """Calendar route - delegates to calendar module"""
    return calendar_func()

@management_blueprint.route('/communications', endpoint='communications')
@login_required
@management_required
def communications_route():
    """Communications route - delegates to communications module"""
    return communications_func()

# Add aliases for communications sub-routes to maintain backward compatibility
@management_blueprint.route('/communications/messages', endpoint='management_messages')
@login_required
@management_required
def management_messages_route():
    """Messages route - delegates to communications module"""
    return management_messages_func()

@management_blueprint.route('/communications/messages/send', methods=['GET', 'POST'], endpoint='management_send_message')
@login_required
@management_required
def management_send_message_route():
    """Send message route - delegates to communications module"""
    return management_send_message_func()

@management_blueprint.route('/communications/messages/<int:message_id>', endpoint='management_view_message')
@login_required
@management_required
def management_view_message_route(message_id):
    """View message route - delegates to communications module"""
    return management_view_message_func(message_id)

@management_blueprint.route('/communications/groups', endpoint='management_groups')
@login_required
@management_required
def management_groups_route():
    """Groups route - delegates to communications module"""
    return management_groups_func()

@management_blueprint.route('/communications/groups/create', methods=['GET', 'POST'], endpoint='management_create_group')
@login_required
@management_required
def management_create_group_route():
    """Create group route - delegates to communications module"""
    return management_create_group_func()

@management_blueprint.route('/communications/groups/<int:group_id>', endpoint='management_view_group')
@login_required
@management_required
def management_view_group_route(group_id):
    """View group route - delegates to communications module"""
    return management_view_group_func(group_id)

@management_blueprint.route('/communications/announcements/create', methods=['GET', 'POST'], endpoint='management_create_announcement')
@login_required
@management_required
def management_create_announcement_route():
    """Create announcement route - delegates to communications module"""
    return management_create_announcement_func()

@management_blueprint.route('/communications/announcements/schedule', methods=['GET', 'POST'], endpoint='management_schedule_announcement')
@login_required
@management_required
def management_schedule_announcement_route():
    """Schedule announcement route - delegates to communications module"""
    return management_schedule_announcement_func()

@management_blueprint.route('/student-jobs', endpoint='student_jobs')
@login_required
@management_required
def student_jobs_route():
    """Student jobs route - delegates to students module"""
    return student_jobs_func()

@management_blueprint.route('/settings', endpoint='settings')
@login_required
@management_required
def settings_route():
    """Settings route - delegates to administration module"""
    return settings_func()



