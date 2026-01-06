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
from .dashboard import management_dashboard as management_dashboard_func, redo_dashboard as redo_dashboard_func
from .calendar import calendar as calendar_func, school_breaks as school_breaks_func, add_calendar_event as add_calendar_event_func
from .students import students as students_func, student_jobs as student_jobs_func, add_student as add_student_func, download_students_csv as download_students_csv_func, download_students_template as download_students_template_func, upload_students_csv as upload_students_csv_func, student_report_card_history as student_report_card_history_func, view_student as view_student_func, admin_create_student_group as admin_create_student_group_func, generate_report_card_for_student as generate_report_card_for_student_func, void_assignment_for_students as void_assignment_for_students_func, unvoid_assignment_for_students as unvoid_assignment_for_students_func
from .teachers import (
    teachers as teachers_func, 
    add_teacher_staff as add_teacher_staff_func, 
    teacher_work_days as teacher_work_days_func, 
    add_teacher_work_days as add_teacher_work_days_func,
    edit_teacher_staff as edit_teacher_staff_func,
    remove_teacher_staff as remove_teacher_staff_func,
    view_teacher as view_teacher_func
)
from .classes import (
    classes as classes_func, 
    add_class as add_class_func, 
    view_class as view_class_func, 
    link_existing_classroom as link_existing_classroom_func, 
    create_and_link_classroom as create_and_link_classroom_func, 
    unlink_classroom as unlink_classroom_func,
    confirm_link_classroom as confirm_link_classroom_func, 
    take_class_attendance as take_class_attendance_func,
    edit_class as edit_class_func,
    remove_class as remove_class_func,
    class_roster as class_roster_func,
    class_grades as class_grades_func,
    manage_class_roster as manage_class_roster_func,
    class_grades_view as class_grades_view_func,
    admin_class_group_assignments as admin_class_group_assignments_func,
    admin_class_deadline_reminders as admin_class_deadline_reminders_func,
    admin_class_analytics as admin_class_analytics_func,
    admin_class_360_feedback as admin_class_360_feedback_func,
    admin_class_reflection_journals as admin_class_reflection_journals_func,
    admin_class_conflicts as admin_class_conflicts_func,
    admin_class_groups as admin_class_groups_func,
    admin_group_assignment_type_selector as admin_group_assignment_type_selector_func
)
from .assignments import (
    assignments_and_grades as assignments_and_grades_func,
    view_assignment as view_assignment_func,
    grade_assignment as grade_assignment_func,
    edit_assignment as edit_assignment_func,
    assignment_type_selector as assignment_type_selector_func,
    add_assignment as add_assignment_func,
    create_quiz_assignment as create_quiz_assignment_func,
    create_discussion_assignment as create_discussion_assignment_func,
    group_assignment_type_selector as group_assignment_type_selector_func,
    admin_view_group_assignment as admin_view_group_assignment_func,
    admin_grade_group_assignment as admin_grade_group_assignment_func,
    admin_edit_group_assignment as admin_edit_group_assignment_func,
    admin_delete_group_assignment as admin_delete_group_assignment_func,
    admin_grant_extensions as admin_grant_extensions_func,
    admin_grade_statistics as admin_grade_statistics_func,
    admin_grade_history as admin_grade_history_func,
    admin_group_grade_statistics as admin_group_grade_statistics_func,
    void_group_assignment as void_group_assignment_func,
    unvoid_group_assignment as unvoid_group_assignment_func,
    admin_change_group_assignment_status as admin_change_group_assignment_status_func,
    view_extension_requests as view_extension_requests_func,
    review_extension_request as review_extension_request_func,
    export_quiz_to_google_forms as export_quiz_to_google_forms_func
)
from .attendance import unified_attendance as unified_attendance_func, attendance_reports as attendance_reports_func, attendance_analytics as attendance_analytics_func
from .reports import report_cards as report_cards_func, generate_report_card_form as generate_report_card_form_func, report_cards_by_category as report_cards_by_category_func, view_report_card as view_report_card_func, generate_report_card_pdf as generate_report_card_pdf_func, delete_report_card as delete_report_card_func
from .communications import (
    communications as communications_func,
    management_messages as management_messages_func,
    management_groups as management_groups_func,
    management_create_group as management_create_group_func,
    management_view_group as management_view_group_func,
    management_send_message as management_send_message_func,
    management_view_message as management_view_message_func,
    management_create_announcement as management_create_announcement_func,
    management_schedule_announcement as management_schedule_announcement_func,
    admin_manage_group as admin_manage_group_func,
    admin_delete_group as admin_delete_group_func
)
from .administration import (
    settings as settings_func, 
    billing as billing_func, 
    google_connect_account as google_connect_account_func, 
    google_connect_callback as google_connect_callback_func, 
    google_disconnect_account as google_disconnect_account_func,
    edit_school_year as edit_school_year_func,
    edit_academic_period as edit_academic_period_func,
    edit_active_school_year as edit_active_school_year_func
)

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

