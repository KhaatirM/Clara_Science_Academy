import os
import json
from flask import Flask, render_template, g, current_app, redirect, url_for, flash, request, session
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from config import Config
from sqlalchemy import func, and_
from datetime import datetime

# Import extensions to avoid circular imports
from extensions import db, login_manager
# from flask_migrate import Migrate  # Temporarily disabled due to import issues

# Import models here to avoid circular imports
from models import User, Student, Grade, SchoolYear, ReportCard, Assignment, Notification, MaintenanceMode, ActivityLog

def _calculate_grades_for_subjects(grades, subjects):
    """
    Helper function to calculate average grades for a list of subjects.
    
    Args:
        grades (list): A list of Grade objects for the student.
        subjects (list): A list of subject names (str) to calculate grades for.

    Returns:
        dict: A dictionary with calculated grades for each subject.
    """
    calculated = {}
    for subject in subjects:
        # Filter grades for the current subject
        subject_grades = [g for g in grades if g.assignment.class_info.name == subject]
        
        if subject_grades:
            total_score = 0
            count = 0
            # Safely calculate total score, handling potential JSON and data errors
            for g in subject_grades:
                try:
                    grade_data = json.loads(g.grade_data)
                    score = grade_data.get('score')
                    # Ensure score is a number before adding
                    if isinstance(score, (int, float)):
                        total_score += score
                        count += 1
                except (json.JSONDecodeError, TypeError):
                    current_app.logger.warning(f"Could not parse grade_data for grade id {g.id}: {g.grade_data}")
                    pass
            
            # Calculate average if valid grades were found
            if count > 0:
                avg = total_score / count
                calculated[subject] = {'score': round(avg, 2), 'comment': ''}
    return calculated

def _calculate_grades_1_2(grades, quarter):
    """
    Calculate grades for students in 1st and 2nd grade.
    
    Note: Subject names are hardcoded. For a more flexible system,
    this should be driven by data (e.g., a subject category in the database).
    """
    subjects = [
        "Reading Comprehension", "Language Arts", "Spelling", "Handwriting",
        "Math", "Science", "Social Studies", "Art", "Physical Education"
    ]
    return _calculate_grades_for_subjects(grades, subjects)

def _calculate_grades_3(grades, quarter):
    """
    Calculate grades for students in 3rd grade.
    
    Note: Subject names are hardcoded.
    """
    subjects = [
        "Reading", "English", "Spelling", "Math", "Science", "Social Studies",
        "Art", "Physical Education", "Islamic Studies", "Quran", "Arabic"
    ]
    return _calculate_grades_for_subjects(grades, subjects)

def _calculate_grades_4_8(grades, quarter):
    """
    Calculate grades for students in 4th through 8th grade.
    
    Note: Subject names are hardcoded.
    """
    subjects = [
        "Reading", "English", "Spelling", "Vocabulary", "Math", "Science",
        "Social Studies", "Art", "Physical Education", "Islamic Studies", "Quran", "Arabic"
    ]
    calculated_grades = _calculate_grades_for_subjects(grades, subjects)
    
    # Calculate overall average for these grade levels
    if calculated_grades:
        scores = [d.get('score', 0) for d in calculated_grades.values() if isinstance(d.get('score'), (int, float))]
        if scores:
            overall_avg = sum(scores) / len(scores)
            calculated_grades['Overall'] = {'score': round(overall_avg, 2)}
            
    return calculated_grades

