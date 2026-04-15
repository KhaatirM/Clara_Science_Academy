import os
import json
from flask import Flask, render_template, g, current_app, redirect, url_for, flash, request, session, jsonify, abort
from flask_login import current_user, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config, ProductionConfig, DevelopmentConfig, TestingConfig
from sqlalchemy import func, and_, text
from datetime import datetime, timezone
from decorators import is_teacher_role

# Import extensions to avoid circular imports
from extensions import db, login_manager, csrf, mail
from flask_migrate import Migrate

# Import models here to avoid circular imports
from models import User, Student, Grade, SchoolYear, ReportCard, Assignment, Notification, MaintenanceMode, ActivityLog, AssignmentExtension, QuarterGrade, Class, Enrollment, AcademicPeriod, RedoRequest

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
    mail.init_app(app)
    
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

        # Add user.low_grade_threshold column if missing (for student "Grades to Improve" feature)
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(user)"))
                    columns = [row[1] for row in r]
                    if 'low_grade_threshold' not in columns:
                        conn.execute(text("ALTER TABLE user ADD COLUMN low_grade_threshold INTEGER"))
                        conn.commit()
                        print("Added user.low_grade_threshold column.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'user' AND column_name = 'low_grade_threshold'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN low_grade_threshold INTEGER'))
                        conn.commit()
                        print("Added user.low_grade_threshold column.")
        except Exception as e:
            print(f"Note: low_grade_threshold column check failed (may already exist): {e}")

        # Add student profile confirmation columns if missing (report cards + enrollment policy)
        _student_cols = [
            ('gender', 'VARCHAR(30)', 'TEXT'),
            ('entrance_date', 'VARCHAR(9)', 'TEXT'),
            ('expected_grad_date', 'VARCHAR(7)', 'TEXT'),
        ]
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                for col_name, pg_type, sqlite_type in _student_cols:
                    if dialect == 'sqlite':
                        r = conn.execute(text("PRAGMA table_info(student)"))
                        columns = [row[1] for row in r]
                        if col_name not in columns:
                            conn.execute(text(
                                f"ALTER TABLE student ADD COLUMN {col_name} {sqlite_type}"
                            ))
                            conn.commit()
                            print(f"Added student.{col_name} column.")
                    elif dialect == 'postgresql':
                        r = conn.execute(text(
                            "SELECT 1 FROM information_schema.columns "
                            "WHERE table_name = 'student' AND column_name = :col"
                        ), {"col": col_name})
                        if r.fetchone() is None:
                            conn.execute(text(
                                f'ALTER TABLE "student" ADD COLUMN {col_name} {pg_type}'
                            ))
                            conn.commit()
                            print(f"Added student.{col_name} column.")
        except Exception as e:
            print(f"Note: student profile columns check failed (may already exist): {e}")

        # Add assignment advanced grading columns if missing
        _assignment_cols = [
            ('allow_extra_credit', 'BOOLEAN DEFAULT FALSE', 'INTEGER DEFAULT 0'),
            ('max_extra_credit_points', 'DOUBLE PRECISION DEFAULT 0.0', 'REAL DEFAULT 0.0'),
            ('late_penalty_enabled', 'BOOLEAN DEFAULT FALSE', 'INTEGER DEFAULT 0'),
            ('late_penalty_per_day', 'DOUBLE PRECISION DEFAULT 0.0', 'REAL DEFAULT 0.0'),
            ('late_penalty_max_days', 'INTEGER DEFAULT 0', 'INTEGER DEFAULT 0'),
        ]
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                for col_name, pg_type, sqlite_type in _assignment_cols:
                    if dialect == 'sqlite':
                        r = conn.execute(text("PRAGMA table_info(assignment)"))
                        columns = [row[1] for row in r]
                        if col_name not in columns:
                            conn.execute(text(
                                f"ALTER TABLE assignment ADD COLUMN {col_name} {sqlite_type}"
                            ))
                            conn.commit()
                            print(f"Added assignment.{col_name} column.")
                    elif dialect == 'postgresql':
                        r = conn.execute(text(
                            "SELECT 1 FROM information_schema.columns "
                            "WHERE table_name = 'assignment' AND column_name = :col"
                        ), {"col": col_name})
                        if r.fetchone() is None:
                            conn.execute(text(
                                f'ALTER TABLE "assignment" ADD COLUMN {col_name} {pg_type}'
                            ))
                            conn.commit()
                            print(f"Added assignment.{col_name} column.")
        except Exception as e:
            print(f"Note: assignment advanced grading columns check failed (may already exist): {e}")

        # Add assignment.status_override and status_override_until if missing (for temporary status overrides)
        for table_name in ('assignment', 'group_assignment'):
            try:
                with db.engine.connect() as conn:
                    dialect = db.engine.dialect.name
                    if dialect == 'sqlite':
                        r = conn.execute(text(f"PRAGMA table_info({table_name})"))
                        columns = [row[1] for row in r]
                        if 'status_override' not in columns:
                            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN status_override VARCHAR(20)"))
                            conn.commit()
                            print(f"Added {table_name}.status_override column.")
                        if 'status_override_until' not in columns:
                            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN status_override_until TIMESTAMP"))
                            conn.commit()
                            print(f"Added {table_name}.status_override_until column.")
                    elif dialect == 'postgresql':
                        for col_name, col_type in [('status_override', 'VARCHAR(20)'), ('status_override_until', 'TIMESTAMP')]:
                            r = conn.execute(text(
                                "SELECT 1 FROM information_schema.columns "
                                "WHERE table_name = :tbl AND column_name = :col"
                            ), {"tbl": table_name, "col": col_name})
                            if r.fetchone() is None:
                                conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {col_name} {col_type}'))
                                conn.commit()
                                print(f"Added {table_name}.{col_name} column.")
            except Exception as e:
                print(f"Note: {table_name} status_override columns check failed (may already exist): {e}")

        # Student assistant assignment approval columns (assignment + group_assignment)
        _assistant_cols = [
            ('assistant_approval_status', 'VARCHAR(20)', 'TEXT'),
            ('proposed_by_student_id', 'INTEGER', 'INTEGER'),
            ('assistant_approval_reviewed_by_user_id', 'INTEGER', 'INTEGER'),
            ('assistant_approval_reviewed_at', 'TIMESTAMP', 'TIMESTAMP'),
            ('assistant_approval_review_notes', 'TEXT', 'TEXT'),
        ]
        for table_name in ('assignment', 'group_assignment'):
            try:
                with db.engine.connect() as conn:
                    dialect = db.engine.dialect.name
                    for col_name, pg_type, sqlite_type in _assistant_cols:
                        if dialect == 'sqlite':
                            r = conn.execute(text(f"PRAGMA table_info({table_name})"))
                            columns = [row[1] for row in r]
                            if col_name not in columns:
                                conn.execute(text(
                                    f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sqlite_type}"
                                ))
                                conn.commit()
                                print(f"Added {table_name}.{col_name} column.")
                        elif dialect == 'postgresql':
                            r = conn.execute(text(
                                "SELECT 1 FROM information_schema.columns "
                                "WHERE table_name = :tbl AND column_name = :col"
                            ), {"tbl": table_name, "col": col_name})
                            if r.fetchone() is None:
                                conn.execute(text(
                                    f'ALTER TABLE "{table_name}" ADD COLUMN {col_name} {pg_type}'
                                ))
                                conn.commit()
                                print(f"Added {table_name}.{col_name} column.")
            except Exception as e:
                print(f"Note: {table_name} assistant approval columns check failed (may already exist): {e}")

        # Create redo_request table if missing (for student redo requests on inactive assignments)
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='redo_request'"))
                    if r.fetchone() is None:
                        conn.execute(text("""
                            CREATE TABLE redo_request (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                assignment_id INTEGER NOT NULL REFERENCES assignment(id),
                                student_id INTEGER NOT NULL REFERENCES student(id),
                                reason TEXT,
                                status VARCHAR(20) DEFAULT 'Pending' NOT NULL,
                                requested_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                                reviewed_at DATETIME,
                                reviewed_by INTEGER REFERENCES teacher_staff(id),
                                review_notes TEXT
                            )
                        """))
                        conn.commit()
                        print("Created redo_request table.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.tables WHERE table_name = 'redo_request'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text("""
                            CREATE TABLE redo_request (
                                id SERIAL PRIMARY KEY,
                                assignment_id INTEGER NOT NULL REFERENCES assignment(id),
                                student_id INTEGER NOT NULL REFERENCES student(id),
                                reason TEXT,
                                status VARCHAR(20) DEFAULT 'Pending' NOT NULL,
                                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                                reviewed_at TIMESTAMP,
                                reviewed_by INTEGER REFERENCES teacher_staff(id),
                                review_notes TEXT
                            )
                        """))
                        conn.commit()
                        print("Created redo_request table.")
        except Exception as e:
            print(f"Note: redo_request table check failed (may already exist): {e}")

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
        # Guard against stale/corrupt session values (e.g., non-numeric _user_id).
        # Returning None here safely treats the session as unauthenticated
        # instead of raising a 500 during login restore.
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            app.logger.warning("Ignoring invalid session user id: %r", user_id)
            return None

        user = User.query.get(user_id_int)
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
    from management_routes.student_assistant_routes import bp as student_assistant_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(student_blueprint, url_prefix='/student')
    app.register_blueprint(teacher_blueprint, url_prefix='/teacher')
    app.register_blueprint(management_blueprint, url_prefix='/management')
    app.register_blueprint(tech_blueprint, url_prefix='/tech')
    app.register_blueprint(student_assistant_blueprint)  # /assistant/... for student assistants
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

    # Inject at_risk_alerts for teacher/admin dashboard pages (shown on all tabs)
    @app.context_processor
    def inject_at_risk_alerts():
        out = {'at_risk_alerts': [], 'failing_count': 0, 'overdue_count': 0}
        if not current_user.is_authenticated:
            return out
        role = getattr(current_user, 'role', '') or ''
        is_admin = role in ['Director', 'School Administrator']
        teacher_roles = ['History Teacher', 'Science Teacher', 'Physics Teacher',
                        'English Language Arts Teacher', 'Math Teacher', 'Substitute Teacher',
                        'School Counselor', 'School Administrator', 'Director']
        is_teacher = role in teacher_roles or 'Teacher' in role
        if not (is_teacher or is_admin):
            return out
        try:
            from utils.at_risk_alerts import get_at_risk_alerts_for_user
            alerts, failing, overdue = get_at_risk_alerts_for_user()
            return {'at_risk_alerts': alerts, 'failing_count': failing, 'overdue_count': overdue}
        except Exception as e:
            current_app.logger.warning(f"Context processor at_risk_alerts: {e}")
            return out

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

    @app.route('/', methods=['GET', 'POST'])
    def home():
        # Forms in base.html (contact, survey) have no action so submit to current URL.
        # They're meant to be handled by JS; if a POST reaches us, redirect to GET.
        if request.method == 'POST':
            return redirect(url_for('home'))
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
        """Resolve actual file path: try stored path (if on same host), stored as relative to UPLOAD_FOLDER,
        then assignments subfolder, then root. Stored paths from a different environment are ignored."""
        import os
        if file_path_stored and os.path.isabs(file_path_stored) and os.path.exists(file_path_stored):
            return file_path_stored
        upload_abs = os.path.abspath(upload_folder) if upload_folder else None
        if not upload_abs:
            return None
        # Try stored path as relative to UPLOAD_FOLDER (handles paths like "assignments/foo.pdf" across deploys)
        if file_path_stored and not os.path.isabs(file_path_stored):
            rel_candidate = os.path.normpath(os.path.join(upload_abs, file_path_stored))
            if os.path.exists(rel_candidate):
                return rel_candidate
        if not filename:
            return None
        # Prefer UPLOAD_FOLDER-based paths (portable across deploys); ignore stored abs path from other hosts
        candidates = [
            os.path.join(upload_abs, 'assignments', filename),
            os.path.join(upload_abs, 'group_assignments', filename),
            os.path.join(upload_abs, filename),
        ]
        if file_path_stored:
            base = os.path.basename(file_path_stored)
            if base and base != filename:
                candidates.insert(1, os.path.join(upload_abs, 'assignments', base))
                candidates.insert(2, os.path.join(upload_abs, 'group_assignments', base))
        for candidate in candidates:
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
        # Directors and School Administrators always have access (including when class_obj is None)
        if current_user.role in ['Director', 'School Administrator']:
            pass  # Authorized
        elif class_obj:
            if current_user.role == 'Student':
                # Students must use student.download_assignment_file; this route supports them for shared views
                student_id = getattr(current_user, 'student_id', None)
                if not student_id:
                    current_app.logger.warning(f"Student user {current_user.id} has no student_id linked")
                    abort(403, description="Your account is not properly linked. Please contact your administrator.")
                enrollment = Enrollment.query.filter_by(
                    class_id=class_obj.id,
                    student_id=student_id,
                    is_active=True
                ).first()
                if not enrollment:
                    abort(403, description="You are not enrolled in this class")
            else:
                # For teachers, check if they're assigned to the class
                from models import TeacherStaff, class_additional_teachers, class_substitute_teachers

                teacher = None
                if getattr(current_user, 'teacher_staff_id', None):
                    teacher = TeacherStaff.query.get(current_user.teacher_staff_id)

                if not teacher:
                    # Teacher without teacher_staff_id - log for debugging; still deny
                    current_app.logger.warning(f"Teacher user {current_user.id} has no teacher_staff_id")
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
        else:
            # No class_obj and user is not Director/School Administrator
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
            current_app.logger.warning(f"Assignment {assignment_id}: No attachment found (attachment_list={bool(attachment_list)}, legacy filename={assignment.attachment_filename})")
            abort(404, description="No attachment found for this assignment")

        index = request.args.get('index', type=int, default=0)
        if index < 0 or index >= len(docs):
            index = 0
        doc = docs[index]

        file_path = doc['path']
        if not os.path.exists(file_path):
            current_app.logger.warning(
                f"Assignment {assignment_id} file missing: path={file_path}, UPLOAD_FOLDER={upload_folder}. "
                "Uploads may be ephemeral (PaaS). Set UPLOAD_FOLDER to a persistent disk path."
            )
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

    @app.route('/group-assignment/file/<int:assignment_id>')
    @login_required
    def download_group_assignment_file(assignment_id):
        """Download or view a group assignment file."""
        from flask import send_file, abort, request
        from models import GroupAssignment, Enrollment
        import os

        group_assignment = GroupAssignment.query.get_or_404(assignment_id)
        class_obj = group_assignment.class_info

        # Authorization
        if current_user.role in ['Director', 'School Administrator']:
            pass
        elif class_obj:
            if current_user.role == 'Student':
                student_id = getattr(current_user, 'student_id', None)
                if not student_id:
                    abort(403, description="Your account is not properly linked. Please contact your administrator.")
                enrollment = Enrollment.query.filter_by(
                    class_id=class_obj.id,
                    student_id=student_id,
                    is_active=True
                ).first()
                if not enrollment:
                    abort(403, description="You are not enrolled in this class")
            else:
                from models import TeacherStaff, class_additional_teachers, class_substitute_teachers
                teacher = None
                if getattr(current_user, 'teacher_staff_id', None):
                    teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
                if not teacher:
                    abort(403, description="You are not authorized to access this file")

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
        else:
            abort(403, description="You are not authorized to access this file")

        file_path = _resolve_assignment_file_path(
            current_app.config['UPLOAD_FOLDER'],
            group_assignment.attachment_filename,
            group_assignment.attachment_file_path
        )
        if not file_path or not os.path.exists(file_path):
            abort(404, description="File not found")

        view_mode = request.args.get('view', 'false').lower() == 'true'
        mime = group_assignment.attachment_mime_type or ''
        is_pdf = ('pdf' in mime.lower()) or file_path.lower().endswith('.pdf')

        if view_mode and is_pdf:
            return send_file(file_path, as_attachment=False, mimetype=mime or 'application/pdf')

        return send_file(
            file_path,
            as_attachment=True,
            download_name=group_assignment.attachment_original_filename or group_assignment.attachment_filename or 'group_assignment_file'
        )

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

    @app.route('/cron/academic-period-reminders', methods=['POST'])
    @csrf.exempt
    def cron_academic_period_reminders():
        """
        Daily job: send 2-week-before-end reminders for quarters/semesters.
        Protect with CRON_SECRET: header X-Cron-Secret or query ?token=
        """
        secret = app.config.get('CRON_SECRET') or os.environ.get('CRON_SECRET')
        if not secret:
            return jsonify({'ok': False, 'error': 'CRON_SECRET is not configured'}), 503
        received = request.headers.get('X-Cron-Secret') or request.args.get('token')
        if received != secret:
            abort(403)
        from utils.academic_period_reminders import run_academic_period_reminders
        result = run_academic_period_reminders()
        return jsonify(result)

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # This block only runs if you execute 'python app.py' directly
    app.run(debug=True, port=5000)