@management_blueprint.route('/view-student/<int:student_id>', endpoint='view_student')
@login_required
@management_required
def view_student_route(student_id):
    """View student route - delegates to students module"""
    return view_student_func(student_id)

@management_blueprint.route('/report-cards/generate/<int:student_id>', endpoint='generate_report_card_for_student')
@login_required
@management_required
def generate_report_card_for_student_route(student_id):
    """Generate report card for student route - delegates to students module"""
    return generate_report_card_for_student_func(student_id)

@management_blueprint.route('/add-teacher-staff', methods=['GET', 'POST'], endpoint='add_teacher_staff')
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

# Add aliases for Google OAuth routes
@management_blueprint.route('/google-account/connect', endpoint='google_connect_account')
@login_required
@management_required
def google_connect_account_route():
    """Google connect account route - delegates to administration module"""
    return google_connect_account_func()

@management_blueprint.route('/google-account/callback', endpoint='google_connect_callback')
@login_required
@management_required
def google_connect_callback_route():
    """Google connect callback route - delegates to administration module"""
    return google_connect_callback_func()

@management_blueprint.route('/google-account/disconnect', methods=['POST'], endpoint='google_disconnect_account')
@login_required
@management_required
def google_disconnect_account_route():
    """Google disconnect account route - delegates to administration module"""
    return google_disconnect_account_func()

# Add aliases for assignment routes to maintain backward compatibility
@management_blueprint.route('/view-assignment/<int:assignment_id>', endpoint='view_assignment')
@login_required
@management_required
def view_assignment_route(assignment_id):
    """View assignment route - delegates to assignments module"""
    return view_assignment_func(assignment_id)

@management_blueprint.route('/grade/assignment/<int:assignment_id>', methods=['GET', 'POST'], endpoint='grade_assignment')
@login_required
@management_required
def grade_assignment_route(assignment_id):
    """Grade assignment route - delegates to assignments module"""
    return grade_assignment_func(assignment_id)

@management_blueprint.route('/edit-assignment/<int:assignment_id>', methods=['GET', 'POST'], endpoint='edit_assignment')
@login_required
@management_required
def edit_assignment_route(assignment_id):
    """Edit assignment route - delegates to assignments module"""
    return edit_assignment_func(assignment_id)

@management_blueprint.route('/view-class/<int:class_id>', endpoint='view_class')
@login_required
@management_required
def view_class_route(class_id):
    """View class route - delegates to classes module"""
    return view_class_func(class_id)

# Add alias for assignment type selector route
@management_blueprint.route('/assignment/type-selector', endpoint='assignment_type_selector')
@login_required
@management_required
def assignment_type_selector_route():
    """Assignment type selector route - delegates to assignments module"""
    return assignment_type_selector_func()

