import sys
import logging
import os as _os
from logging.handlers import RotatingFileHandler

# Force line-buffered stdout/stderr so request logs and tracebacks show up
# immediately when the app is launched from a non-TTY (e.g. Cursor terminal,
# CI runners, or any captured/piped shell). Otherwise output can sit in a
# block buffer for many seconds, making the server look silent.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass


class _FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes after every record. Some Windows terminals
    (and Cursor's captured terminal) block-buffer pipe stderr, so logs can sit
    invisible for minutes. Calling flush() after each emit forces them out."""

    def emit(self, record):
        super().emit(record)
        try:
            self.flush()
        except Exception:
            pass


def _bootstrap_logging() -> None:
    """Configure log output BEFORE Flask/Werkzeug touch the root logger so we
    capture the very first request. Sends everything to stderr (flushing) AND
    to a rolling file at ``logs/server.log`` — the file is a guaranteed way to
    see logs even if the terminal capture eats them."""
    log_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'logs')
    try:
        _os.makedirs(log_dir, exist_ok=True)
    except Exception:
        log_dir = None

    fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    stream_handler = _FlushingStreamHandler(sys.stderr)
    stream_handler.setFormatter(fmt)

    handlers = [stream_handler]
    if log_dir:
        try:
            file_handler = RotatingFileHandler(
                _os.path.join(log_dir, 'server.log'),
                maxBytes=2 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8',
            )
            file_handler.setFormatter(fmt)
            handlers.append(file_handler)
        except Exception:
            pass

    root = logging.getLogger()
    # Wipe any default handlers Werkzeug might have already attached.
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in handlers:
        root.addHandler(h)
    root.setLevel(logging.INFO)

    # Werkzeug attaches its own handler to its child logger; make sure ours
    # are the ones in effect.
    werkzeug = logging.getLogger('werkzeug')
    for h in list(werkzeug.handlers):
        werkzeug.removeHandler(h)
    werkzeug.setLevel(logging.INFO)
    werkzeug.propagate = True


_bootstrap_logging()

print("Loading Clara Science App...", flush=True)
import os
import json
from flask import Flask, render_template, g, current_app, redirect, url_for, flash, request, session, jsonify, abort
from flask_login import current_user, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
print("  loading config...", flush=True)
from config import Config, ProductionConfig, DevelopmentConfig, TestingConfig
from sqlalchemy import func, and_, text
from datetime import datetime, timezone
from decorators import is_teacher_role, user_can_manage_assignments_and_grades

# Import extensions to avoid circular imports
print("  loading extensions...", flush=True)
from extensions import db, login_manager, csrf, mail
from flask_migrate import Migrate

# Import models here to avoid circular imports
print("  loading models...", flush=True)
from models import User, Student, Grade, SchoolYear, ReportCard, Assignment, Notification, MaintenanceMode, ActivityLog, AssignmentExtension, QuarterGrade, Class, Enrollment, AcademicPeriod, RedoRequest

# Re-export services so "from app import create_notification" etc. still work
print("  loading services...", flush=True)
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

    # gzip compression for HTML/CSS/JS/JSON. Big templates (e.g. the grading page,
    # dashboards) shrink ~5-10x over the wire and noticeably cut perceived load time.
    try:
        from flask_compress import Compress
        Compress(app)
    except ImportError:
        # Flask-Compress is optional; if it isn't installed the app still works.
        app.logger.info("Flask-Compress not installed; skipping gzip compression.")
    
    # Initialize database schema; create_all plus idempotent ADD COLUMN patches for older deployments
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

        # Add user.permissions column if missing (fine-grained permissions for staff)
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(user)"))
                    columns = [row[1] for row in r]
                    if 'permissions' not in columns:
                        conn.execute(text("ALTER TABLE user ADD COLUMN permissions TEXT"))
                        conn.commit()
                        print("Added user.permissions column.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'user' AND column_name = 'permissions'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN permissions TEXT'))
                        conn.commit()
                        print("Added user.permissions column.")
        except Exception as e:
            print(f"Note: permissions column check failed (may already exist): {e}")

        # Add user.secondary_roles (JSON list) for multi-dashboard staff logins
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(user)"))
                    columns = [row[1] for row in r]
                    if 'secondary_roles' not in columns:
                        conn.execute(text("ALTER TABLE user ADD COLUMN secondary_roles TEXT"))
                        conn.commit()
                        print("Added user.secondary_roles column.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'user' AND column_name = 'secondary_roles'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN secondary_roles TEXT'))
                        conn.commit()
                        print("Added user.secondary_roles column.")
        except Exception as e:
            print(f"Note: secondary_roles column check failed (may already exist): {e}")

        # Add message.is_edited / parent_message_id if missing (ORM expects them; older DBs may lack them)
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(message)"))
                    msg_columns = [row[1] for row in r]
                    if 'is_edited' not in msg_columns:
                        conn.execute(text("ALTER TABLE message ADD COLUMN is_edited INTEGER DEFAULT 0"))
                        conn.commit()
                        print("Added message.is_edited column.")
                    if 'parent_message_id' not in msg_columns:
                        conn.execute(text("ALTER TABLE message ADD COLUMN parent_message_id INTEGER"))
                        conn.commit()
                        print("Added message.parent_message_id column.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'message' AND column_name = 'is_edited'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text(
                            "ALTER TABLE message ADD COLUMN is_edited BOOLEAN NOT NULL DEFAULT false"
                        ))
                        conn.commit()
                        print("Added message.is_edited column.")
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'message' AND column_name = 'parent_message_id'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text("ALTER TABLE message ADD COLUMN parent_message_id INTEGER"))
                        conn.commit()
                        print("Added message.parent_message_id column.")
        except Exception as e:
            print(f"Note: message table column check failed (may already exist): {e}")

        # Add teacher_staff employment status columns if missing (staff lifecycle tracking)
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(teacher_staff)"))
                    columns = [row[1] for row in r]
                    if 'employment_status' not in columns:
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN employment_status VARCHAR(30) DEFAULT 'Active'"))
                        conn.commit()
                        print("Added teacher_staff.employment_status column.")
                    if 'marked_for_removal' not in columns:
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN marked_for_removal INTEGER DEFAULT 0"))
                        conn.commit()
                        print("Added teacher_staff.marked_for_removal column.")
                    if 'removal_note' not in columns:
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN removal_note TEXT"))
                        conn.commit()
                        print("Added teacher_staff.removal_note column.")
                    if 'status_updated_at' not in columns:
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN status_updated_at DATETIME"))
                        conn.commit()
                        print("Added teacher_staff.status_updated_at column.")
                    if 'is_active' not in columns:
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"))
                        conn.commit()
                        print("Added teacher_staff.is_active column.")
                    if 'portal_login' not in columns:
                        conn.execute(text(
                            "ALTER TABLE teacher_staff ADD COLUMN portal_login INTEGER NOT NULL DEFAULT 1"
                        ))
                        conn.commit()
                        print("Added teacher_staff.portal_login column.")
                elif dialect == 'postgresql':
                    def _pg_has(col):
                        r = conn.execute(text(
                            "SELECT 1 FROM information_schema.columns "
                            "WHERE table_schema = 'public' AND table_name = 'teacher_staff' AND column_name = :c"
                        ), {"c": col})
                        return r.fetchone() is not None
                    if not _pg_has('employment_status'):
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN employment_status VARCHAR(30) NOT NULL DEFAULT 'Active'"))
                        conn.commit()
                        print("Added teacher_staff.employment_status column.")
                    if not _pg_has('marked_for_removal'):
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN marked_for_removal BOOLEAN NOT NULL DEFAULT false"))
                        conn.commit()
                        print("Added teacher_staff.marked_for_removal column.")
                    if not _pg_has('removal_note'):
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN removal_note TEXT"))
                        conn.commit()
                        print("Added teacher_staff.removal_note column.")
                    if not _pg_has('status_updated_at'):
                        conn.execute(text("ALTER TABLE teacher_staff ADD COLUMN status_updated_at TIMESTAMP"))
                        conn.commit()
                        print("Added teacher_staff.status_updated_at column.")
                    if not _pg_has('is_active'):
                        conn.execute(text(
                            "ALTER TABLE teacher_staff ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true"
                        ))
                        conn.commit()
                        print("Added teacher_staff.is_active column.")
                    if not _pg_has('portal_login'):
                        conn.execute(text(
                            "ALTER TABLE teacher_staff ADD COLUMN portal_login BOOLEAN NOT NULL DEFAULT true"
                        ))
                        conn.commit()
                        print("Added teacher_staff.portal_login column.")
        except Exception as e:
            print(f"Note: teacher_staff status columns check failed (may already exist): {e}")

        # Add student profile confirmation columns if missing (report cards + enrollment policy)
        _student_cols = [
            ('gender', 'VARCHAR(30)', 'TEXT'),
            ('entrance_date', 'VARCHAR(9)', 'TEXT'),
            ('expected_grad_date', 'VARCHAR(7)', 'TEXT'),
            ('grad_year', 'INTEGER', 'INTEGER'),
            ('expected_graduation_year', 'INTEGER', 'INTEGER'),
            ('is_active', 'BOOLEAN NOT NULL DEFAULT true', 'INTEGER NOT NULL DEFAULT 1'),
            ('is_repeating', 'BOOLEAN NOT NULL DEFAULT false', 'INTEGER NOT NULL DEFAULT 0'),
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

        # Add class.google_group_email if missing (Directory group sync)
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                col_name = 'google_group_email'
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(class)"))
                    columns = [row[1] for row in r]
                    if col_name not in columns:
                        conn.execute(text("ALTER TABLE class ADD COLUMN google_group_email TEXT"))
                        conn.commit()
                        print("Added class.google_group_email column.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'class' AND column_name = :col"
                    ), {"col": col_name})
                    if r.fetchone() is None:
                        conn.execute(text('ALTER TABLE "class" ADD COLUMN google_group_email VARCHAR(120)'))
                        conn.commit()
                        print("Added class.google_group_email column.")
        except Exception as e:
            print(f"Note: class google_group_email column check failed (may already exist): {e}")

        # Class term metadata (full year vs semester/quarter); required by Class ORM on Postgres
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(class)"))
                    columns = [row[1] for row in r]
                    if 'term_type' not in columns:
                        conn.execute(text(
                            "ALTER TABLE class ADD COLUMN term_type VARCHAR(20) NOT NULL DEFAULT 'full_year'"
                        ))
                        conn.commit()
                        print("Added class.term_type column.")
                    if 'term_value' not in columns:
                        conn.execute(text("ALTER TABLE class ADD COLUMN term_value VARCHAR(10)"))
                        conn.commit()
                        print("Added class.term_value column.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'class' AND column_name = 'term_type'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text(
                            'ALTER TABLE "class" ADD COLUMN term_type VARCHAR(20) NOT NULL DEFAULT \'full_year\''
                        ))
                        conn.commit()
                        print("Added class.term_type column.")
                    r2 = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'class' AND column_name = 'term_value'"
                    ))
                    if r2.fetchone() is None:
                        conn.execute(text('ALTER TABLE "class" ADD COLUMN term_value VARCHAR(10)'))
                        conn.commit()
                        print("Added class.term_value column.")
        except Exception as e:
            print(f"Note: class term_type/term_value column check failed (may already exist): {e}")

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

        # Quiz authoring draft (save incomplete quiz; students never see until published)
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(assignment)"))
                    columns = [row[1] for row in r]
                    if 'quiz_authoring_is_draft' not in columns:
                        conn.execute(text(
                            "ALTER TABLE assignment ADD COLUMN quiz_authoring_is_draft INTEGER NOT NULL DEFAULT 0"
                        ))
                        conn.commit()
                        print("Added assignment.quiz_authoring_is_draft column.")
                elif dialect == 'postgresql':
                    r = conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'assignment' AND column_name = 'quiz_authoring_is_draft'"
                    ))
                    if r.fetchone() is None:
                        conn.execute(text(
                            'ALTER TABLE "assignment" ADD COLUMN quiz_authoring_is_draft BOOLEAN NOT NULL DEFAULT false'
                        ))
                        conn.commit()
                        print("Added assignment.quiz_authoring_is_draft column.")
        except Exception as e:
            print(f"Note: assignment.quiz_authoring_is_draft check failed (may already exist): {e}")

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

        # Add report_card columns for auto-generation provenance if missing
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    r = conn.execute(text("PRAGMA table_info(report_card)"))
                    cols = [row[1] for row in r]
                    if 'is_auto_generated' not in cols:
                        conn.execute(text(
                            "ALTER TABLE report_card ADD COLUMN is_auto_generated INTEGER NOT NULL DEFAULT 0"
                        ))
                        conn.commit()
                        print("Added report_card.is_auto_generated column.")
                    if 'generated_by_user_id' not in cols:
                        conn.execute(text(
                            "ALTER TABLE report_card ADD COLUMN generated_by_user_id INTEGER"
                        ))
                        conn.commit()
                        print("Added report_card.generated_by_user_id column.")
                    if 'director_approved' not in cols:
                        conn.execute(text(
                            "ALTER TABLE report_card ADD COLUMN director_approved INTEGER NOT NULL DEFAULT 0"
                        ))
                        conn.commit()
                        print("Added report_card.director_approved column.")
                    if 'approved_at' not in cols:
                        conn.execute(text(
                            "ALTER TABLE report_card ADD COLUMN approved_at DATETIME"
                        ))
                        conn.commit()
                        print("Added report_card.approved_at column.")
                    if 'approved_by_user_id' not in cols:
                        conn.execute(text(
                            "ALTER TABLE report_card ADD COLUMN approved_by_user_id INTEGER"
                        ))
                        conn.commit()
                        print("Added report_card.approved_by_user_id column.")
                elif dialect == 'postgresql':
                    for col_name, col_sql in (
                        ('is_auto_generated',
                         'ALTER TABLE "report_card" ADD COLUMN is_auto_generated BOOLEAN NOT NULL DEFAULT false'),
                        ('generated_by_user_id',
                         'ALTER TABLE "report_card" ADD COLUMN generated_by_user_id INTEGER'),
                        ('director_approved',
                         'ALTER TABLE "report_card" ADD COLUMN director_approved BOOLEAN NOT NULL DEFAULT false'),
                        ('approved_at',
                         'ALTER TABLE "report_card" ADD COLUMN approved_at TIMESTAMP'),
                        ('approved_by_user_id',
                         'ALTER TABLE "report_card" ADD COLUMN approved_by_user_id INTEGER'),
                    ):
                        r = conn.execute(text(
                            "SELECT 1 FROM information_schema.columns "
                            "WHERE table_name = 'report_card' AND column_name = :col"
                        ), {"col": col_name})
                        if r.fetchone() is None:
                            conn.execute(text(col_sql))
                            conn.commit()
                            print(f"Added report_card.{col_name} column.")
        except Exception as e:
            print(f"Note: report_card provenance column check failed (may already exist): {e}")

        # Create school_year_closure / extension / event tables if missing
        try:
            with db.engine.connect() as conn:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    def _has_table(name):
                        return conn.execute(text(
                            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"
                        ), {"n": name}).fetchone() is not None

                    if not _has_table('school_year_closure'):
                        conn.execute(text("""
                            CREATE TABLE school_year_closure (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                school_year_id INTEGER NOT NULL REFERENCES school_year(id),
                                closure_date DATE NOT NULL,
                                student_lockout_at DATE NOT NULL,
                                teacher_lockout_at DATE NOT NULL,
                                finalize_at DATE NOT NULL,
                                phase VARCHAR(20) NOT NULL DEFAULT 'scheduled',
                                previous_phase VARCHAR(20),
                                created_by_user_id INTEGER REFERENCES user(id),
                                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                student_notice_sent_at DATETIME,
                                teacher_notice_sent_at DATETIME,
                                admin_warning_sent_at DATETIME,
                                students_locked_at DATETIME,
                                teachers_locked_at DATETIME,
                                finalized_at DATETIME,
                                cancelled_at DATETIME,
                                cancelled_by_user_id INTEGER REFERENCES user(id),
                                cancellation_reason TEXT,
                                paused_at DATETIME,
                                paused_by_user_id INTEGER REFERENCES user(id),
                                notes TEXT,
                                last_tick_at DATETIME,
                                finalize_stats TEXT
                            )
                        """))
                        conn.commit()
                        print("Created school_year_closure table.")
                    if not _has_table('school_year_closure_extension'):
                        conn.execute(text("""
                            CREATE TABLE school_year_closure_extension (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                closure_id INTEGER NOT NULL REFERENCES school_year_closure(id),
                                scope_user_id INTEGER REFERENCES user(id),
                                scope_class_id INTEGER REFERENCES class(id),
                                for_role VARCHAR(10) NOT NULL DEFAULT 'both',
                                extended_until DATE NOT NULL,
                                reason TEXT,
                                granted_by_user_id INTEGER REFERENCES user(id),
                                granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                revoked_at DATETIME,
                                revoked_by_user_id INTEGER REFERENCES user(id),
                                revoked_reason TEXT
                            )
                        """))
                        conn.commit()
                        print("Created school_year_closure_extension table.")
                    if not _has_table('school_year_closure_event'):
                        conn.execute(text("""
                            CREATE TABLE school_year_closure_event (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                closure_id INTEGER NOT NULL REFERENCES school_year_closure(id),
                                event_type VARCHAR(40) NOT NULL,
                                actor_user_id INTEGER REFERENCES user(id),
                                actor_label VARCHAR(40),
                                payload TEXT,
                                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        conn.commit()
                        print("Created school_year_closure_event table.")
                    if not _has_table('parent_student_link'):
                        conn.execute(text("""
                            CREATE TABLE parent_student_link (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                parent_user_id INTEGER NOT NULL REFERENCES user(id),
                                student_id INTEGER NOT NULL REFERENCES student(id),
                                relationship VARCHAR(50),
                                parent_slot INTEGER,
                                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT uq_parent_student_link UNIQUE (parent_user_id, student_id)
                            )
                        """))
                        conn.commit()
                        print("Created parent_student_link table.")
                elif dialect == 'postgresql':
                    def _has_table_pg(name):
                        return conn.execute(text(
                            "SELECT 1 FROM information_schema.tables WHERE table_name = :n"
                        ), {"n": name}).fetchone() is not None

                    if not _has_table_pg('school_year_closure'):
                        conn.execute(text("""
                            CREATE TABLE school_year_closure (
                                id SERIAL PRIMARY KEY,
                                school_year_id INTEGER NOT NULL REFERENCES school_year(id),
                                closure_date DATE NOT NULL,
                                student_lockout_at DATE NOT NULL,
                                teacher_lockout_at DATE NOT NULL,
                                finalize_at DATE NOT NULL,
                                phase VARCHAR(20) NOT NULL DEFAULT 'scheduled',
                                previous_phase VARCHAR(20),
                                created_by_user_id INTEGER REFERENCES "user"(id),
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                student_notice_sent_at TIMESTAMP,
                                teacher_notice_sent_at TIMESTAMP,
                                admin_warning_sent_at TIMESTAMP,
                                students_locked_at TIMESTAMP,
                                teachers_locked_at TIMESTAMP,
                                finalized_at TIMESTAMP,
                                cancelled_at TIMESTAMP,
                                cancelled_by_user_id INTEGER REFERENCES "user"(id),
                                cancellation_reason TEXT,
                                paused_at TIMESTAMP,
                                paused_by_user_id INTEGER REFERENCES "user"(id),
                                notes TEXT,
                                last_tick_at TIMESTAMP,
                                finalize_stats TEXT
                            )
                        """))
                        conn.commit()
                        print("Created school_year_closure table.")
                    if not _has_table_pg('school_year_closure_extension'):
                        conn.execute(text("""
                            CREATE TABLE school_year_closure_extension (
                                id SERIAL PRIMARY KEY,
                                closure_id INTEGER NOT NULL REFERENCES school_year_closure(id),
                                scope_user_id INTEGER REFERENCES "user"(id),
                                scope_class_id INTEGER REFERENCES "class"(id),
                                for_role VARCHAR(10) NOT NULL DEFAULT 'both',
                                extended_until DATE NOT NULL,
                                reason TEXT,
                                granted_by_user_id INTEGER REFERENCES "user"(id),
                                granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                revoked_at TIMESTAMP,
                                revoked_by_user_id INTEGER REFERENCES "user"(id),
                                revoked_reason TEXT
                            )
                        """))
                        conn.commit()
                        print("Created school_year_closure_extension table.")
                    if not _has_table_pg('school_year_closure_event'):
                        conn.execute(text("""
                            CREATE TABLE school_year_closure_event (
                                id SERIAL PRIMARY KEY,
                                closure_id INTEGER NOT NULL REFERENCES school_year_closure(id),
                                event_type VARCHAR(40) NOT NULL,
                                actor_user_id INTEGER REFERENCES "user"(id),
                                actor_label VARCHAR(40),
                                payload TEXT,
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        conn.commit()
                        print("Created school_year_closure_event table.")
                    if not _has_table_pg('parent_student_link'):
                        conn.execute(text("""
                            CREATE TABLE parent_student_link (
                                id SERIAL PRIMARY KEY,
                                parent_user_id INTEGER NOT NULL REFERENCES "user"(id),
                                student_id INTEGER NOT NULL REFERENCES student(id),
                                relationship VARCHAR(50),
                                parent_slot INTEGER,
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT uq_parent_student_link UNIQUE (parent_user_id, student_id)
                            )
                        """))
                        conn.commit()
                        print("Created parent_student_link table.")
        except Exception as e:
            print(f"Note: school_year_closure table check failed (may already exist): {e}")

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

        try:
            user = User.query.get(user_id_int)
        except Exception as exc:
            # Database connection hiccups can happen under load (e.g. SSL EOF).
            # Roll back the broken transaction so subsequent requests can recover cleanly.
            try:
                from models import db
                db.session.rollback()
            except Exception:
                pass
            app.logger.warning("load_user failed for id %s: %s", user_id_int, exc)
            return None

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
    from parentroutes import parent_blueprint
    from teacher_routes import teacher_blueprint  # Using new modular teacher_routes package
    from management_routes import management_blueprint  # Using new modular management_routes package
    from management_routes.school_year_closure import school_year_closure_bp
    from techroutes import tech_blueprint
    from communications_api import api_bp as communications_api_bp
    from shared_communications import bp as shared_communications_bp
    from management_routes.student_assistant_routes import bp as student_assistant_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(student_blueprint, url_prefix='/student')
    app.register_blueprint(parent_blueprint, url_prefix='/parent')
    app.register_blueprint(teacher_blueprint, url_prefix='/teacher')
    app.register_blueprint(management_blueprint, url_prefix='/management')
    app.register_blueprint(school_year_closure_bp)  # Phased year-end workflow (own url_prefix)

    # Lockout enforcement: gates known student/teacher write endpoints once a
    # SchoolYearClosure has advanced past Day 7 / Day 21. Honors per-user and
    # per-class extensions.
    try:
        from utils.closure_gates import register_closure_gates
        register_closure_gates(app)
    except Exception as _gate_exc:
        app.logger.exception("Failed to register closure gates: %s", _gate_exc)
    app.register_blueprint(tech_blueprint, url_prefix='/tech')
    app.register_blueprint(student_assistant_blueprint)  # /assistant/... for student assistants
    app.register_blueprint(communications_api_bp)  # Communications API - no prefix, uses absolute paths
    app.register_blueprint(shared_communications_bp)  # Shared communications routes

    # Expose ``current_app`` to Jinja so templates can defensively check
    # registered endpoints (e.g. {% if 'foo.bar' in current_app.view_functions %}).
    from flask import current_app as _flask_current_app
    app.jinja_env.globals['current_app'] = _flask_current_app

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

    @app.template_filter("staff_role_labels")
    def staff_role_labels_filter(teacher_staff):
        """Canonical role labels for staff directory (primary + secondary + directory field)."""
        from utils.user_roles import ordered_role_labels_for_teacher_staff

        return ordered_role_labels_for_teacher_staff(teacher_staff)

    @app.template_filter("role_badge_class")
    def role_badge_class_filter(role_label):
        """Bootstrap badge CSS classes for a role label in staff lists."""
        from utils.user_roles import role_badge_bootstrap_class

        return role_badge_bootstrap_class(role_label or "")

    @app.template_filter("user_lifecycle")
    def user_lifecycle_filter(user):
        """Current vs former for Tech user management (student / staff profile flags)."""
        from utils.tech_user_management import user_lifecycle_bucket

        return user_lifecycle_bucket(user)

    @app.template_filter("portal_account_status")
    def portal_account_status_filter(user):
        """Active / Disabled / No account for Tech User Management status column."""
        from utils.tech_user_management import user_portal_status_label

        return user_portal_status_label(user)

    @app.template_filter('schooltime')
    def schooltime_filter(value, fmt='%m/%d/%Y %I:%M %p'):
        """
        Format a datetime in the school's configured timezone.

        Production hosts typically run in UTC. If DB datetimes are stored as UTC (often naive),
        calling strftime() directly in templates will display UTC and appear "ahead" of EST.
        This filter treats naive datetimes as UTC and converts to the effective school timezone
        (Tech DB override, then SCHOOL_TIMEZONE env, then Eastern).
        """
        if value is None:
            return ''
        try:
            from datetime import datetime, timezone
            from zoneinfo import ZoneInfo  # py3.9+
            from utils.school_timezone import get_school_timezone_name

            tz_name = get_school_timezone_name()
            school_tz = ZoneInfo(tz_name)

            dt = value
            if not isinstance(dt, datetime):
                return str(dt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone(school_tz)
            return local_dt.strftime(fmt)
        except Exception:
            try:
                import pytz
                from datetime import datetime, timezone
                from utils.school_timezone import get_school_timezone_name

                tz_name = get_school_timezone_name()
                school_tz = pytz.timezone(tz_name)
                dt = value
                if not isinstance(dt, datetime):
                    return str(dt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                local_dt = dt.astimezone(school_tz)
                return local_dt.strftime(fmt)
            except Exception:
                try:
                    return value.strftime(fmt)  # last resort
                except Exception:
                    return str(value)

    @app.template_filter('effective_assignment_status')
    def effective_assignment_status_filter(assignment):
        """Lifecycle status consistent with open/close/due dates and temporary status_override window."""
        if assignment is None:
            return ''
        try:
            from teacher_routes.assignment_utils import get_effective_assignment_status
            return get_effective_assignment_status(assignment)
        except Exception:
            return getattr(assignment, 'status', None) or ''

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

    @app.template_filter('quiz_content')
    def quiz_content_filter(value):
        """
        Render quiz question/option content with safe formatting:
        - Supports triple-backtick fenced blocks: ```lang ... ```
        - Preserves line breaks
        """
        from markupsafe import Markup, escape
        if value is None:
            return Markup('')
        s = str(value)

        # Normalize newlines
        s = s.replace('\r\n', '\n').replace('\r', '\n')

        parts = []
        i = 0
        while True:
            start = s.find('```', i)
            if start == -1:
                parts.append(('text', s[i:]))
                break
            # text before fence
            parts.append(('text', s[i:start]))
            # find end fence
            fence_header_end = s.find('\n', start + 3)
            if fence_header_end == -1:
                # treat remainder as text
                parts.append(('text', s[start:]))
                break
            lang = s[start + 3:fence_header_end].strip() or 'text'
            end = s.find('```', fence_header_end + 1)
            if end == -1:
                # no closing fence; treat remainder as text
                parts.append(('text', s[start:]))
                break
            code = s[fence_header_end + 1:end]
            parts.append(('code', (lang, code)))
            i = end + 3

        out_html = []
        for kind, payload in parts:
            if kind == 'text':
                escaped_txt = escape(payload)
                out_html.append(escaped_txt.replace('\n', '<br>\n'))
            else:
                lang, code = payload
                code_esc = '\n'.join(escape(line) for line in code.split('\n'))
                out_html.append(
                    Markup(
                        f'<div class="quiz-code-block" data-lang="{escape(lang)}">'
                        f'<span class="badge text-bg-secondary mb-2">{escape(lang)}</span>'
                        f'<pre class="mb-0 p-3 bg-dark text-light rounded-3"><code>{code_esc}</code></pre>'
                        f'</div>'
                    )
                )
        return Markup(''.join(str(x) for x in out_html))

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
            try:
                site_override = SystemConfig.get_value('site_theme_override')
                if site_override:
                    effective = site_override
                else:
                    pref = getattr(current_user, 'theme_preference', None)
                    if pref:
                        effective = pref
            except Exception as e:
                # If the request transaction is in a failed state (e.g., prior DB error),
                # ensure we can still render error pages without cascading failures.
                try:
                    db.session.rollback()
                except Exception:
                    pass
                current_app.logger.warning("inject_theme failed; falling back to default theme: %s", e)
        return {'effective_theme': effective}

    @app.context_processor
    def inject_app_version():
        from utils.app_version import app_version_context
        return app_version_context()

    @app.context_processor
    def inject_permissions_helpers():
        """Expose permission helpers to templates."""
        try:
            from decorators import has_permission, get_user_permissions

            def has_perm(perm):
                try:
                    return has_permission(current_user, perm)
                except Exception:
                    return False

            def perms():
                try:
                    return sorted(list(get_user_permissions(current_user)))
                except Exception:
                    return []

            return {"has_perm": has_perm, "current_user_permissions": perms()}
        except Exception:
            return {"has_perm": lambda _p: False, "current_user_permissions": []}

    @app.context_processor
    def inject_dual_dashboard():
        """Staff who may open Tech or Management dashboard (merged / multi-role accounts)."""
        if not current_user.is_authenticated:
            return {"dual_dashboard_staff": False}
        try:
            from utils.user_roles import staff_must_choose_dashboard

            return {"dual_dashboard_staff": staff_must_choose_dashboard(current_user)}
        except Exception as e:
            current_app.logger.warning("inject_dual_dashboard failed: %s", e)
            return {"dual_dashboard_staff": False}

    @app.context_processor
    def inject_credential_modal():
        """One-shot payload for the credential summary modal after adding students/staff."""
        if not current_user.is_authenticated:
            return {"credential_modal": None}
        try:
            data = session.pop("credential_modal", None)
            return {"credential_modal": data}
        except Exception as e:
            current_app.logger.warning("inject_credential_modal failed: %s", e)
            return {"credential_modal": None}

    @app.context_processor
    def inject_role_canonical():
        """Primary role (alerts, etc.); ``sidebar_role_canonical`` follows tech/management switch for dual staff."""
        if not current_user.is_authenticated:
            return {"role_canonical": "", "sidebar_role_canonical": ""}
        try:
            from utils.user_roles import (
                canonical_role_label,
                staff_must_choose_dashboard,
                pick_tech_sidebar_canonical,
                pick_management_sidebar_canonical,
            )

            base = canonical_role_label(current_user.role)
            sidebar = base
            if staff_must_choose_dashboard(current_user):
                target = session.get("staff_dashboard_target")
                if target == "tech":
                    sidebar = pick_tech_sidebar_canonical(current_user)
                elif target == "management":
                    sidebar = pick_management_sidebar_canonical(current_user)
                else:
                    bp = getattr(request, "blueprint", None) or ""
                    if bp == "tech":
                        sidebar = pick_tech_sidebar_canonical(current_user)
                    elif bp == "management":
                        sidebar = pick_management_sidebar_canonical(current_user)
            return {"role_canonical": base, "sidebar_role_canonical": sidebar}
        except Exception:
            r = getattr(current_user, "role", None) or ""
            return {"role_canonical": r, "sidebar_role_canonical": r}

    @app.context_processor
    def inject_management_capability_flags():
        """
        UI flags for merged accounts (e.g. Tech + School Administrator): primary ``role`` may be Tech
        while Director/School Admin lives in ``secondary_roles``. Templates must not rely on
        ``current_user.role in ['Director', 'School Administrator']`` alone.
        """
        if not current_user.is_authenticated:
            return {
                "has_mgmt_role_access": False,
                "can_student_admin_ui": False,
                "can_staff_admin_ui": False,
                "can_calendar_admin_ui": False,
                "can_assignments_admin_ui": False,
                "can_home_assignment_actions": False,
                "can_manage_student_assistants": False,
            }
        try:
            from utils.user_roles import user_has_management_entry_access
            from decorators import (
                has_permission,
                has_any_permission,
                is_teacher_role,
                user_can_manage_student_assistants,
            )

            _cal_perms = (
                "students:view",
                "students:edit",
                "teachers_staff:manage",
                "classes:manage",
                "assignments_grades:manage",
                "attendance:manage",
                "report_cards:view",
                "report_cards:generate",
            )
            h = user_has_management_entry_access(current_user)
            stu = h or has_permission(current_user, "students:edit")
            stf = h or has_permission(current_user, "teachers_staff:manage")
            cal = h or has_any_permission(current_user, _cal_perms)
            asn = h or has_permission(current_user, "assignments_grades:manage")
            home_asn = h or asn or is_teacher_role(getattr(current_user, "role", None))
            return {
                "has_mgmt_role_access": h,
                "can_student_admin_ui": stu,
                "can_staff_admin_ui": stf,
                "can_calendar_admin_ui": cal,
                "can_assignments_admin_ui": asn,
                "can_home_assignment_actions": home_asn,
                "can_manage_student_assistants": user_can_manage_student_assistants(current_user),
            }
        except Exception as e:
            current_app.logger.warning("inject_management_capability_flags failed: %s", e)
            return {
                "has_mgmt_role_access": False,
                "can_student_admin_ui": False,
                "can_staff_admin_ui": False,
                "can_calendar_admin_ui": False,
                "can_assignments_admin_ui": False,
                "can_home_assignment_actions": False,
                "can_manage_student_assistants": False,
            }

    @app.context_processor
    def inject_role_display():
        """Single place to control how a user's role is displayed in the sidebar."""
        try:
            role = (getattr(current_user, 'role', None) or '').strip()
            if not current_user.is_authenticated:
                return {"current_user_role_display": role}
            profile = getattr(current_user, 'teacher_staff_profile', None)
            dept = (getattr(profile, 'department', None) or '').strip() if profile else ''
            # Normalize legacy teacher roles to simplified display
            if role in ['Math Teacher', 'Science Teacher', 'History Teacher', 'Physics Teacher', 'English Language Arts Teacher']:
                display = 'Teacher'
            elif role == 'School Counselor':
                display = 'Counselor'
            elif role == 'Substitute Teacher':
                display = 'Substitute'
            else:
                display = role or 'User'
            if dept and dept != 'Administration':
                return {"current_user_role_display": f"{display} • {dept}"}
            if dept == 'Administration' and role not in ['School Administrator', 'Director']:
                # Show subtle hint that access is permission-based
                return {"current_user_role_display": f"{display} • Administration"}
            return {"current_user_role_display": display}
        except Exception:
            return {"current_user_role_display": getattr(current_user, 'role', '')}

    @app.context_processor
    def inject_school_timezone_display():
        """IANA zone used for assignment times, schooltime filter, and school-day logic (same for all users)."""
        try:
            from flask_login import current_user

            if not current_user.is_authenticated:
                return {}
            from utils.school_timezone import get_school_timezone_name

            return {"school_timezone_display": get_school_timezone_name()}
        except Exception as e:
            current_app.logger.warning("inject_school_timezone_display: %s", e)
            return {"school_timezone_display": None}

    @app.context_processor
    def inject_school_years_for_filters():
        """Provide school years for management filter dropdowns (defensive)."""
        try:
            from models import SchoolYear
            years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
            active = next((y for y in years if getattr(y, "is_active", False)), None)
            latest_label = None
            if not active and years:
                y = years[0]
                latest_label = y.name + (" (Closed)" if not getattr(y, "is_active", False) else "")
            return {
                "all_school_years": years,
                "active_school_year_obj": active,
                "has_active_school_year": active is not None,
                "latest_school_year_label": latest_label,
            }
        except Exception:
            return {
                "all_school_years": [],
                "active_school_year_obj": None,
                "has_active_school_year": False,
                "latest_school_year_label": None,
            }

    # Inject at_risk_alerts for teacher/admin dashboard pages (shown on all tabs)
    @app.context_processor
    def inject_at_risk_alerts():
        from utils.academic_concerns_ui import academic_concerns_popup_disabled

        out = {
            'at_risk_alerts': [],
            'failing_count': 0,
            'overdue_count': 0,
            'not_submitted_count': 0,
            'academic_concerns_audience': False,
            'disable_academic_alert_popup': academic_concerns_popup_disabled(),
        }
        if not current_user.is_authenticated:
            return out
        # Primary role may be Tech while School Administrator lives in secondary_roles;
        # teacher roles may appear only in secondary_roles — use same helpers as alert computation.
        try:
            from utils.user_roles import all_role_strings, user_has_management_entry_access
            from decorators import is_teacher_role

            audience = user_has_management_entry_access(current_user) or any(
                is_teacher_role(r) for r in all_role_strings(current_user)
            )
            out['academic_concerns_audience'] = audience
            if not audience:
                return out
        except Exception as e:
            current_app.logger.warning(f"Context processor at_risk_alerts (role gate): {e}")
            return out
        try:
            from utils.at_risk_alerts import get_at_risk_alerts_for_user
            alerts, failing, overdue, not_submitted = get_at_risk_alerts_for_user()
            return {
                **out,
                'at_risk_alerts': alerts,
                'failing_count': failing,
                'overdue_count': overdue,
                'not_submitted_count': not_submitted,
            }
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
            elif role == 'Parent':
                return redirect(url_for('parent.parent_dashboard'))
        
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

        # Check authorization - teachers/admins can view files for their classes.
        # Use same rule as management assignment routes: Director/SA in primary *or* secondary_roles,
        # or explicit assignments_grades:manage (not just primary role string — avoids Tech+SA 403 in iframe).
        if user_can_manage_assignments_and_grades(current_user):
            pass  # Authorized (any class, including missing class_obj)
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

        if user_can_manage_assignments_and_grades(current_user):
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
        try:
            db.session.rollback()
        except Exception:
            pass
        
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
        # Route through ``app.logger`` so tracebacks land in BOTH the live
        # terminal AND ``logs/server.log``. The previous implementation used
        # bare ``print`` + ``traceback.print_exc`` which can be silently
        # swallowed by Cursor's captured terminal on Windows.
        try:
            app.logger.exception("Unexpected error: %s", error)
        except Exception:
            import traceback
            print(f"Unexpected error: {error}", flush=True)
            traceback.print_exc()
        try:
            db.session.rollback()
        except Exception:
            pass
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
            return jsonify({'ok': False, 'error': 'invalid or missing secret'}), 403
        from utils.academic_period_reminders import run_academic_period_reminders
        result = run_academic_period_reminders()
        return jsonify(result)

    @app.route('/cron/school-year-closure-tick', methods=['POST'])
    @csrf.exempt
    def cron_school_year_closure_tick():
        """
        Daily job: advance every active SchoolYearClosure that has crossed a
        milestone (Day 7 / Day 21 / Day 28), fire notifications, and auto-run
        finalize once Day 28 is reached.

        Idempotent: re-running the same day is a no-op once each transition
        has been recorded. Protected with CRON_SECRET like the other cron endpoints.
        """
        secret = app.config.get('CRON_SECRET') or os.environ.get('CRON_SECRET')
        if not secret:
            return jsonify({'ok': False, 'error': 'CRON_SECRET is not configured'}), 503
        received = request.headers.get('X-Cron-Secret') or request.args.get('token')
        if received != secret:
            # Use a direct JSON response (not abort(403)) so the 403 errorhandler
            # doesn't redirect external schedulers to /login.
            return jsonify({'ok': False, 'error': 'invalid or missing secret'}), 403
        from services.school_year_closure import run_closure_tick
        result = run_closure_tick(actor_label='cron')
        return jsonify({'ok': True, 'result': result})

    # ------------------------------------------------------------------
    # Request access log via Flask (Werkzeug's own access log sometimes
    # doesn't propagate to the root logger under certain Windows setups).
    # We log through ``app.logger`` which inherits the flushing handlers
    # installed by ``_bootstrap_logging`` at the top of this file, so every
    # request reliably appears in both stderr and ``logs/server.log``.
    # ------------------------------------------------------------------
    _access_logger = logging.getLogger('clara.access')

    # Wrap the WSGI app so we log EVERY request — this is below Flask's
    # request lifecycle and works even if middleware short-circuits before
    # before_request hooks fire.
    _inner_wsgi = app.wsgi_app

    def _logging_wsgi(environ, start_response):
        method = environ.get('REQUEST_METHOD', '-')
        path = environ.get('PATH_INFO', '-')
        qs = environ.get('QUERY_STRING')
        full = f"{path}?{qs}" if qs else path
        remote = environ.get('HTTP_X_FORWARDED_FOR') or environ.get('REMOTE_ADDR', '-')

        status_holder = {'status': '???'}

        def _start_response(status, headers, exc_info=None):
            status_holder['status'] = status
            return start_response(status, headers, exc_info)

        try:
            result = _inner_wsgi(environ, _start_response)
        except Exception:
            _access_logger.exception('%s "%s %s" CRASHED', remote, method, full)
            raise

        _access_logger.info('%s %s "%s %s"', remote, status_holder['status'], method, full)
        return result

    app.wsgi_app = _logging_wsgi

    return app

# Create the application instance
print("Initializing Clara Science App (first load may take 1–2 minutes)...", flush=True)
app = create_app()
print("Application ready.", flush=True)

if __name__ == '__main__':
    # use_reloader=False avoids a common Windows hang with debug mode
    print("Starting server at http://127.0.0.1:5000", flush=True)
    app.run(debug=True, port=5000, use_reloader=False)