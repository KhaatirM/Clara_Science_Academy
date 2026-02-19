import os
import json
from flask import Flask, render_template, g, current_app, redirect, url_for, flash, request, session, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config, ProductionConfig, DevelopmentConfig, TestingConfig
from sqlalchemy import func, and_, text
from datetime import datetime, timezone
from decorators import is_teacher_role

# Import extensions to avoid circular imports
from extensions import db, login_manager, csrf
from flask_migrate import Migrate

# Import models here to avoid circular imports
from models import User, Student, Grade, SchoolYear, ReportCard, Assignment, Notification, MaintenanceMode, ActivityLog, AssignmentExtension, QuarterGrade, Class, Enrollment, AcademicPeriod

# Re-export services so "from app import create_notification" etc. still work
from services import (
    get_grade_for_student,
    calculate_and_get_grade_for_student,
    create_notification,
    create_notifications_for_users,
    create_notification_for_students_in_class,
    create_notification_for_all_students,
    create_notification_for_all_teachers,
    create_digest_notifications,
    create_grade_update_digest,
    log_activity,
    get_user_activity_log,
)
from database_utils import run_production_database_fix


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

    # ----------------------------------------------------------------------
    # START OF FIX: Trust Render's Load Balancer Headers
    # ----------------------------------------------------------------------
    # This tells Flask to trust the X-Forwarded-Proto header set by Render
    # so it knows it is running behind HTTPS.
    app.wsgi_app = ProxyFix(
        app.wsgi_app, 
        x_for=1, 
        x_proto=1, 
        x_host=1, 
        x_prefix=1
    )
    # ----------------------------------------------------------------------
    # END OF FIX
    # ----------------------------------------------------------------------

    # Initialize extensions with the app
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Initialize database schema (no ALTER TABLE here; use Flask-Migrate for schema changes)
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"FATAL DATABASE ERROR DURING INITIALIZATION: {e}")
            raise e
        
        # Add user.theme_preference column if missing (one-off migration for themes feature)
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(user)"))
                    columns = [row[1] for row in r]
                    if 'theme_preference' not in columns:
                        conn.execute(text("ALTER TABLE user ADD COLUMN theme_preference VARCHAR(50)"))
                        conn.commit()
                        print("Added user.theme_preference column.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'user' AND column_name = 'theme_preference'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN theme_preference VARCHAR(50)'))
                        conn.commit()
                        print("Added user.theme_preference column.")
        except Exception as e:
            print(f"Note: theme_preference column check failed (may already exist): {e}")

        # Optional: run one-off production DB fix only when explicitly requested.
        # Prefer Flask-Migrate for schema changes: flask db migrate / flask db upgrade
        if os.environ.get('RUN_PRODUCTION_DB_FIX', '').strip() == '1':
            try:
                run_production_database_fix()
            except Exception as e:
                print(f"Production database fix failed: {e}")
                import traceback
                traceback.print_exc()

    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        if user:
            # Check if user has expired temporary access
            if user.teacher_staff_id:
                try:
                    from models import TeacherStaff
                    from datetime import datetime, timezone
                    teacher_staff = TeacherStaff.query.get(user.teacher_staff_id)
                    # Check if columns exist before accessing them
                    if teacher_staff and hasattr(teacher_staff, 'is_temporary') and hasattr(teacher_staff, 'access_expires_at'):
                        if teacher_staff.is_temporary and teacher_staff.access_expires_at:
                            # Handle both naive and aware datetimes
                            expires_at = teacher_staff.access_expires_at
                            now = datetime.now(timezone.utc)
                            
                            # If expires_at is naive, make it timezone-aware (assume UTC)
                            if expires_at.tzinfo is None:
                                expires_at = expires_at.replace(tzinfo=timezone.utc)
                            
                            if expires_at < now:
                                # Access has expired - return None to prevent login
                                return None
                except Exception as e:
                    # If there's an error accessing temporary access fields (e.g., column doesn't exist yet),
                    # just continue and return the user - migration will fix it on next startup
                    print(f"Warning: Could not check temporary access: {e}")
        return user

    # Import and register blueprints
    from authroutes import auth_blueprint
    from studentroutes import student_blueprint
    from teacher_routes import teacher_blueprint  # Using new modular teacher_routes package
    from management_routes import management_blueprint  # Using new modular management_routes package
    from techroutes import tech_blueprint
    from communications_api import api_bp as communications_api_bp
    from shared_communications import bp as shared_communications_bp
    
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(student_blueprint, url_prefix='/student')
    app.register_blueprint(teacher_blueprint, url_prefix='/teacher')
    app.register_blueprint(management_blueprint, url_prefix='/management')
    app.register_blueprint(tech_blueprint, url_prefix='/tech')
    app.register_blueprint(communications_api_bp)  # Communications API - no prefix, uses absolute paths
    app.register_blueprint(shared_communications_bp)  # Shared communications routes

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

    @app.template_filter('discussion_content')
    def discussion_content_filter(value):
        """Render discussion content: plain text or code block with line numbers.
        Code content starts with [DISCUSSION_CODE:lang] on the first line."""
        from markupsafe import Markup, escape
        if value is None:
            return Markup('')
        s = str(value)
        code_prefix = '[DISCUSSION_CODE:'
        if s.startswith(code_prefix):
            try:
                end = s.index(']')
                lang = s[len(code_prefix):end].strip() or 'text'
                body = s[end + 1:].lstrip('\n\r')
                # Split into lines and escape each for XSS safety
                lines = body.split('\n')
                line_nums_html = '\n'.join(str(i + 1) for i in range(len(lines)))
                code_html = '\n'.join(escape(line) for line in lines)
                html = (
                    f'<div class="discussion-code-block" data-lang="{escape(lang)}">'
                    f'<span class="code-lang-badge">{escape(lang)}</span>'
                    f'<div class="code-block-wrapper">'
                    f'<pre class="line-numbers">\n{line_nums_html}\n</pre>'
                    f'<pre class="code-content"><code>{code_html}</code></pre>'
                    f'</div></div>'
                )
                return Markup(html)
            except (ValueError, IndexError):
                pass
        # Plain text: escape and convert newlines to <br>
        escaped = escape(s)
        html = escaped.replace('\r\n', '<br>\n').replace('\n', '<br>\n').replace('\r', '<br>\n')
        return Markup(html)

    @app.template_filter('discussion_preview')
    def discussion_preview_filter(value, maxlen=200):
        """Return plain-text preview for discussion list (strips code prefix if present)."""
        if value is None:
            return ''
        s = str(value).strip()
        if s.startswith('[DISCUSSION_CODE:'):
            try:
                end = s.index(']')
                lang = s[len('[DISCUSSION_CODE:'):end].strip()
                body = s[end + 1:].lstrip('\n\r')
                prefix = f'[{lang} code] '
                preview = (prefix + body)[:maxlen]
                return preview + ('...' if len(prefix + body) > maxlen else '')
            except (ValueError, IndexError):
                pass
        return s[:maxlen] + ('...' if len(s) > maxlen else '')

    # Inject effective theme into all templates (site override from tech, or user preference)
    @app.context_processor
    def inject_theme():
        from models import SystemConfig
        effective = 'default'
        if current_user.is_authenticated:
            site_override = SystemConfig.get_value('site_theme_override')
            if site_override:
                effective = site_override
            else:
                pref = getattr(current_user, 'theme_preference', None)
                if pref:
                    effective = pref
        return {'effective_theme': effective}

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
        """Handle 403 Forbidden errors by redirecting to appropriate dashboard."""
        flash('You do not have permission to access this page.', 'danger')
        
        # If user is authenticated, redirect to their appropriate dashboard
        if current_user.is_authenticated:
            role = current_user.role
            
            # Determine the correct dashboard based on role
            if role == 'Student':
                return redirect(url_for('student.student_dashboard'))
            elif is_teacher_role(role) or role in ['School Administrator', 'Director']:
                # For teachers and admins, check if they should go to teacher or management dashboard
                if role in ['School Administrator', 'Director']:
                    return redirect(url_for('management.management_dashboard'))
                else:
                    return redirect(url_for('teacher.dashboard.teacher_dashboard'))
            elif role in ['Tech', 'IT Support']:
                return redirect(url_for('tech.tech_dashboard'))
        
        # If not authenticated, redirect to login
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
            
            # Allow tech users and administrators to bypass maintenance mode (always allowed)
            if current_user.is_authenticated and current_user.role in ['Tech', 'IT Support', 'Director', 'School Administrator']:
                print("Tech/Admin user bypassing maintenance mode")
                return render_template('shared/home.html')
            
            # Calculate progress percentage using UTC time
            total_duration = (maintenance.end_time - maintenance.start_time).total_seconds()
            elapsed = (datetime.now(timezone.utc) - maintenance.start_time).total_seconds()
            progress_percentage = min(100, max(0, int((elapsed / total_duration) * 100)))
            
            return render_template('shared/maintenance.html', 
                                 maintenance=maintenance, 
                                 progress_percentage=progress_percentage)
        
        return render_template('shared/home.html')

    def _resolve_assignment_file_path(upload_folder, filename, file_path_stored=None):
        """Resolve actual file path: try stored path, then assignments subfolder, then root."""
        import os
        if file_path_stored and os.path.exists(file_path_stored):
            return file_path_stored
        if not filename:
            return None
        for candidate in [
            os.path.join(upload_folder, 'assignments', filename),
            os.path.join(upload_folder, filename),
        ]:
            if os.path.exists(candidate):
                return candidate
        return None

    @app.route('/assignment/file/<int:assignment_id>')
    @login_required
    def download_assignment_file(assignment_id):
        """Download or view assignment file. Use ?index=N for Nth document when multiple are attached."""
        from flask import send_file, abort, request
        from models import Assignment, Enrollment, AssignmentAttachment
        import os

        assignment = Assignment.query.get_or_404(assignment_id)
        class_obj = assignment.class_info

        # Check authorization - teachers/admins can view files for their classes
        if class_obj:
            # Directors and School Administrators have access
            if current_user.role in ['Director', 'School Administrator']:
                pass  # Authorized
            elif current_user.role == 'Student':
                # Check if student is enrolled in the class
                enrollment = Enrollment.query.filter_by(
                    class_id=class_obj.id,
                    student_id=current_user.student_id if hasattr(current_user, 'student_id') else None,
                    is_active=True
                ).first()
                if not enrollment:
                    abort(403, description="You are not authorized to access this file")
            else:
                # For teachers, check if they're assigned to the class
                from models import TeacherStaff, class_additional_teachers, class_substitute_teachers

                teacher = None
                if current_user.teacher_staff_id:
                    teacher = TeacherStaff.query.get(current_user.teacher_staff_id)

                if not teacher:
                    abort(403, description="You are not authorized to access this file")

                # Check if teacher is primary, additional, or substitute
                is_authorized = (
                    class_obj.teacher_id == teacher.id or
                    db.session.query(class_additional_teachers).filter(
                        class_additional_teachers.c.class_id == class_obj.id,
                        class_additional_teachers.c.teacher_id == teacher.id
                    ).count() > 0 or
                    db.session.query(class_substitute_teachers).filter(
                        class_substitute_teachers.c.class_id == class_obj.id,
                        class_substitute_teachers.c.teacher_id == teacher.id
                    ).count() > 0
                )

                if not is_authorized:
                    abort(403, description="You are not authorized to access this file")

        # Build list of documents: use attachment_list if any, else legacy single attachment
        docs = []
        upload_folder = current_app.config['UPLOAD_FOLDER']
        attachment_list = list(assignment.attachment_list or [])

        if attachment_list:
            for att in attachment_list:
                path = _resolve_assignment_file_path(
                    upload_folder,
                    att.attachment_filename,
                    att.attachment_file_path
                )
                if path:
                    docs.append({
                        'path': path,
                        'original_filename': att.attachment_original_filename or att.attachment_filename,
                        'mime_type': att.attachment_mime_type,
                    })
        elif assignment.attachment_filename:
            path = _resolve_assignment_file_path(
                upload_folder,
                assignment.attachment_filename,
                assignment.attachment_file_path
            )
            if path:
                docs.append({
                    'path': path,
                    'original_filename': assignment.attachment_original_filename or assignment.attachment_filename,
                    'mime_type': assignment.attachment_mime_type,
                })

        if not docs:
            abort(404, description="No attachment found for this assignment")

        index = request.args.get('index', type=int, default=0)
        if index < 0 or index >= len(docs):
            index = 0
        doc = docs[index]

        file_path = doc['path']
        if not os.path.exists(file_path):
            abort(404, description="File not found")

        view_mode = request.args.get('view', 'false').lower() == 'true'
        is_pdf = doc['mime_type'] and 'pdf' in (doc['mime_type'] or '').lower()

        try:
            if view_mode and is_pdf:
                return send_file(
                    file_path,
                    as_attachment=False,
                    mimetype=doc['mime_type'] or 'application/pdf'
                )
            else:
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=doc['original_filename']
                )
        except Exception as e:
            current_app.logger.error(f"Error serving assignment file: {e}")
            abort(404)

    # Start GPA scheduler in development mode
    if app.config.get('ENV') == 'development':
        try:
            from scripts.gpa_scheduler import start_gpa_scheduler
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
                StudentGroup, StudentGroupMember, GroupAssignment, GroupAssignmentExtension,
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
    
    # Removed duplicate 403 handler - using the one above that redirects appropriately
    
    @app.errorhandler(CSRFError)
    def csrf_error(error):
        """Handle CSRF errors."""
        flash('CSRF token missing or invalid. Please try again.', 'danger')
        return redirect(request.url or url_for('home'))
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle any unexpected errors."""
        import traceback
        print(f"Unexpected error: {error}")
        traceback.print_exc()
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

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # This block only runs if you execute 'python app.py' directly
    app.run(debug=True, port=5000)