# Add alias for create quiz assignment route
@management_blueprint.route('/assignment/create-quiz', methods=['GET', 'POST'], endpoint='create_quiz_assignment')
@login_required
@management_required
def create_quiz_assignment_route():
    """Create quiz assignment route - delegates to assignments module"""
    return create_quiz_assignment_func()

@management_blueprint.route('/assignment/create/discussion', methods=['GET', 'POST'], endpoint='create_discussion_assignment')
@login_required
@management_required
def create_discussion_assignment_route():
    """Create discussion assignment route - delegates to assignments module"""
    return create_discussion_assignment_func()

# Add alias for group assignment type selector route
@management_blueprint.route('/group-assignment/type-selector', endpoint='group_assignment_type_selector')
@login_required
@management_required
def group_assignment_type_selector_route():
    """Group assignment type selector route - delegates to assignments module"""
    return group_assignment_type_selector_func()

# Add alias for teacher work days route
@management_blueprint.route('/calendar/teacher-work-days', endpoint='teacher_work_days')
@login_required
@management_required
def teacher_work_days_route():
    """Teacher work days route - delegates to teachers module"""
    return teacher_work_days_func()

# Add alias for add teacher work days route
@management_blueprint.route('/calendar/teacher-work-days/add', methods=['POST'], endpoint='add_teacher_work_days')
@login_required
@management_required
def add_teacher_work_days_route():
    """Add teacher work days route - delegates to teachers module"""
    return add_teacher_work_days_func()

# Add alias for download students CSV route
@management_blueprint.route('/students/download-csv', endpoint='download_students_csv')
@login_required
@management_required
def download_students_csv_route():
    """Download students CSV route - delegates to students module"""
    return download_students_csv_func()

# Add alias for download students template route
@management_blueprint.route('/students/download-template', endpoint='download_students_template')
@login_required
@management_required
def download_students_template_route():
    """Download students template route - delegates to students module"""
    return download_students_template_func()

# Add alias for upload students CSV route
@management_blueprint.route('/students/upload-csv', methods=['POST'], endpoint='upload_students_csv')
@login_required
@management_required
def upload_students_csv_route():
    """Upload students CSV route - delegates to students module"""
    return upload_students_csv_func()

# Add alias for add assignment route
@management_blueprint.route('/add-assignment', methods=['GET', 'POST'], endpoint='add_assignment')
@login_required
@management_required
def add_assignment_route():
    """Add assignment route - delegates to assignments module"""
    return add_assignment_func()

# Add alias for attendance reports route
@management_blueprint.route('/attendance/reports', endpoint='attendance_reports')
@login_required
@management_required
def attendance_reports_route():
    """Attendance reports route - delegates to attendance module"""
    return attendance_reports_func()

# Add alias for generate report card form route
@management_blueprint.route('/report/card/generate', methods=['GET', 'POST'], endpoint='generate_report_card_form')
@login_required
@management_required
def generate_report_card_form_route():
    """Generate report card form route - delegates to reports module"""
    return generate_report_card_form_func()

# Add alias for report cards by category route
@management_blueprint.route('/report-cards/category/<category>', endpoint='report_cards_by_category')
@login_required
@management_required
def report_cards_by_category_route(category):
    """Report cards by category route - delegates to reports module"""
    return report_cards_by_category_func(category)

# Add alias for view report card route
@management_blueprint.route('/report/card/view/<int:report_card_id>', endpoint='view_report_card')
@login_required
@management_required
def view_report_card_route(report_card_id):
    """View report card route - delegates to reports module"""
    return view_report_card_func(report_card_id)

# Add alias for generate report card PDF route
@management_blueprint.route('/report/card/pdf/<int:report_card_id>', endpoint='generate_report_card_pdf')
@login_required
@management_required
def generate_report_card_pdf_route(report_card_id):
    """Generate report card PDF route - delegates to reports module"""
    return generate_report_card_pdf_func(report_card_id)

