import os
import json
from flask import Flask, render_template, g, current_app, redirect, url_for, flash, request, session, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash
from config import Config, ProductionConfig, DevelopmentConfig, TestingConfig
from sqlalchemy import func, and_, text
from datetime import datetime, timezone

# Import extensions to avoid circular imports
from extensions import db, login_manager, csrf
from flask_migrate import Migrate

# Import models here to avoid circular imports
from models import User, Student, Grade, SchoolYear, ReportCard, Assignment, Notification, MaintenanceMode, ActivityLog, AssignmentExtension, QuarterGrade, Class, Enrollment, AcademicPeriod

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
    Only calculates grades if the quarter has ended according to AcademicPeriod dates.
    """
    from datetime import date
    from models import AcademicPeriod
    
    student = Student.query.get(student_id)
    if not student:
        return {}

    # Check if the quarter has ended before calculating grades
    quarter_period = AcademicPeriod.query.filter_by(
        school_year_id=school_year_id,
        name=f"Q{quarter}",
        period_type='quarter',
        is_active=True
    ).first()
    
    if quarter_period:
        today = date.today()
        if today < quarter_period.end_date:
            current_app.logger.info(f"Quarter Q{quarter} has not ended yet (ends {quarter_period.end_date}). Grade calculation skipped.")
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


def run_production_database_fix():
    """
    Run production database fix to add missing columns.
    Only runs in production environment when DATABASE_URL is available.
    """
    # Check if we're in production environment
    if not os.getenv('DATABASE_URL'):
        return
    
    # Check if we're running on Render (production)
    if not os.getenv('RENDER'):
        return
    
    print("Running production database fix...")
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Get database URL
        database_url = os.getenv('DATABASE_URL')
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgres://')
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'assignment' 
            AND column_name IN ('allow_save_and_continue', 'max_save_attempts', 'save_timeout_minutes')
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add missing columns
        columns_to_add = []
        
        if 'allow_save_and_continue' not in existing_columns:
            columns_to_add.append("allow_save_and_continue BOOLEAN DEFAULT FALSE")
            
        if 'max_save_attempts' not in existing_columns:
            columns_to_add.append("max_save_attempts INTEGER DEFAULT 3")
            
        if 'save_timeout_minutes' not in existing_columns:
            columns_to_add.append("save_timeout_minutes INTEGER DEFAULT 30")
        
        if not columns_to_add:
            print("All required columns already exist")
            cursor.close()
            conn.close()
            return
        
        # Add missing columns
        for column_def in columns_to_add:
            column_name = column_def.split()[0]
            print(f"Adding column: {column_name}")
            cursor.execute(f"ALTER TABLE assignment ADD COLUMN {column_def}")
            print(f"Added column: {column_name}")
        
        cursor.close()
        conn.close()
        print("Production database fix completed successfully!")
        
    except ImportError:
        print("psycopg2 not available, skipping database fix")
    except Exception as e:
        print(f"Database fix failed: {e}")

def create_app(config_class=None):
    """
    Factory function to create the Flask application.
    Automatically selects configuration based on environment.
    """
    if config_class is None:
        # Auto-detect environment and select appropriate config
        env = os.environ.get('FLASK_ENV', 'production').lower()
        if env == 'development':
            config_class = DevelopmentConfig
        elif env == 'testing':
            config_class = TestingConfig
        else:
            config_class = ProductionConfig  # Default to production for security
    
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    # Disable automatic CSRF token rendering
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    
    # Initialize database schema
    with app.app_context():
        try:
            # Initialize database tables
            db.create_all()
            print("Database tables created successfully")
            
            # Fix class table schema if needed
            try:
                from sqlalchemy import inspect, text
                inspector = inspect(db.engine)
                
                if 'class' in inspector.get_table_names():
                    columns = [col['name'] for col in inspector.get_columns('class')]
                    missing_columns = []
                    
                    required_columns = ['room_number', 'schedule', 'max_students', 'description', 'is_active', 'created_at', 'updated_at']
                    for col in required_columns:
                        if col not in columns:
                            missing_columns.append(col)
                    
                    if missing_columns:
                        print(f"Adding missing class table columns: {missing_columns}")
                        
                        # Check database type for correct SQL syntax
                        db_url = str(db.engine.url)
                        is_postgres = 'postgresql' in db_url
                        
                        with db.engine.connect() as connection:
                            for col in missing_columns:
                                try:
                                    if col == 'room_number':
                                        connection.execute(text("ALTER TABLE class ADD COLUMN room_number VARCHAR(20)"))
                                    elif col == 'schedule':
                                        connection.execute(text("ALTER TABLE class ADD COLUMN schedule VARCHAR(200)"))
                                    elif col == 'max_students':
                                        connection.execute(text("ALTER TABLE class ADD COLUMN max_students INTEGER DEFAULT 30"))
                                    elif col == 'description':
                                        connection.execute(text("ALTER TABLE class ADD COLUMN description TEXT"))
                                    elif col == 'is_active':
                                        connection.execute(text("ALTER TABLE class ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                                    elif col == 'created_at':
                                        if is_postgres:
                                            connection.execute(text("ALTER TABLE class ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                                        else:
                                            connection.execute(text("ALTER TABLE class ADD COLUMN created_at DATETIME"))
                                    elif col == 'updated_at':
                                        if is_postgres:
                                            connection.execute(text("ALTER TABLE class ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                                        else:
                                            connection.execute(text("ALTER TABLE class ADD COLUMN updated_at DATETIME"))
                                    print(f"Added column: {col}")
                                except Exception as col_error:
                                    print(f"Error adding column {col}: {col_error}")
                            connection.commit()
                        print("Class table schema updated successfully")
                    else:
                        print("Class table schema is up to date")
                        
            except Exception as schema_error:
                print(f"Error updating class table schema: {schema_error}")
                
        except Exception as e:
            # Re-raise the exception immediately to force a visible traceback in the console.
            print(f"FATAL DATABASE ERROR DURING INITIALIZATION: {e}")
            raise e  # <- CRITICAL: Re-raises the error to kill the process and dump the traceback.
        
        # Run production database fix if needed
        try:
            run_production_database_fix()
        except Exception as e:
            print(f"Production database fix failed: {e}")

    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import and register blueprints
    from authroutes import auth_blueprint
    from studentroutes import student_blueprint
    from teacher_routes import teacher_blueprint  # Using new modular teacher_routes package
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
    
    @app.template_filter('display_grade')
    def display_grade_filter(grade_level):
        """Display grade level with proper formatting (0 -> K, None -> N/A)"""
        if grade_level == 0:
            return 'K'
        elif grade_level:
            return str(grade_level)
        else:
            return 'N/A'
    
    @app.template_filter('nl2br')
    def nl2br_filter(value):
        """Convert newlines to <br> tags"""
        from markupsafe import Markup
        if value is None:
            return Markup('')
        # Convert newlines to <br> tags and mark as safe HTML
        html = str(value).replace('\r\n', '<br>\n').replace('\n', '<br>\n').replace('\r', '<br>\n')
        return Markup(html)

    # Add CSP headers to allow necessary JavaScript execution
    @app.after_request
    def add_security_headers(response):
        # Set Content Security Policy to allow inline scripts and eval for necessary functionality
        # Using a more permissive policy to resolve CSP issues
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "connect-src 'self' https:;"
        )
        return response

    # Custom error handlers
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors by redirecting to login page."""
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth.login'))
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors by redirecting to login page."""
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors by redirecting to home page."""
        return redirect(url_for('auth.home'))

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        db.session.rollback()
        return render_template('shared/home.html'), 500
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """Handle CSRF errors."""
        flash('Invalid request. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    @app.route('/')
    def home():
        # Check for maintenance mode - handle case where table might not exist
        maintenance = None
        try:
            maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
        except Exception as e:
            # Table might not exist yet, continue without maintenance mode
            pass
        
        if maintenance and maintenance.end_time > datetime.now(timezone.utc):
            # Debug logging for maintenance mode
            print(f"Maintenance mode active: {maintenance.is_active}")
            print(f"Maintenance end time: {maintenance.end_time}")
            print(f"Current time: {datetime.now()}")
            print(f"Allow tech access: {maintenance.allow_tech_access}")
            if current_user.is_authenticated:
                print(f"User authenticated: {current_user.username}, Role: {current_user.role}")
            else:
                print("User not authenticated")
            
            # Allow tech users to bypass maintenance mode (always allowed)
            if current_user.is_authenticated and current_user.role in ['Tech', 'IT Support', 'Director']:
                print("Tech user bypassing maintenance mode")
                return render_template('shared/home.html')
            
            # Calculate progress percentage using UTC time
            total_duration = (maintenance.end_time - maintenance.start_time).total_seconds()
            elapsed = (datetime.now(timezone.utc) - maintenance.start_time).total_seconds()
            progress_percentage = min(100, max(0, int((elapsed / total_duration) * 100)))
            
            return render_template('shared/maintenance.html', 
                                 maintenance=maintenance, 
                                 progress_percentage=progress_percentage)
        
        return render_template('shared/home.html')

    @app.route('/assignment/file/<int:assignment_id>')
    @login_required
    def download_assignment_file(assignment_id):
        """Download assignment file"""
        from flask import send_file, abort
        from models import Assignment
        import os
        
        assignment = Assignment.query.get_or_404(assignment_id)
        
        if not assignment.attachment_filename:
            abort(404, description="No attachment found for this assignment")
        
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], assignment.attachment_filename)
        
        if not os.path.exists(file_path):
            abort(404, description="File not found")
        
        try:
            return send_file(
                file_path,
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
    
    # Temporary migration route for grade_levels column
    @app.route('/migrate/add-grade-levels')
    def add_grade_levels_migration():
        """Migration route to add grade_levels column to class table"""
        try:
            from sqlalchemy import text
            
            # Check if the column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'class' AND column_name = 'grade_levels'
            """))
            
            if result.fetchone():
                flash('grade_levels column already exists in class table', 'info')
                return redirect(url_for('management.classes'))
            
            # Add the grade_levels column
            db.session.execute(text("ALTER TABLE class ADD COLUMN grade_levels VARCHAR(100)"))
            db.session.commit()
            
            flash('Successfully added grade_levels column to class table! You can now uncomment the grade_levels field in models.py', 'success')
            return redirect(url_for('management.classes'))
            
        except Exception as e:
            flash(f'Error adding grade_levels column: {str(e)}', 'danger')
            return redirect(url_for('management.classes'))
    
    @app.route('/migrate/create-missing-tables')
    @login_required
    def create_missing_tables():
        """Create missing tables for group work and deadline reminders."""
        if current_user.role not in ['School Administrator', 'Director', 'Tech']:
            flash('Access denied. Only administrators can run migrations.', 'danger')
            return redirect(url_for('auth.dashboard'))
        
        try:
            # Import the models to ensure they're registered
            from models import (
                DeadlineReminder, ReminderNotification, 
                StudentGroup, StudentGroupMember, GroupAssignment, 
                GroupSubmission, GroupGrade, GroupTemplate, GroupContract,
                GroupRotation, GroupRotationHistory, PeerEvaluation,
                AssignmentRubric, AssignmentTemplate, GroupProgress,
                GroupWorkReport, IndividualContribution, TimeTracking,
                CollaborationMetrics, ReportExport, AnalyticsDashboard,
                PerformanceBenchmark, Feedback360, Feedback360Response,
                Feedback360Criteria, GroupConflict, ConflictResolution,
                ConflictParticipant, ReflectionJournal, DraftSubmission,
                DraftFeedback, DeadlineReminder, ReminderNotification
            )
            
            # Create all tables
            db.create_all()
            
            flash('Successfully created all missing tables! Group work and deadline reminder features should now work.', 'success')
            return redirect(url_for('management.management_dashboard'))
            
        except Exception as e:
            flash(f'Error creating missing tables: {str(e)}', 'danger')
            return redirect(url_for('management.management_dashboard'))
    
    @app.route('/migrate/add-temporary-password-fields')
    @login_required
    def add_temporary_password_fields():
        """Add temporary password fields to the User table."""
        if current_user.role not in ['School Administrator', 'Director', 'Tech']:
            flash('Access denied. Only administrators can run migrations.', 'danger')
            return redirect(url_for('auth.dashboard'))
        
        try:
            # Check if columns already exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user' 
                AND column_name IN ('is_temporary_password', 'password_changed_at', 'created_at')
            """))
            
            existing_columns = [row[0] for row in result]
            
            # Add is_temporary_password column if it doesn't exist
            if 'is_temporary_password' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN is_temporary_password BOOLEAN DEFAULT FALSE NOT NULL
                """))
                db.session.commit()
                flash('Added is_temporary_password column to User table', 'success')
            else:
                flash('is_temporary_password column already exists', 'info')
            
            # Add password_changed_at column if it doesn't exist
            if 'password_changed_at' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN password_changed_at TIMESTAMP
                """))
                db.session.commit()
                flash('Added password_changed_at column to User table', 'success')
            else:
                flash('password_changed_at column already exists', 'info')
            
            # Add created_at column if it doesn't exist
            if 'created_at' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                """))
                db.session.commit()
                flash('Added created_at column to User table', 'success')
            else:
                flash('created_at column already exists', 'info')
            
            flash('Temporary password fields migration completed successfully!', 'success')
            return redirect(url_for('management.management_dashboard'))
            
        except Exception as e:
            flash(f'Error adding temporary password fields: {str(e)}', 'danger')
            return redirect(url_for('management.management_dashboard'))
    
    # Register global error handlers
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 server errors."""
        # Log error for debugging
        print(f"500 Error: {error}")
        
        # Return user-friendly error page
        return render_template('shared/error.html', 
                             error_code=500,
                             error_message="An internal server error occurred. Please try again later.",
                             bug_report_id=None), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('shared/error.html', 
                             error_code=404,
                             error_message="The page you're looking for doesn't exist.",
                             bug_report_id=None), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 forbidden errors."""
        return render_template('shared/error.html', 
                             error_code=403,
                             error_message="You don't have permission to access this resource.",
                             bug_report_id=None), 403
    
    @app.errorhandler(CSRFError)
    def csrf_error(error):
        """Handle CSRF errors."""
        flash('CSRF token missing or invalid. Please try again.', 'danger')
        return redirect(request.url or url_for('home'))
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle any unexpected errors."""
        print(f"Unexpected error: {error}")
        return render_template('shared/error.html', 
                             error_code=500,
                             error_message="An unexpected error occurred. Please try again later.",
                             bug_report_id=None), 500

    # API endpoint for frontend error reporting (simplified)
    @app.route('/api/frontend-error', methods=['POST'])
    def frontend_error_report():
        """Handle frontend error reports from JavaScript."""
        try:
            error_data = request.get_json()
            if not error_data:
                return jsonify({'success': False, 'message': 'No error data provided'}), 400
            
            # Just log the error for now
            print(f"Frontend error: {error_data.get('message', 'Unknown error')}")
            
            return jsonify({
                'success': True, 
                'message': 'Error logged successfully'
            }), 200
                
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    return app