def calculate_and_get_grade_for_student(student_id, school_year_id, quarter):
    """
    Calculates and retrieves grades for a student for a specific quarter and school year.
    This function computes grades based on assignments and stores the result in a ReportCard entry.
    """
    student = Student.query.get(student_id)
    if not student:
        return {}

    # Fetch all relevant grades for the student in the given school year and quarter
    grades = db.session.query(Grade).join(Assignment).filter(
        Grade.student_id == student_id,
        Assignment.school_year_id == school_year_id,
        Assignment.quarter == quarter
    ).all()

    calculated_grades = {}
    # Dispatch to the correct calculation function based on grade level
    if student.grade_level in [1, 2]:
        calculated_grades = _calculate_grades_1_2(grades, quarter)
    elif student.grade_level == 3:
        calculated_grades = _calculate_grades_3(grades, quarter)
    elif student.grade_level in [4, 5, 6, 7, 8]:
        calculated_grades = _calculate_grades_4_8(grades, quarter)
    else:
        current_app.logger.info(f"No grade calculation logic for grade level: {student.grade_level}")
        return {} # No calculation defined for this grade level

    # Find or create a report card entry
    report_card = ReportCard.query.filter_by(
        student_id=student_id,
        school_year_id=school_year_id,
        quarter=quarter
    ).first()

    if not report_card:
        report_card = ReportCard()
        report_card.student_id = student_id
        report_card.school_year_id = school_year_id
        report_card.quarter = quarter
        db.session.add(report_card)

    # Update the report card with the newly calculated grades
    report_card.grades_details = json.dumps(calculated_grades)
    report_card.generated_at = func.now()
    
    # Commit the changes to the database
    db.session.commit()

    return calculated_grades

def get_grade_for_student(student_id, school_year_id, quarter):
    """
    Retrieves the stored grades for a student from their report card.
    If no report card exists, it attempts to calculate the grades.
    """
    report_card = ReportCard.query.filter_by(
        student_id=student_id,
        school_year_id=school_year_id,
        quarter=quarter
    ).first()

    if report_card and report_card.grades_details:
        return json.loads(report_card.grades_details)
    else:
        # If no report card is found, calculate the grades on-the-fly
        return calculate_and_get_grade_for_student(student_id, school_year_id, quarter)

def create_notification(user_id, notification_type, title, message, link=None):
    """
    Create a notification for a specific user.
    
    Args:
        user_id (int): The user ID to create the notification for
        notification_type (str): Type of notification ('announcement', 'assignment', 'grade', etc.)
        title (str): Notification title
        message (str): Notification message
        link (str, optional): URL for more information/action
    """
    notification = Notification()
    notification.user_id = user_id
    notification.type = notification_type
    notification.title = title
    notification.message = message
    notification.link = link
    db.session.add(notification)
    db.session.commit()
    return notification

def create_notifications_for_users(user_ids, notification_type, title, message, link=None):
    """
    Create notifications for multiple users.
    
    Args:
        user_ids (list): List of user IDs to create notifications for
        notification_type (str): Type of notification
        title (str): Notification title
        message (str): Notification message
        link (str, optional): URL for more information/action
    """
    notifications = []
    for user_id in user_ids:
        notification = create_notification(user_id, notification_type, title, message, link)
        notifications.append(notification)
    return notifications

def create_notification_for_students_in_class(class_id, notification_type, title, message, link=None):
    """
    Create notifications for all students in a specific class.
    
    Args:
        class_id (int): The class ID
        notification_type (str): Type of notification
        title (str): Notification title
        message (str): Notification message
        link (str, optional): URL for more information/action
    """
    # Get all students in the class (simplified - in real implementation, use Enrollment model)
    # For now, we'll get all students since enrollment isn't implemented
    students = Student.query.all()
    user_ids = [student.user.id for student in students if student.user]
    return create_notifications_for_users(user_ids, notification_type, title, message, link)

def create_notification_for_all_students(notification_type, title, message, link=None):
    """
    Create notifications for all students.
    
    Args:
        notification_type (str): Type of notification
        title (str): Notification title
        message (str): Notification message
        link (str, optional): URL for more information/action
    """
    students = Student.query.all()
    user_ids = [student.user.id for student in students if student.user]
    return create_notifications_for_users(user_ids, notification_type, title, message, link)

def create_notification_for_all_teachers(notification_type, title, message, link=None):
    """
    Create notifications for all teachers.
    
    Args:
        notification_type (str): Type of notification
        title (str): Notification title
        message (str): Notification message
        link (str, optional): URL for more information/action
    """
    from models import TeacherStaff
    teachers = TeacherStaff.query.all()
    user_ids = [teacher.user.id for teacher in teachers if teacher.user]
    return create_notifications_for_users(user_ids, notification_type, title, message, link)