# Add alias for delete report card route
@management_blueprint.route('/report-cards/delete/<int:report_card_id>', methods=['POST'], endpoint='delete_report_card')
@login_required
@management_required
def delete_report_card_route(report_card_id):
    """Delete report card route - delegates to reports module"""
    return delete_report_card_func(report_card_id)

# Add alias for attendance analytics route
@management_blueprint.route('/attendance-analytics', endpoint='attendance_analytics')
@login_required
@management_required
def attendance_analytics_route():
    """Attendance analytics route - delegates to attendance module"""
    return attendance_analytics_func()

# Add alias for student report card history route
@management_blueprint.route('/report-cards/student/<int:student_id>', endpoint='student_report_card_history')
@login_required
@management_required
def student_report_card_history_route(student_id):
    """Student report card history route - delegates to students module"""
    return student_report_card_history_func(student_id)

# Add alias for take class attendance route
@management_blueprint.route('/attendance/take/<int:class_id>', methods=['GET', 'POST'], endpoint='take_class_attendance')
@login_required
@management_required
def take_class_attendance_route(class_id):
    """Take class attendance route - delegates to classes module"""
    return take_class_attendance_func(class_id)

# Add alias for school breaks route
@management_blueprint.route('/calendar/school-breaks', methods=['GET', 'POST'], endpoint='school_breaks')
@login_required
@management_required
def school_breaks_route():
    """School breaks route - delegates to calendar module"""
    return school_breaks_func()

# Add alias for add calendar event route
@management_blueprint.route('/calendar/add-event', methods=['POST'], endpoint='add_calendar_event')
@login_required
@management_required
def add_calendar_event_route():
    """Add calendar event route - delegates to calendar module"""
    return add_calendar_event_func()

# Add alias for link existing classroom route
@management_blueprint.route('/class/<int:class_id>/link-existing-google-classroom', methods=['GET', 'POST'], endpoint='link_existing_classroom')
@login_required
@management_required
def link_existing_classroom_route(class_id):
    """Link existing classroom route - delegates to classes module"""
    return link_existing_classroom_func(class_id)

# Add alias for create and link classroom route
@management_blueprint.route('/class/<int:class_id>/create-google-classroom', methods=['GET', 'POST'], endpoint='create_and_link_classroom')
@login_required
@management_required
def create_and_link_classroom_route(class_id):
    """Create and link classroom route - delegates to classes module"""
    return create_and_link_classroom_func(class_id)

# Add alias for unlink classroom route
@management_blueprint.route('/class/<int:class_id>/unlink-google-classroom', methods=['POST'], endpoint='unlink_classroom')
@login_required
@management_required
def unlink_classroom_route(class_id):
    """Unlink classroom route - delegates to classes module"""
    return unlink_classroom_func(class_id)

# Add alias for confirm link classroom route
@management_blueprint.route('/class/<int:class_id>/confirm-link-classroom/<google_classroom_id>', methods=['POST'], endpoint='confirm_link_classroom')
@login_required
@management_required
def confirm_link_classroom_route(class_id, google_classroom_id):
    """Confirm link classroom route - delegates to classes module"""
    return confirm_link_classroom_func(class_id, google_classroom_id)

# Add alias for redo dashboard route
@management_blueprint.route('/redo-dashboard', endpoint='redo_dashboard')
@login_required
@management_required
def redo_dashboard_route():
    """Redo dashboard route - delegates to dashboard module"""
    return redo_dashboard_func()

# Add aliases for class management routes
@management_blueprint.route('/class/<int:class_id>/edit', methods=['GET', 'POST'], endpoint='edit_class')
@login_required
@management_required
def edit_class_route(class_id):
    """Edit class route - delegates to classes module"""
    return edit_class_func(class_id)

@management_blueprint.route('/class/<int:class_id>/remove', methods=['POST'], endpoint='remove_class')
@login_required
@management_required
def remove_class_route(class_id):
    """Remove class route - delegates to classes module"""
    return remove_class_func(class_id)

@management_blueprint.route('/class/<int:class_id>/roster', methods=['GET', 'POST'], endpoint='class_roster')
@login_required
@management_required
def class_roster_route(class_id):
    """Class roster route - delegates to classes module"""
    return class_roster_func(class_id)

@management_blueprint.route('/class/<int:class_id>/grades', endpoint='class_grades')
@login_required
@management_required
def class_grades_route(class_id):
    """Class grades route - delegates to classes module"""
    return class_grades_func(class_id)

@management_blueprint.route('/manage-class-roster/<int:class_id>', methods=['GET', 'POST'], endpoint='manage_class_roster')
@login_required
@management_required
def manage_class_roster_route(class_id):
    """Manage class roster route - delegates to classes module"""
    return manage_class_roster_func(class_id)

@management_blueprint.route('/class-grades-view/<int:class_id>', endpoint='class_grades_view')
@login_required
@management_required
def class_grades_view_route(class_id):
    """Class grades view route - delegates to classes module"""
    return class_grades_view_func(class_id)

# Add aliases for admin class routes
@management_blueprint.route('/class/<int:class_id>/group-assignments', endpoint='admin_class_group_assignments')
@login_required
@management_required
def admin_class_group_assignments_route(class_id):
    """Admin class group assignments route - delegates to classes module"""
    return admin_class_group_assignments_func(class_id)

@management_blueprint.route('/class/<int:class_id>/deadline-reminders', endpoint='admin_class_deadline_reminders')
@login_required
@management_required
def admin_class_deadline_reminders_route(class_id):
    """Admin class deadline reminders route - delegates to classes module"""
    return admin_class_deadline_reminders_func(class_id)

@management_blueprint.route('/class/<int:class_id>/analytics', endpoint='admin_class_analytics')
@login_required
@management_required
def admin_class_analytics_route(class_id):
    """Admin class analytics route - delegates to classes module"""
    return admin_class_analytics_func(class_id)

@management_blueprint.route('/class/<int:class_id>/360-feedback', endpoint='admin_class_360_feedback')
@login_required
@management_required
def admin_class_360_feedback_route(class_id):
    """Admin class 360 feedback route - delegates to classes module"""
    return admin_class_360_feedback_func(class_id)

@management_blueprint.route('/class/<int:class_id>/reflection-journals', endpoint='admin_class_reflection_journals')
@login_required
@management_required
def admin_class_reflection_journals_route(class_id):
    """Admin class reflection journals route - delegates to classes module"""
    return admin_class_reflection_journals_func(class_id)

@management_blueprint.route('/class/<int:class_id>/conflicts', endpoint='admin_class_conflicts')
@login_required
@management_required
def admin_class_conflicts_route(class_id):
    """Admin class conflicts route - delegates to classes module"""
    return admin_class_conflicts_func(class_id)

@management_blueprint.route('/class/<int:class_id>/groups', endpoint='admin_class_groups')
@login_required
@management_required
def admin_class_groups_route(class_id):
    """Admin class groups route - delegates to classes module"""
    return admin_class_groups_func(class_id)

@management_blueprint.route('/class/<int:class_id>/groups/create', methods=['GET', 'POST'], endpoint='admin_create_student_group')
@login_required
@management_required
def admin_create_student_group_route(class_id):
    """Admin create student group route - delegates to students module"""
    return admin_create_student_group_func(class_id)

@management_blueprint.route('/class/<int:class_id>/group-assignment/type-selector', endpoint='admin_group_assignment_type_selector')
@login_required
@management_required
def admin_group_assignment_type_selector_route(class_id):
    """Admin group assignment type selector route - delegates to classes module"""
    return admin_group_assignment_type_selector_func(class_id)

# Add aliases for teacher management routes
@management_blueprint.route('/edit-teacher-staff/<int:staff_id>', methods=['GET', 'POST'], endpoint='edit_teacher_staff')
@login_required
@management_required
def edit_teacher_staff_route(staff_id):
    """Edit teacher staff route - delegates to teachers module"""
    return edit_teacher_staff_func(staff_id)