def log_activity(user_id, action, details=None, ip_address=None, user_agent=None, success=True, error_message=None):
    """
    Log user activity for auditing and security purposes.
    
    Args:
        user_id (int): The user ID performing the action
        action (str): The action being performed (e.g., 'login', 'create_student')
        details (dict, optional): Additional details about the action
        ip_address (str, optional): IP address of the user
        user_agent (str, optional): User agent string
        success (bool): Whether the action was successful
        error_message (str, optional): Error message if action failed
    """
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
        # If logging fails, we don't want to break the main functionality
        current_app.logger.error(f"Failed to log activity: {str(e)}")


def get_user_activity_log(user_id=None, action=None, start_date=None, end_date=None, limit=100):
    """
    Retrieve activity log entries with optional filtering.
    
    Args:
        user_id (int, optional): Filter by specific user
        action (str, optional): Filter by specific action
        start_date (datetime, optional): Filter by start date
        end_date (datetime, optional): Filter by end date
        limit (int): Maximum number of entries to return
    
    Returns:
        list: List of ActivityLog objects
    """
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


def create_app(config_class=Config):
    """
    Factory function to create the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    db.init_app(app)
    # migrate = Migrate(app, db)  # Temporarily disabled due to import issues
    login_manager.init_app(app)

    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import and register blueprints
    from authroutes import auth_blueprint
    from studentroutes import student_blueprint
    from teacherroutes import teacher_blueprint
    from managementroutes import management_blueprint
    from techroutes import tech_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(student_blueprint, url_prefix='/student')
    app.register_blueprint(teacher_blueprint, url_prefix='/teacher')
    app.register_blueprint(management_blueprint, url_prefix='/management')
    app.register_blueprint(tech_blueprint, url_prefix='/tech')

    # Custom template filters
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Convert JSON string to Python object"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}

    # Add CSP headers to allow necessary JavaScript execution
    @app.after_request
    def add_security_headers(response):
        # Set Content Security Policy to allow inline scripts and eval for necessary functionality
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response

    # Custom error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('home.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('home.html'), 500
        
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('home.html'), 403

    @app.route('/')
    def home():
        # Check for maintenance mode - handle case where table might not exist
        maintenance = None
        try:
            maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
        except Exception as e:
            # Table might not exist yet, continue without maintenance mode
            pass
        
        if maintenance and maintenance.end_time > datetime.now():
            # Debug logging for maintenance mode
            print(f"Maintenance mode active: {maintenance.is_active}")
            print(f"Maintenance end time: {maintenance.end_time}")
            print(f"Current time: {datetime.now()}")
            print(f"Allow tech access: {maintenance.allow_tech_access}")
            if current_user.is_authenticated:
                print(f"User authenticated: {current_user.username}, Role: {current_user.role}")
            else:
                print("User not authenticated")
            
            # Allow tech users to bypass maintenance mode
            if current_user.is_authenticated and current_user.role in ['Tech', 'IT Support', 'Director'] and maintenance.allow_tech_access:
                print("Tech user bypassing maintenance mode")
                return render_template('home.html')
            
            # Calculate progress percentage
            total_duration = (maintenance.end_time - maintenance.start_time).total_seconds()
            elapsed = (datetime.now() - maintenance.start_time).total_seconds()
            progress_percentage = min(100, max(0, int((elapsed / total_duration) * 100)))
            
            return render_template('maintenance.html', 
                                 maintenance=maintenance, 
                                 progress_percentage=progress_percentage)
        
        return render_template('home.html')

    @app.route('/assignment/file/<int:assignment_id>')
    @login_required
    def download_assignment_file(assignment_id):
        """Download assignment file"""
        from flask import send_file, abort
        from models import Assignment
        
        assignment = Assignment.query.get_or_404(assignment_id)
        
        if not assignment.attachment_file_path or not os.path.exists(assignment.attachment_file_path):
            abort(404)
        
        try:
            return send_file(
                assignment.attachment_file_path,
                as_attachment=True,
                download_name=assignment.attachment_original_filename or assignment.attachment_filename
            )
        except Exception as e:
            current_app.logger.error(f"Error serving assignment file: {e}")
            abort(404)

    # Start GPA scheduler in development mode
    if app.config.get('ENV') == 'development':
        try:
            from gpa_scheduler import start_gpa_scheduler
            start_gpa_scheduler()
            print("GPA scheduler started successfully.")
        except Exception as e:
            print(f"Failed to start GPA scheduler: {e}")
    
    return app