@management_blueprint.route('/remove-teacher-staff/<int:staff_id>', methods=['POST'], endpoint='remove_teacher_staff')
@login_required
@management_required
def remove_teacher_staff_route(staff_id):
    """Remove teacher staff route - delegates to teachers module"""
    return remove_teacher_staff_func(staff_id)

@management_blueprint.route('/view-teacher/<int:teacher_id>', endpoint='view_teacher')
@login_required
@management_required
def view_teacher_route(teacher_id):
    """View teacher staff route - delegates to teachers module"""
    return view_teacher_func(teacher_id)

# Add aliases for group assignment admin routes
@management_blueprint.route('/group-assignment/<int:assignment_id>/view', endpoint='admin_view_group_assignment')
@login_required
@management_required
def admin_view_group_assignment_route(assignment_id):
    """Admin view group assignment route - delegates to assignments module"""
    return admin_view_group_assignment_func(assignment_id)

@management_blueprint.route('/group-assignment/<int:assignment_id>/grade', methods=['GET', 'POST'], endpoint='admin_grade_group_assignment')
@login_required
def admin_grade_group_assignment_route(assignment_id):
    """Grade group assignment route - allows teachers and administrators (delegates to assignments module)"""
    return admin_grade_group_assignment_func(assignment_id)

@management_blueprint.route('/group-assignment/<int:assignment_id>/edit', methods=['GET', 'POST'], endpoint='admin_edit_group_assignment')
@login_required
@management_required
def admin_edit_group_assignment_route(assignment_id):
    """Admin edit group assignment route - delegates to assignments module"""
    return admin_edit_group_assignment_func(assignment_id)

@management_blueprint.route('/group-assignment/<int:assignment_id>/delete', methods=['POST'], endpoint='admin_delete_group_assignment')
@login_required
@management_required
def admin_delete_group_assignment_route(assignment_id):
    """Admin delete group assignment route - delegates to assignments module"""
    return admin_delete_group_assignment_func(assignment_id)

@management_blueprint.route('/group-assignment/<int:assignment_id>/void', methods=['POST'], endpoint='void_group_assignment')
@login_required
@management_required
def void_group_assignment_route(assignment_id):
    """Void group assignment route - delegates to assignments module"""
    return void_group_assignment_func(assignment_id)

@management_blueprint.route('/group-assignment/<int:assignment_id>/unvoid', methods=['POST'], endpoint='unvoid_group_assignment')
@login_required
@management_required
def unvoid_group_assignment_route(assignment_id):
    """Unvoid group assignment route - delegates to assignments module"""
    return unvoid_group_assignment_func(assignment_id)

@management_blueprint.route('/group-assignment/<int:assignment_id>/change-status', methods=['POST'], endpoint='admin_change_group_assignment_status')
@login_required
@management_required
def admin_change_group_assignment_status_route(assignment_id):
    """Change group assignment status route - delegates to assignments module"""
    return admin_change_group_assignment_status_func(assignment_id)

@management_blueprint.route('/assignment/<int:assignment_id>/extensions', endpoint='admin_grant_extensions')
@login_required
@management_required
def admin_grant_extensions_route(assignment_id):
    """Admin grant extensions route - delegates to assignments module"""
    return admin_grant_extensions_func(assignment_id)

# Add alias for grant_extensions (backward compatibility)
@management_blueprint.route('/assignment/<int:assignment_id>/grant-extensions', methods=['POST'], endpoint='grant_extensions')
@login_required
@management_required
def grant_extensions_route(assignment_id):
    """Grant extensions route - alias for admin_grant_extensions"""
    return admin_grant_extensions_func(assignment_id)

@management_blueprint.route('/grades/statistics/<int:assignment_id>', endpoint='admin_grade_statistics')
@login_required
@management_required
def admin_grade_statistics_route(assignment_id):
    """Admin grade statistics route - delegates to assignments module"""
    return admin_grade_statistics_func(assignment_id)

@management_blueprint.route('/grades/history/<int:grade_id>', endpoint='admin_grade_history')
@login_required
@management_required
def admin_grade_history_route(grade_id):
    """Admin grade history route - delegates to assignments module"""
    return admin_grade_history_func(grade_id)

@management_blueprint.route('/group-assignment/<int:assignment_id>/statistics', endpoint='admin_group_grade_statistics')
@login_required
@management_required
def admin_group_grade_statistics_route(assignment_id):
    """Admin group grade statistics route - delegates to assignments module"""
    return admin_group_grade_statistics_func(assignment_id)

# Add route aliases for extension requests
@management_blueprint.route('/extension-requests', endpoint='view_extension_requests')
@login_required
@management_required
def view_extension_requests_route():
    """View extension requests route - delegates to assignments module"""
    from .assignments import view_extension_requests as view_extension_requests_func
    return view_extension_requests_func()

@management_blueprint.route('/extension-request/<int:request_id>/review', methods=['POST'], endpoint='review_extension_request')
@login_required
@management_required
def review_extension_request_route(request_id):
    """Review extension request route - delegates to assignments module"""
    from .assignments import review_extension_request as review_extension_request_func
    return review_extension_request_func(request_id)

# Add aliases for school year and academic period routes
@management_blueprint.route('/school-year/edit/<int:year_id>', methods=['POST'], endpoint='edit_school_year')
@login_required
@management_required
def edit_school_year_route(year_id):
    """Edit school year route - delegates to administration module"""
    return edit_school_year_func(year_id)

@management_blueprint.route('/school-year/edit-active', methods=['POST'], endpoint='edit_active_school_year')
@login_required
@management_required
def edit_active_school_year_route():
    """Edit active school year route - delegates to administration module"""
    return edit_active_school_year_func()

@management_blueprint.route('/academic-period/edit/<int:period_id>', methods=['POST'], endpoint='edit_academic_period')
@login_required
@management_required
def edit_academic_period_route(period_id):
    """Edit academic period route - delegates to administration module"""
    return edit_academic_period_func(period_id)

# Add alias for admin manage group route
@management_blueprint.route('/communications/groups/<int:group_id>/manage', methods=['GET', 'POST'], endpoint='admin_manage_group')
@login_required
@management_required
def admin_manage_group_route(group_id):
    """Admin manage group route - delegates to communications module"""
    return admin_manage_group_func(group_id)

# Add alias for admin delete group route
@management_blueprint.route('/group/<int:group_id>/delete', methods=['POST'], endpoint='admin_delete_group')
@login_required
@management_required
def admin_delete_group_route(group_id):
    """Admin delete group route - delegates to communications module"""
    return admin_delete_group_func(group_id)

# Add aliases for void/unvoid assignment routes
@management_blueprint.route('/void-assignment/<int:assignment_id>', methods=['POST'], endpoint='void_assignment_for_students')
@login_required
@management_required
def void_assignment_for_students_route(assignment_id):
    """Void assignment for students route - delegates to students module"""
    return void_assignment_for_students_func(assignment_id)

@management_blueprint.route('/unvoid-assignment/<int:assignment_id>', methods=['POST'], endpoint='unvoid_assignment_for_students')
@login_required
@management_required
def unvoid_assignment_for_students_route(assignment_id):
    """Unvoid assignment for students route - delegates to students module"""
    return unvoid_assignment_for_students_func(assignment_id)

# Add alias for export quiz to Google Forms route
@management_blueprint.route('/assignment/<int:assignment_id>/export-to-google-forms', methods=['POST'], endpoint='export_quiz_to_google_forms')
@login_required
@management_required
def export_quiz_to_google_forms_route(assignment_id):
    """Export quiz to Google Forms route - delegates to assignments module"""
    return export_quiz_to_google_forms_func(assignment_id)



