# Standard library imports
import csv
import io
import os
import shutil
import json
from datetime import datetime, timedelta

# Core Flask imports
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, Response, current_app
from flask_login import login_required, current_user, login_user, logout_user

# Database and model imports
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from models import db, User, MaintenanceMode, ActivityLog, TeacherStaff, Student, Grade, Assignment, SystemConfig, StudentDevice, AdminAuditLog
from scripts.gpa_scheduler import calculate_student_gpa
from copy import copy

# Authentication and decorators
from decorators import tech_required

# Application imports - lazy import to avoid circular dependency
def get_log_activity():
    """Lazy import of log_activity to avoid circular dependency."""
    from app import log_activity
    return log_activity

def get_user_activity_log():
    """Lazy import of get_user_activity_log to avoid circular dependency."""
    from app import get_user_activity_log
    return get_user_activity_log

# Werkzeug utilities
from werkzeug.security import generate_password_hash

tech_blueprint = Blueprint('tech', __name__)


def _parse_dt_ymd(s):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d')
    except Exception:
        return None


@tech_blueprint.route('/audit-logs')
@login_required
@tech_required
def audit_logs():
    """View management audit logs (Tech-only)."""
    q = (request.args.get('q') or '').strip()
    method = (request.args.get('method') or '').strip().upper()
    status = request.args.get('status', '').strip()
    user_id = request.args.get('user_id', '').strip()
    start = _parse_dt_ymd(request.args.get('start'))
    end = _parse_dt_ymd(request.args.get('end'))

    page = request.args.get('page', type=int) or 1
    per_page = min(200, max(20, request.args.get('per_page', type=int) or 50))

    qry = AdminAuditLog.query
    if start:
        qry = qry.filter(AdminAuditLog.created_at >= start)
    if end:
        qry = qry.filter(AdminAuditLog.created_at < (end + timedelta(days=1)))
    if method:
        qry = qry.filter(AdminAuditLog.method == method)
    if status.isdigit():
        qry = qry.filter(AdminAuditLog.status_code == int(status))
    if user_id.isdigit():
        qry = qry.filter(AdminAuditLog.user_id == int(user_id))
    if q:
        like = f"%{q}%"
        qry = qry.filter(
            or_(
                AdminAuditLog.path.ilike(like),
                AdminAuditLog.endpoint.ilike(like),
                AdminAuditLog.user_role.ilike(like),
                AdminAuditLog.ip_address.ilike(like),
            )
        )

    qry = qry.order_by(AdminAuditLog.created_at.desc())
    pagination = qry.paginate(page=page, per_page=per_page, error_out=False)

    user_options = []
    for u in User.query.order_by(User.username.asc()).all():
        user_options.append({'id': u.id, 'label': f"{u.username} ({u.role})"})

    return render_template(
        'tech/admin_audit_logs.html',
        logs=pagination.items,
        pagination=pagination,
        q=q,
        method=method,
        status=status,
        user_id=user_id,
        start=request.args.get('start', ''),
        end=request.args.get('end', ''),
        per_page=per_page,
        user_options=user_options,
    )


@tech_blueprint.route('/audit-logs/export.csv')
@login_required
@tech_required
def export_audit_logs_csv():
    """Export filtered audit logs to CSV (Tech-only)."""
    q = (request.args.get('q') or '').strip()
    method = (request.args.get('method') or '').strip().upper()
    status = request.args.get('status', '').strip()
    user_id = request.args.get('user_id', '').strip()
    start = _parse_dt_ymd(request.args.get('start'))
    end = _parse_dt_ymd(request.args.get('end'))

    qry = AdminAuditLog.query
    if start:
        qry = qry.filter(AdminAuditLog.created_at >= start)
    if end:
        qry = qry.filter(AdminAuditLog.created_at < (end + timedelta(days=1)))
    if method:
        qry = qry.filter(AdminAuditLog.method == method)
    if status.isdigit():
        qry = qry.filter(AdminAuditLog.status_code == int(status))
    if user_id.isdigit():
        qry = qry.filter(AdminAuditLog.user_id == int(user_id))
    if q:
        like = f"%{q}%"
        qry = qry.filter(
            or_(
                AdminAuditLog.path.ilike(like),
                AdminAuditLog.endpoint.ilike(like),
                AdminAuditLog.user_role.ilike(like),
                AdminAuditLog.ip_address.ilike(like),
            )
        )

    qry = qry.order_by(AdminAuditLog.created_at.desc()).limit(20000)
    rows = qry.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'created_at', 'user_id', 'user_role', 'teacher_staff_id',
        'method', 'status_code', 'duration_ms', 'endpoint', 'path',
        'ip_address', 'user_agent',
        'query_params', 'form_data', 'json_data',
    ])
    for r in rows:
        writer.writerow([
            r.created_at.isoformat() if r.created_at else '',
            r.user_id or '',
            r.user_role or '',
            r.teacher_staff_id or '',
            r.method or '',
            r.status_code or '',
            r.duration_ms or '',
            r.endpoint or '',
            r.path or '',
            r.ip_address or '',
            r.user_agent or '',
            r.query_params or '',
            r.form_data or '',
            r.json_data or '',
        ])

    out = buf.getvalue().encode('utf-8')
    return Response(
        out,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=admin_audit_logs.csv'},
    )

@tech_blueprint.route('/dashboard')
@login_required
@tech_required
def tech_dashboard():
    users = User.query.all()
    # Check if maintenance mode is active
    maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
    
    # Debug logging for tech dashboard
    print(f"Tech dashboard - User: {current_user.username}, Role: {current_user.role}")
    print(f"Maintenance mode: {maintenance.is_active if maintenance else 'None'}")
    if maintenance:
        print(f"Maintenance allow_tech_access: {maintenance.allow_tech_access}")
    
    return render_template('tech/tech_dashboard.html', users=users, maintenance=maintenance)

@tech_blueprint.route('/activity/log')
@login_required
@tech_required
def activity_log():
    """View user activity log with filtering options."""
    # Get filter parameters
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    limit = request.args.get('limit', 100, type=int)
    
    # Parse dates
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            pass
    
    # Get activity logs
    logs = get_user_activity_log()(
        user_id=user_id,
        action=action if action else None,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    # Get users for filter dropdown
    users = User.query.all()
    
    # Get unique actions for filter dropdown
    actions = db.session.query(ActivityLog.action).distinct().all()
    actions = [action[0] for action in actions]
    
    return render_template('tech/activity_log.html', 
                         logs=logs, 
                         users=users, 
                         actions=actions,
                         filters={
                             'user_id': user_id,
                             'action': action,
                             'start_date': start_date_str,
                             'end_date': end_date_str,
                             'limit': limit
                         })

@tech_blueprint.route('/system')
@login_required
@tech_required
def system():
    """Unified System page combining Status, Config, and Maintenance."""
    import psutil
    from models import User, Student, TeacherStaff, ActivityLog, BugReport, MaintenanceMode, SystemConfig
    import sys
    import flask
    
    now = datetime.now()
    
    # Get live system statistics (from system_status)
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = round(memory.used / (1024**3), 2)
        memory_total_gb = round(memory.total / (1024**3), 2)
        
        try:
            if os.name == 'nt':
                disk = psutil.disk_usage('C:\\')
            else:
                disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = round(disk.used / (1024**3), 2)
            disk_total_gb = round(disk.total / (1024**3), 2)
        except Exception:
            disk_percent = 'N/A'
            disk_used_gb = 'N/A'
            disk_total_gb = 'N/A'
        
        try:
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
        except Exception:
            network_bytes_sent = 'N/A'
            network_bytes_recv = 'N/A'
        
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = now - boot_time
        except Exception:
            uptime = 'N/A'
        
        total_users = User.query.count()
        total_students = Student.query.count()
        total_teachers = TeacherStaff.query.count()
        
        yesterday = now - timedelta(days=1)
        recent_activities = ActivityLog.query.filter(
            ActivityLog.timestamp >= yesterday
        ).count()
        
        recent_errors = ActivityLog.query.filter(
            ActivityLog.timestamp >= yesterday,
            ActivityLog.success == False
        ).count()
        
        open_bugs = BugReport.query.filter(BugReport.status == 'open').count()
        total_bugs = BugReport.query.count()
        
        maintenance_mode = MaintenanceMode.query.filter(MaintenanceMode.is_active == True).first()
        is_maintenance_mode = maintenance_mode is not None
        
        active_sessions = ActivityLog.query.filter(
            ActivityLog.timestamp >= now - timedelta(minutes=30)
        ).distinct(ActivityLog.user_id).count()
        
        system_data = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'memory_used_gb': memory_used_gb,
            'memory_total_gb': memory_total_gb,
            'disk_percent': disk_percent,
            'disk_used_gb': disk_used_gb,
            'disk_total_gb': disk_total_gb,
            'network_bytes_sent': network_bytes_sent,
            'network_bytes_recv': network_bytes_recv,
            'uptime': uptime,
            'total_users': total_users,
            'total_students': total_students,
            'total_teachers': total_teachers,
            'recent_activities': recent_activities,
            'recent_errors': recent_errors,
            'open_bugs': open_bugs,
            'total_bugs': total_bugs,
            'is_maintenance_mode': is_maintenance_mode,
            'active_sessions': active_sessions,
            'now': now,
            'timedelta': timedelta
        }
        
    except Exception as e:
        system_data = {
            'cpu_percent': 'N/A',
            'memory_percent': 'N/A',
            'memory_used_gb': 'N/A',
            'memory_total_gb': 'N/A',
            'disk_percent': 'N/A',
            'disk_used_gb': 'N/A',
            'disk_total_gb': 'N/A',
            'network_bytes_sent': 'N/A',
            'network_bytes_recv': 'N/A',
            'uptime': 'N/A',
            'total_users': User.query.count(),
            'total_students': Student.query.count(),
            'total_teachers': TeacherStaff.query.count(),
            'recent_activities': ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(days=1)
            ).count(),
            'recent_errors': ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(days=1),
                ActivityLog.success == False
            ).count(),
            'open_bugs': BugReport.query.filter(BugReport.status == 'open').count(),
            'total_bugs': BugReport.query.count(),
            'is_maintenance_mode': MaintenanceMode.query.filter(MaintenanceMode.is_active == True).first() is not None,
            'active_sessions': ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(minutes=30)
            ).distinct(ActivityLog.user_id).count(),
            'now': now,
            'timedelta': timedelta,
            'error': str(e)
        }
    
    # Get system configuration (from system_config)
    config_info = {
        'debug_mode': SystemConfig.get_value('debug_mode', 'Development Server'),
        'database_path': SystemConfig.get_value('database_path', 'instance/app.db'),
        'max_upload_size': SystemConfig.get_value('max_upload_size', '16 MB'),
        'session_timeout': SystemConfig.get_value('session_timeout', '24 hours'),
        'backup_location': SystemConfig.get_value('backup_location', 'backups/'),
        'log_level': SystemConfig.get_value('log_level', 'INFO')
    }
    site_theme_override = SystemConfig.get_value('site_theme_override') or ''

    from utils.school_timezone import (
        get_school_timezone_name,
        is_valid_iana_tz,
        SYSTEM_CONFIG_KEY,
        DEFAULT_SCHOOL_TIMEZONE,
    )

    db_school_tz = (SystemConfig.get_value(SYSTEM_CONFIG_KEY, '') or '').strip()
    env_school_tz = (current_app.config.get('SCHOOL_TIMEZONE') or '').strip() or DEFAULT_SCHOOL_TIMEZONE
    effective_school_tz = get_school_timezone_name()
    try:
        from zoneinfo import ZoneInfo

        school_tz_now = datetime.now(ZoneInfo(effective_school_tz)).strftime('%Y-%m-%d %I:%M %p %Z')
    except Exception:
        school_tz_now = '—'
    if db_school_tz and is_valid_iana_tz(db_school_tz):
        school_tz_source = 'Tech database override (applies to everyone)'
    elif db_school_tz:
        school_tz_source = 'Invalid override stored; using server default'
    else:
        school_tz_source = 'Server configuration (SCHOOL_TIMEZONE in .env / hosting)'

    system_info = {
        'python_version': sys.version.split()[0],
        'flask_version': flask.__version__,
        'database': 'SQLite',
        'server': 'Development' if config_info['debug_mode'] == 'Development Server' else 'Production'
    }
    
    # Get maintenance mode (from maintenance_control)
    maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
    
    return render_template(
        'tech/system.html',
        **system_data,
        config=config_info,
        system_info=system_info,
        maintenance=maintenance,
        site_theme_override=site_theme_override,
        school_timezone_effective=effective_school_tz,
        school_timezone_env=env_school_tz,
        school_timezone_db_raw=db_school_tz,
        school_timezone_source_label=school_tz_source,
        school_timezone_now_sample=school_tz_now,
    )


THEME_CHOICES = [
    'default', 'light', 'dark', 'snowy', 'autumn', 'spring', 'summer',
    'ocean', 'forest', 'holiday',
    'sunset', 'midnight', 'desert', 'lavender', 'rose', 'cherry',
    'aurora', 'storm', 'wine', 'mint'
]


@tech_blueprint.route('/school-timezone', methods=['POST'])
@login_required
@tech_required
def set_school_timezone():
    """Set or clear school-wide IANA timezone (SystemConfig). Applies to all users for dates and schooltime display."""
    from utils.school_timezone import is_valid_iana_tz, SYSTEM_CONFIG_KEY

    action = request.form.get('action', 'set')
    if action == 'clear':
        SystemConfig.set_value(
            SYSTEM_CONFIG_KEY,
            '',
            description='School IANA timezone override (empty = use SCHOOL_TIMEZONE from server config)',
            category='general',
            user_id=current_user.id,
        )
        flash(
            'School timezone override cleared. Everyone now uses the server default '
            '(SCHOOL_TIMEZONE in environment, or Eastern if unset).',
            'success',
        )
    else:
        tz = (request.form.get('school_timezone') or '').strip()
        if not tz:
            flash('Enter an IANA timezone (for example America/New_York), or clear the override.', 'warning')
        elif not is_valid_iana_tz(tz):
            flash(
                'Invalid timezone name. Use a valid IANA zone (e.g. America/Chicago). '
                'See tz database lists online.',
                'danger',
            )
        else:
            SystemConfig.set_value(
                SYSTEM_CONFIG_KEY,
                tz,
                description='School-wide IANA timezone for assignment windows, attendance logic, and displayed times',
                category='general',
                user_id=current_user.id,
            )
            flash(f'School timezone set to "{tz}" for everyone.', 'success')
    try:
        get_log_activity()(
            user_id=current_user.id,
            action='set_school_timezone',
            details={'action': action, 'timezone': (request.form.get('school_timezone') or '').strip()},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
        )
    except Exception:
        pass
    return redirect(url_for('tech.system'))


@tech_blueprint.route('/site-theme', methods=['POST'])
@login_required
@tech_required
def set_site_theme():
    """Set or clear the site-wide theme override. All users will see this theme until cleared."""
    action = request.form.get('action', 'set')
    if action == 'clear':
        SystemConfig.set_value('site_theme_override', '', description='Site-wide theme override (empty = use each user\'s preference)', category='general', user_id=current_user.id)
        flash('Site theme override cleared. Everyone will see their own theme again.', 'success')
    else:
        theme = (request.form.get('theme') or '').strip().lower()
        if theme not in THEME_CHOICES:
            flash('Invalid theme selected.', 'warning')
        else:
            SystemConfig.set_value('site_theme_override', theme, description='Site-wide theme override', category='general', user_id=current_user.id)
            flash(f'Site theme set to "{theme}" for everyone. Users will see this theme until you clear it.', 'success')
    return redirect(url_for('tech.system'))


@tech_blueprint.route('/system/status')
@login_required
@tech_required
def system_status():
    import psutil
    from models import User, Student, TeacherStaff, ActivityLog, BugReport, MaintenanceMode
    
    now = datetime.now()
    
    # Get live system statistics
    try:
        # CPU and Memory usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = round(memory.used / (1024**3), 2)
        memory_total_gb = round(memory.total / (1024**3), 2)
        
        # Disk usage - handle different operating systems
        try:
            if os.name == 'nt':  # Windows
                disk = psutil.disk_usage('C:\\')
            else:  # Unix/Linux/Mac
                disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = round(disk.used / (1024**3), 2)
            disk_total_gb = round(disk.total / (1024**3), 2)
        except Exception:
            # Fallback if disk usage fails
            disk_percent = 'N/A'
            disk_used_gb = 'N/A'
            disk_total_gb = 'N/A'
        
        # Network statistics
        try:
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
        except Exception:
            network_bytes_sent = 'N/A'
            network_bytes_recv = 'N/A'
        
        # System uptime
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = now - boot_time
        except Exception:
            uptime = 'N/A'
        
        # Database statistics
        total_users = User.query.count()
        total_students = Student.query.count()
        total_teachers = TeacherStaff.query.count()
        
        # Recent activity (last 24 hours)
        yesterday = now - timedelta(days=1)
        recent_activities = ActivityLog.query.filter(
            ActivityLog.timestamp >= yesterday
        ).count()
        
        # Error statistics (last 24 hours)
        recent_errors = ActivityLog.query.filter(
            ActivityLog.timestamp >= yesterday,
            ActivityLog.success == False
        ).count()
        
        # Bug reports statistics
        open_bugs = BugReport.query.filter(BugReport.status == 'open').count()
        total_bugs = BugReport.query.count()
        
        # Maintenance mode status
        maintenance_mode = MaintenanceMode.query.filter(MaintenanceMode.is_active == True).first()
        is_maintenance_mode = maintenance_mode is not None
        
        # Active sessions (approximation based on recent activity)
        active_sessions = ActivityLog.query.filter(
            ActivityLog.timestamp >= now - timedelta(minutes=30)
        ).distinct(ActivityLog.user_id).count()
        
        system_data = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'memory_used_gb': memory_used_gb,
            'memory_total_gb': memory_total_gb,
            'disk_percent': disk_percent,
            'disk_used_gb': disk_used_gb,
            'disk_total_gb': disk_total_gb,
            'network_bytes_sent': network_bytes_sent,
            'network_bytes_recv': network_bytes_recv,
            'uptime': uptime,
            'total_users': total_users,
            'total_students': total_students,
            'total_teachers': total_teachers,
            'recent_activities': recent_activities,
            'recent_errors': recent_errors,
            'open_bugs': open_bugs,
            'total_bugs': total_bugs,
            'is_maintenance_mode': is_maintenance_mode,
            'active_sessions': active_sessions,
            'now': now,
            'timedelta': timedelta
        }
        
    except Exception as e:
        # Fallback data if psutil fails
        system_data = {
            'cpu_percent': 'N/A',
            'memory_percent': 'N/A',
            'memory_used_gb': 'N/A',
            'memory_total_gb': 'N/A',
            'disk_percent': 'N/A',
            'disk_used_gb': 'N/A',
            'disk_total_gb': 'N/A',
            'network_bytes_sent': 'N/A',
            'network_bytes_recv': 'N/A',
            'uptime': 'N/A',
            'total_users': User.query.count(),
            'total_students': Student.query.count(),
            'total_teachers': TeacherStaff.query.count(),
            'recent_activities': ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(days=1)
            ).count(),
            'recent_errors': ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(days=1),
                ActivityLog.success == False
            ).count(),
            'open_bugs': BugReport.query.filter(BugReport.status == 'open').count(),
            'total_bugs': BugReport.query.count(),
            'is_maintenance_mode': MaintenanceMode.query.filter(MaintenanceMode.is_active == True).first() is not None,
            'active_sessions': ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(minutes=30)
            ).distinct(ActivityLog.user_id).count(),
            'now': now,
            'timedelta': timedelta,
            'error': str(e)
        }
    
    return render_template('management/system_status.html', **system_data)

@tech_blueprint.route('/error/reports')
@login_required
@tech_required
def error_reports():
    """Unified Error/Bug Log with both system errors and user-submitted bug reports."""
    from models import BugReport
    
    # Get error logs from activity log
    error_logs = ActivityLog.query.filter(
        ActivityLog.success == False
    ).order_by(ActivityLog.timestamp.desc()).limit(50).all()
    
    # Get bug reports
    bug_reports = BugReport.query.order_by(BugReport.created_at.desc()).limit(50).all()
    
    # Get error statistics
    error_stats = db.session.query(
        ActivityLog.action,
        db.func.count(ActivityLog.id).label('count')
    ).filter(
        ActivityLog.success == False
    ).group_by(ActivityLog.action).all()
    
    # Get bug report statistics
    bug_stats = db.session.query(
        BugReport.status,
        db.func.count(BugReport.id).label('count')
    ).group_by(BugReport.status).all()
    
    # Get filter parameters
    type_filter = request.args.get('type_filter', 'All')
    status_filter = request.args.get('status_filter', 'All')
    date_filter = request.args.get('date_filter', '7d')
    
    # Apply filters
    if type_filter == 'Errors':
        bug_reports = []
    elif type_filter == 'Bugs':
        error_logs = []
    
    if status_filter != 'All':
        bug_reports = [report for report in bug_reports if report.status == status_filter]
    
    if date_filter == '24h':
        cutoff = datetime.now() - timedelta(hours=24)
        error_logs = [log for log in error_logs if log.timestamp >= cutoff]
        bug_reports = [report for report in bug_reports if report.created_at >= cutoff]
    elif date_filter == '7d':
        cutoff = datetime.now() - timedelta(days=7)
        error_logs = [log for log in error_logs if log.timestamp >= cutoff]
        bug_reports = [report for report in bug_reports if report.created_at >= cutoff]
    elif date_filter == '30d':
        cutoff = datetime.now() - timedelta(days=30)
        error_logs = [log for log in error_logs if log.timestamp >= cutoff]
        bug_reports = [report for report in bug_reports if report.created_at >= cutoff]
    
    # Combine and sort all entries by timestamp
    all_entries = []
    
    # Add error logs with type identifier
    for log in error_logs:
        all_entries.append({
            'type': 'error',
            'timestamp': log.timestamp,
            'data': log
        })
    
    # Add bug reports with type identifier
    for report in bug_reports:
        all_entries.append({
            'type': 'bug',
            'timestamp': report.created_at,
            'data': report
        })
    
    # Sort by timestamp (newest first)
    all_entries.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('tech/it_error_reports.html', 
                         all_entries=all_entries,
                         error_stats=error_stats,
                         bug_stats=bug_stats,
                         type_filter=type_filter,
                         status_filter=status_filter,
                         date_filter=date_filter)

@tech_blueprint.route('/database/backup', methods=['POST'])
@login_required
@tech_required
def backup_database():
    try:
        # Get the database file path - handle different operating systems
        if os.name == 'nt':  # Windows
            db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
        else:  # Unix/Linux/Mac
            db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
        
        # Check if database file exists
        if not os.path.exists(db_path):
            flash('Database file not found. Cannot create backup.', 'danger')
            return redirect(url_for('tech.tech_dashboard'))
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(os.getcwd(), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'app_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy the database file
        shutil.copy2(db_path, backup_path)
        
        # Verify backup was created successfully
        if not os.path.exists(backup_path):
            raise Exception("Backup file was not created successfully")
        
        # Log the backup action
        get_log_activity()(
            user_id=current_user.id,
            action='database_backup',
            details={'backup_file': backup_filename, 'backup_size': os.path.getsize(backup_path)},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        flash(f'Database backup created successfully: {backup_filename}', 'success')
    except Exception as e:
        flash(f'Error creating database backup: {str(e)}', 'danger')
        # Log the error
        get_log_activity()(
            user_id=current_user.id,
            action='database_backup_failed',
            details={'error': str(e)},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=False,
            error_message=str(e)
        )
    
    return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/database/integrity', methods=['POST'])
@login_required
@tech_required
def check_database_integrity():
    try:
        # Get list of tables that actually exist in the database
        existing_tables = []
        try:
            result = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
            existing_tables = [row[0] for row in result.fetchall()]
        except Exception as e:
            flash(f'Error getting table list: {str(e)}', 'danger')
            return redirect(url_for('tech.tech_dashboard'))
        
        # Define tables to check (only those that exist)
        tables_to_check = ['user', 'student', 'teacher_staff', 'school_year', 'class', 'assignment', 'submission', 'grade', 'report_card', 'announcement', 'notification', 'maintenance_mode', 'activity_log', 'bug_report', 'attendance', 'system_config']
        
        # Filter to only check existing tables
        tables = [table for table in tables_to_check if table in existing_tables]
        
        results = {}
        errors_found = 0
        
        for table in tables:
            try:
                # Try to count records in each table
                result = db.session.execute(db.text(f'SELECT COUNT(*) FROM {table}'))
                count = result.scalar()
                results[table] = {'status': 'OK', 'count': count}
            except Exception as e:
                results[table] = {'status': 'ERROR', 'error': str(e)}
                errors_found += 1
        
        # Log the integrity check
        get_log_activity()(
            user_id=current_user.id,
            action='database_integrity_check',
            details={'tables_checked': len(tables), 'errors_found': errors_found, 'results': results},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        if errors_found == 0:
            flash(f'Database integrity check completed successfully. {len(tables)} tables checked and accessible.', 'success')
        else:
            flash(f'Database integrity check completed with {errors_found} errors. Check logs for details.', 'warning')
            
    except Exception as e:
        flash(f'Error checking database integrity: {str(e)}', 'danger')
        # Log the error
        get_log_activity()(
            user_id=current_user.id,
            action='database_integrity_check_failed',
            details={'error': str(e)},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=False,
            error_message=str(e)
        )
    
    return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/system/clear-cache', methods=['POST'])
@login_required
@tech_required
def clear_cache():
    try:
        # Clear any cached data (this is a placeholder for actual cache clearing)
        # In a real application, you might clear Redis cache, file cache, etc.
        
        # Log the cache clearing action
        get_log_activity()(
            user_id=current_user.id,
            action='clear_system_cache',
            details={'cache_type': 'all'},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        flash('System cache cleared successfully.', 'success')
    except Exception as e:
        flash(f'Error clearing cache: {str(e)}', 'danger')
    
    return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/system/restart-server', methods=['POST'])
@login_required
@tech_required
def restart_server():
    try:
        # Log the restart action
        get_log_activity()(
            user_id=current_user.id,
            action='restart_server',
            details={'initiated_by': current_user.username},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        flash('Server restart initiated. Please wait a moment for the server to restart.', 'warning')
        # In a real application, you would implement actual server restart logic
        # For now, we'll just show a message
    except Exception as e:
        flash(f'Error restarting server: {str(e)}', 'danger')
    
    return redirect(url_for('tech.system'))

@tech_blueprint.route('/system/view-logs')
@login_required
@tech_required
def view_system_logs():
    """View system logs - redirect to activity log with system filter"""
    return redirect(url_for('tech.activity_log', action='system'))

@tech_blueprint.route('/database/logs')
@login_required
@tech_required
def view_database_logs():
    """View database-specific logs and operations"""
    try:
        # Get recent database operations from activity log
        db_logs = get_user_activity_log()(
            action='database',
            limit=50
        )
        
        # Get database statistics
        from models import User, Student, TeacherStaff, Class, Assignment, Grade, ReportCard
        db_stats = {
            'users': User.query.count(),
            'students': Student.query.count(),
            'teachers': TeacherStaff.query.count(),
            'classes': Class.query.count(),
            'assignments': Assignment.query.count(),
            'grades': Grade.query.count(),
            'report_cards': ReportCard.query.count()
        }
        
        return render_template('management/database_logs.html', logs=db_logs, stats=db_stats)
    except Exception as e:
        flash(f'Error viewing database logs: {str(e)}', 'danger')
        return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/system/update', methods=['POST'])
@login_required
@tech_required
def update_system():
    """Initiate system update process"""
    try:
        # Log the update action
        get_log_activity()(
            user_id=current_user.id,
            action='initiate_system_update',
            details={'timestamp': datetime.now().isoformat()},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # In a real application, this would trigger an actual update process
        # For now, we'll simulate the update process
        flash('System update initiated. This is a simulation - no actual update will occur.', 'info')
        
    except Exception as e:
        flash(f'Error initiating system update: {str(e)}', 'danger')
    
    return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/user/reset-password/<int:user_id>', methods=['POST'])
@login_required
@tech_required
def reset_user_password(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        # Generate a temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        
        # Update the user's password and set temporary flag
        user.password_hash = generate_password_hash(temp_password)
        user.is_temporary_password = True
        user.password_changed_at = None  # Reset password change timestamp
        db.session.commit()
        
        flash(f'Password reset successfully. Temporary password: {temp_password}. User will be required to change password on next login.', 'success')
    except Exception as e:
        flash(f'Error resetting password: {str(e)}', 'danger')
    
    return redirect(url_for('tech.user_management'))

@tech_blueprint.route('/user/view/<int:user_id>')
@login_required
@tech_required
def view_user_details(user_id):
    user = User.query.get_or_404(user_id)
    
    # --- GPA IMPACT ANALYSIS ---
    current_gpa = None
    hypothetical_gpa = None
    at_risk_grades_list = []
    all_missing_assignments = []
    class_gpa_breakdown = []
    class_assignments_impact = {}

    if user.student_profile:
        student = user.student_profile 
        all_grades = Grade.query.filter_by(student_id=student.id).all()
        
        # Get all classes this student is enrolled in
        from models import Enrollment
        enrollments = Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
        student_classes = {enrollment.class_id: enrollment.class_info for enrollment in enrollments if enrollment.class_info}
        
        # Separate grades by class and find missing/at-risk assignments
        grades_by_class = {}
        for g in all_grades:
            class_id = g.assignment.class_id
            if class_id not in grades_by_class:
                grades_by_class[class_id] = []
            grades_by_class[class_id].append(g)
            
            try:
                grade_data = json.loads(g.grade_data)
                score = grade_data.get('score')
                g.display_score = score
                
                # Check if assignment is past due
                if g.assignment.due_date < datetime.utcnow():
                    if score is None:
                        # Missing assignment
                        all_missing_assignments.append({
                            'grade': g,
                            'assignment': g.assignment,
                            'class_name': g.assignment.class_info.name,
                            'due_date': g.assignment.due_date,
                            'status': 'missing'
                        })
                    elif score <= 69:
                        # Failing assignment
                        at_risk_grades_list.append(g)
                        all_missing_assignments.append({
                            'grade': g,
                            'assignment': g.assignment,
                            'class_name': g.assignment.class_info.name,
                            'due_date': g.assignment.due_date,
                            'status': 'failing',
                            'score': score
                        })
            except (json.JSONDecodeError, TypeError):
                continue

        # Calculate Current Overall GPA
        current_gpa = calculate_student_gpa(all_grades) 

        # Calculate GPA per class
        for class_id, class_grades in grades_by_class.items():
            if class_id in student_classes:
                class_obj = student_classes[class_id]
                class_current_gpa = calculate_student_gpa(class_grades)
                
                # Calculate hypothetical GPA for this class (fixing at-risk assignments)
                class_at_risk = [g for g in class_grades if g in at_risk_grades_list]
                class_hypothetical_grades = []
                for g in class_grades:
                    if g in class_at_risk:
                        hypothetical_grade = copy(g)
                        try:
                            grade_data = json.loads(g.grade_data)
                            grade_data['score'] = 70
                            hypothetical_grade.grade_data = json.dumps(grade_data)
                            class_hypothetical_grades.append(hypothetical_grade)
                        except (json.JSONDecodeError, TypeError):
                            class_hypothetical_grades.append(g)
                    else:
                        class_hypothetical_grades.append(g)
                
                class_hypothetical_gpa = calculate_student_gpa(class_hypothetical_grades)
                
                # Get assignments impacting this class
                class_impact_assignments = [
                    item for item in all_missing_assignments 
                    if item['assignment'].class_id == class_id
                ]
                
                class_gpa_breakdown.append({
                    'class_name': class_obj.name,
                    'class_id': class_id,
                    'current_gpa': class_current_gpa,
                    'hypothetical_gpa': class_hypothetical_gpa,
                    'impact_assignments': class_impact_assignments,
                    'total_assignments': len(class_grades)
                })
        
        # Calculate Hypothetical Overall GPA
        hypothetical_grades = []
        for g in all_grades:
            if g in at_risk_grades_list:
                hypothetical_grade = copy(g)
                try:
                    grade_data = json.loads(g.grade_data)
                    grade_data['score'] = 70
                    hypothetical_grade.grade_data = json.dumps(grade_data)
                    hypothetical_grades.append(hypothetical_grade)
                except (json.JSONDecodeError, TypeError):
                    hypothetical_grades.append(g)
            else:
                hypothetical_grades.append(g)
        
        hypothetical_gpa = calculate_student_gpa(hypothetical_grades)
    # --- END GPA ANALYSIS ---
    
    return render_template('management/user_details.html', 
                         user=user,
                         current_gpa=current_gpa,
                         hypothetical_gpa=hypothetical_gpa,
                         at_risk_grades_list=at_risk_grades_list,
                         all_missing_assignments=all_missing_assignments,
                         class_gpa_breakdown=class_gpa_breakdown)

@tech_blueprint.route('/system/config')
@login_required
@tech_required
def system_config():
    from models import SystemConfig
    import sys
    import flask
    
    # Get current configuration from database
    config_info = {
        'debug_mode': SystemConfig.get_value('debug_mode', 'Development Server'),
        'database_path': SystemConfig.get_value('database_path', 'instance/app.db'),
        'max_upload_size': SystemConfig.get_value('max_upload_size', '16 MB'),
        'session_timeout': SystemConfig.get_value('session_timeout', '24 hours'),
        'backup_location': SystemConfig.get_value('backup_location', 'backups/'),
        'log_level': SystemConfig.get_value('log_level', 'INFO')
    }
    
    # Get system information
    system_info = {
        'python_version': sys.version.split()[0],
        'flask_version': flask.__version__,
        'database': 'SQLite',
        'server': 'Development' if config_info['debug_mode'] == 'Development Server' else 'Production'
    }
    
    return render_template('management/system_config.html', config=config_info, system_info=system_info)

@tech_blueprint.route('/system/config/update', methods=['POST'])
@login_required
@tech_required
def update_system_config():
    from models import SystemConfig
    
    try:
        # Get form data
        debug_mode = request.form.get('debug_mode')
        max_upload_size = request.form.get('max_upload_size')
        session_timeout = request.form.get('session_timeout')
        backup_location = request.form.get('backup_location')
        log_level = request.form.get('log_level')
        
        # Update configuration in database
        SystemConfig.set_value('debug_mode', debug_mode, 'Server mode configuration', 'general', current_user.id)
        SystemConfig.set_value('max_upload_size', max_upload_size, 'Maximum file upload size', 'performance', current_user.id)
        SystemConfig.set_value('session_timeout', session_timeout, 'User session timeout duration', 'security', current_user.id)
        SystemConfig.set_value('backup_location', backup_location, 'Database backup directory', 'backup', current_user.id)
        SystemConfig.set_value('log_level', log_level, 'Application logging level', 'general', current_user.id)
        
        # Log the configuration update
        get_log_activity()(
            user_id=current_user.id,
            action='update_system_config',
            details={
                'debug_mode': debug_mode,
                'max_upload_size': max_upload_size,
                'session_timeout': session_timeout,
                'backup_location': backup_location,
                'log_level': log_level
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        flash('System configuration updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating configuration: {str(e)}', 'danger')
    
    return redirect(url_for('tech.system'))

@tech_blueprint.route('/user/management', methods=['GET'])
@login_required
@tech_required
def user_management():
    users = (
        User.query.options(
            joinedload(User.student_profile),
            joinedload(User.teacher_staff_profile),
        )
        .order_by(User.username.asc())
        .all()
    )
    from utils.tech_user_management import partition_users_for_tech_management

    parts = partition_users_for_tech_management(users)
    return render_template(
        'management/user_management.html',
        **parts,
    )

@tech_blueprint.route('/maintenance')
@login_required
@tech_required
def maintenance_control():
    maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
    return render_template('management/maintenance_control.html', maintenance=maintenance)

@tech_blueprint.route('/maintenance/start', methods=['POST'])
@login_required
@tech_required
def start_maintenance():
    try:
        # Get form data
        duration_minutes = int(request.form.get('duration_minutes', 60))
        reason = request.form.get('reason', 'Scheduled maintenance')
        maintenance_message = request.form.get('maintenance_message', 'System is under maintenance. Please check back later.')
        
        # Validate duration (max 7 days = 10080 minutes)
        max_duration = 7 * 24 * 60  # 7 days in minutes
        if duration_minutes > max_duration:
            flash(f'Error: Maximum maintenance duration is 7 days ({max_duration} minutes).', 'danger')
            return redirect(url_for('tech.system'))
        
        # Deactivate any existing maintenance sessions
        MaintenanceMode.query.update({'is_active': False})
        db.session.commit()
        
        # Create new maintenance session using UTC time
        from datetime import timezone
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        maintenance = MaintenanceMode()
        maintenance.is_active = True
        maintenance.start_time = start_time
        maintenance.end_time = end_time
        maintenance.duration_minutes = duration_minutes
        maintenance.reason = reason
        maintenance.initiated_by = current_user.id
        maintenance.maintenance_message = maintenance_message
        maintenance.allow_tech_access = True  # Tech users always have access
        
        db.session.add(maintenance)
        db.session.commit()
        
        # Format duration for display
        if duration_minutes >= 1440:  # 1 day or more
            days = duration_minutes // 1440
            hours = (duration_minutes % 1440) // 60
            if hours > 0:
                duration_display = f"{days} day{'s' if days > 1 else ''} and {hours} hour{'s' if hours > 1 else ''}"
            else:
                duration_display = f"{days} day{'s' if days > 1 else ''}"
        elif duration_minutes >= 60:  # 1 hour or more
            hours = duration_minutes // 60
            minutes = duration_minutes % 60
            if minutes > 0:
                duration_display = f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minute{'s' if minutes > 1 else ''}"
            else:
                duration_display = f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            duration_display = f"{duration_minutes} minute{'s' if duration_minutes > 1 else ''}"
        
        flash(f'Maintenance mode activated for {duration_display}. End time: {end_time.strftime("%Y-%m-%d %H:%M:%S")}', 'success')
    except Exception as e:
        flash(f'Error starting maintenance mode: {str(e)}', 'danger')
    
    return redirect(url_for('tech.system'))

@tech_blueprint.route('/maintenance/stop', methods=['POST'])
@login_required
@tech_required
def stop_maintenance():
    try:
        # Deactivate all maintenance sessions
        MaintenanceMode.query.update({'is_active': False})
        db.session.commit()
        
        flash('Maintenance mode deactivated successfully.', 'success')
    except Exception as e:
        flash(f'Error stopping maintenance mode: {str(e)}', 'danger')
    
    return redirect(url_for('tech.system'))

@tech_blueprint.route('/user/impersonate/<int:user_id>')
@login_required
@tech_required
def impersonate_user(user_id):
    """Allow tech users to impersonate other users for troubleshooting."""
    try:
        target_user = User.query.get_or_404(user_id)
        
        # Prevent self-impersonation
        if target_user.id == current_user.id:
            flash('You cannot impersonate yourself.', 'danger')
            return redirect(url_for('tech.user_management'))
        
        # Log the impersonation action
        get_log_activity()(
            user_id=current_user.id,
            action='impersonate_user',
            details={
                'target_user_id': target_user.id,
                'target_username': target_user.username,
                'target_role': target_user.role
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Store original user info in session
        session['original_user_id'] = current_user.id
        session['original_username'] = current_user.username
        session['impersonating_user_id'] = target_user.id
        session['impersonating_username'] = target_user.username
        
        # Log in as the target user
        login_user(target_user)
        
        flash(f'Now impersonating {target_user.username} ({target_user.role})', 'warning')
        return redirect(url_for('auth.dashboard'))
        
    except Exception as e:
        flash(f'Error impersonating user: {str(e)}', 'danger')
        return redirect(url_for('tech.user_management'))

@tech_blueprint.route('/user/stop-impersonating')
@login_required
def stop_impersonating():
    """Stop impersonating and return to original tech user."""
    try:
        if 'original_user_id' not in session:
            flash('You are not currently impersonating anyone.', 'info')
            return redirect(url_for('tech.tech_dashboard'))
        
        # Get original user
        original_user = User.query.get(session['original_user_id'])
        if not original_user:
            flash('Original user not found. Logging out.', 'danger')
            logout_user()
            return redirect(url_for('auth.login'))
        
        # Log the stop impersonation action
        get_log_activity()(
            user_id=original_user.id,
            action='stop_impersonating',
            details={
                'was_impersonating_user_id': session.get('impersonating_user_id'),
                'was_impersonating_username': session.get('impersonating_username')
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Clear impersonation session data
        session.pop('original_user_id', None)
        session.pop('original_username', None)
        session.pop('impersonating_user_id', None)
        session.pop('impersonating_username', None)
        
        # Log in as original user
        login_user(original_user)
        
        flash('Stopped impersonating. Back to tech user.', 'success')
        return redirect(url_for('tech.tech_dashboard'))
        
    except Exception as e:
        flash(f'Error stopping impersonation: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))


# --- Student devices (laptops / tablets) ---------------------------------

DEVICE_TYPES = ('laptop', 'tablet')


def _normalize_device_type(raw):
    if not raw:
        return None
    s = str(raw).strip().lower()
    return s if s in DEVICE_TYPES else None


def _device_type_fits_grade(device_type, grade_level):
    """Grade 3+ → laptop; grade 2 and below → tablet. None grade: no enforced rule."""
    if grade_level is None:
        return True
    try:
        g = int(grade_level)
    except (TypeError, ValueError):
        return True
    if device_type == 'laptop':
        return g >= 3
    if device_type == 'tablet':
        return g <= 2
    return False


def _expected_device_label(grade_level):
    if grade_level is None:
        return None
    try:
        g = int(grade_level)
    except (TypeError, ValueError):
        return None
    return 'laptop' if g >= 3 else 'tablet'


def _students_selectable_for_device(exclude_device_id=None):
    """Students with no device assigned, or (when editing) keep current holder."""
    q_busy = db.session.query(StudentDevice.student_id)
    if exclude_device_id is not None:
        q_busy = q_busy.filter(StudentDevice.id != exclude_device_id)
    busy_ids = {row[0] for row in q_busy.all()}
    if not busy_ids:
        return Student.query.order_by(Student.last_name, Student.first_name).all()
    return (
        Student.query.filter(~Student.id.in_(busy_ids))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )


def _parse_device_form():
    device_type = _normalize_device_type(request.form.get('device_type'))
    asset_name = (request.form.get('asset_name') or '').strip()
    device_name = (request.form.get('device_name') or '').strip() or None
    cord_number = (request.form.get('cord_number') or '').strip() or None
    operating_system = (request.form.get('operating_system') or '').strip() or None
    student_id_raw = request.form.get('student_id')
    student_id = int(student_id_raw) if student_id_raw and str(student_id_raw).isdigit() else None
    return device_type, asset_name, device_name, cord_number, operating_system, student_id


def _norm_csv_header(h):
    if h is None:
        return ''
    return str(h).strip().lower().replace(' ', '_')


def _csv_cell(row, *keys):
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ''


def _student_from_csv_row(row):
    """Resolve Student from normalized row dict. student_db_id = internal PK; school_student_id / student_id = Student.student_id."""
    db_raw = _csv_cell(row, 'student_db_id', 'student_pk', 'db_student_id', 'internal_student_id')
    school_raw = _csv_cell(
        row, 'school_student_id', 'school_id', 'state_student_id', 'student_id_number', 'student_id'
    )
    if db_raw and db_raw.isdigit():
        stu = Student.query.get(int(db_raw))
        if stu:
            return stu
    if school_raw:
        stu = Student.query.filter_by(student_id=school_raw).first()
        if stu:
            return stu
    return None


def _upsert_device_from_csv_row(device_type, asset_name, device_name, cord_number, operating_system, stu, row_num):
    """
    Create or update by asset_name. Reassigns student on that asset if needed.
    Returns (success: bool, message: str).
    """
    if not device_type or not asset_name or not stu:
        return False, f'Row {row_num}: missing device type, asset name, or student'

    if not _device_type_fits_grade(device_type, stu.grade_level):
        exp = _expected_device_label(stu.grade_level)
        return (
            False,
            f'Row {row_num}: type "{device_type}" does not match grade '
            f'{stu.grade_level if stu.grade_level is not None else "N/A"} (expected {exp or "matching type"})',
        )

    by_asset = StudentDevice.query.filter_by(asset_name=asset_name).first()
    by_student = stu.assigned_school_device

    if by_asset and by_student and by_asset.id != by_student.id:
        return (
            False,
            f'Row {row_num}: asset "{asset_name}" is assigned elsewhere and student '
            f'{stu.first_name} {stu.last_name} already has "{by_student.asset_name}"',
        )

    if by_asset:
        conflict = StudentDevice.query.filter(
            StudentDevice.student_id == stu.id,
            StudentDevice.id != by_asset.id,
        ).first()
        if conflict:
            return (
                False,
                f'Row {row_num}: student already has device "{conflict.asset_name}"',
            )
        by_asset.device_type = device_type
        by_asset.device_name = device_name
        by_asset.cord_number = cord_number
        by_asset.operating_system = operating_system
        by_asset.student_id = stu.id
        return True, 'updated'

    if by_student:
        if by_student.asset_name != asset_name:
            return (
                False,
                f'Row {row_num}: student already has device "{by_student.asset_name}" (not "{asset_name}")',
            )
        by_student.device_type = device_type
        by_student.device_name = device_name
        by_student.cord_number = cord_number
        by_student.operating_system = operating_system
        return True, 'updated'

    db.session.add(
        StudentDevice(
            device_type=device_type,
            asset_name=asset_name,
            device_name=device_name,
            cord_number=cord_number,
            operating_system=operating_system,
            student_id=stu.id,
        )
    )
    return True, 'created'


@tech_blueprint.route('/devices/csv-template')
@login_required
@tech_required
def devices_csv_template():
    """Download a blank CSV with headers and example rows."""
    lines = [
        'device_type,asset_name,device_name,cord_number,operating_system,student_db_id,school_student_id',
        'laptop,CSA-Laptop-1,Dell Latitude,1,Windows 11,42,',
        'tablet,CSA-Tablet-2,,2,iPadOS 17,,ABC12345',
    ]
    body = '\r\n'.join(lines) + '\r\n'
    return Response(
        body,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=student_devices_template.csv'},
    )


@tech_blueprint.route('/devices/bulk-upload', methods=['POST'])
@login_required
@tech_required
def devices_bulk_upload():
    """Import devices from CSV (one row per device). Upserts by asset_name."""
    upload = request.files.get('csv_file')
    if not upload or not upload.filename:
        flash('Choose a CSV file to upload.', 'danger')
        return redirect(url_for('tech.devices'))
    if not upload.filename.lower().endswith('.csv'):
        flash('Please upload a .csv file.', 'danger')
        return redirect(url_for('tech.devices'))

    raw = upload.read()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            flash('Could not read file as UTF-8. Save the spreadsheet as CSV UTF-8.', 'danger')
            return redirect(url_for('tech.devices'))

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        flash('CSV has no header.', 'danger')
        return redirect(url_for('tech.devices'))

    headers = [_norm_csv_header(h) for h in reader.fieldnames]
    if 'device_type' not in headers or 'asset_name' not in headers:
        flash('CSV must include columns: device_type, asset_name (see Download template).', 'danger')
        return redirect(url_for('tech.devices'))

    created = updated = 0
    errors = []
    row_num = 1

    for raw_row in reader:
        row_num += 1
        if not raw_row or not any((v and str(v).strip()) for v in raw_row.values()):
            continue
        row = {}
        for k, v in raw_row.items():
            if k is None:
                continue
            nk = _norm_csv_header(k)
            if v is None or v == '':
                row[nk] = ''
            else:
                row[nk] = str(v).strip()

        device_type = _normalize_device_type(_csv_cell(row, 'device_type', 'type'))
        asset_name = _csv_cell(row, 'asset_name', 'laptop_name', 'tablet_name', 'inventory_name')
        device_name = _csv_cell(row, 'device_name') or None
        cord_number = _csv_cell(row, 'cord_number', 'cord', 'cord_#') or None
        operating_system = _csv_cell(row, 'operating_system', 'os') or None

        if not device_type:
            errors.append(f'Row {row_num}: invalid or missing device_type')
            continue
        if not asset_name:
            errors.append(f'Row {row_num}: missing asset_name')
            continue

        stu = _student_from_csv_row(row)
        if not stu:
            errors.append(f'Row {row_num}: student not found (set student_db_id or school_student_id / student_id)')
            continue

        try:
            ok, action = _upsert_device_from_csv_row(
                device_type, asset_name, device_name, cord_number, operating_system, stu, row_num
            )
            if not ok:
                errors.append(action)
                db.session.rollback()
                continue
            db.session.commit()
            if action == 'created':
                created += 1
            else:
                updated += 1
        except IntegrityError:
            db.session.rollback()
            errors.append(f'Row {row_num}: database conflict (duplicate asset or student)')
        except Exception as e:
            db.session.rollback()
            errors.append(f'Row {row_num}: {e}')

    if created or updated:
        flash(
            f'Bulk import finished: {created} created, {updated} updated.'
            + (f' {len(errors)} row(s) skipped.' if errors else ''),
            'success' if not errors else 'warning',
        )
    else:
        flash('No rows were imported.', 'warning')
    for msg in errors[:25]:
        flash(msg, 'danger')
    if len(errors) > 25:
        flash(f'…and {len(errors) - 25} more errors (shown first 25).', 'danger')

    return redirect(url_for('tech.devices'))


@tech_blueprint.route('/devices')
@login_required
@tech_required
def devices():
    """List assigned laptops and tablets."""
    device_type = request.args.get('type', '').strip().lower()
    search = (request.args.get('q') or '').strip()

    q = StudentDevice.query.join(Student, StudentDevice.student_id == Student.id)
    if device_type in DEVICE_TYPES:
        q = q.filter(StudentDevice.device_type == device_type)
    if search:
        like = f'%{search}%'
        q = q.filter(
            or_(
                Student.first_name.ilike(like),
                Student.last_name.ilike(like),
                Student.student_id.ilike(like),
                StudentDevice.asset_name.ilike(like),
                StudentDevice.device_name.ilike(like),
                StudentDevice.cord_number.ilike(like),
            )
        )
    records = q.order_by(StudentDevice.device_type, StudentDevice.asset_name).all()
    return render_template(
        'tech/devices.html',
        records=records,
        filters={'type': device_type, 'q': search},
    )


@tech_blueprint.route('/devices/new', methods=['GET', 'POST'])
@login_required
@tech_required
def device_new():
    if request.method == 'POST':
        device_type, asset_name, device_name, cord_number, operating_system, student_id = _parse_device_form()
        if not device_type:
            flash('Select a valid device type (laptop or tablet).', 'danger')
            return redirect(url_for('tech.device_new'))
        if not asset_name:
            flash('Asset name is required (e.g. CSA-Laptop-12 or CSA-Tablet-5).', 'danger')
            return redirect(url_for('tech.device_new'))
        if not student_id:
            flash('Select a student to attach this device to.', 'danger')
            return redirect(url_for('tech.device_new'))
        stu = Student.query.get(student_id)
        if not stu:
            flash('Student not found.', 'danger')
            return redirect(url_for('tech.device_new'))
        if stu.assigned_school_device:
            flash('That student already has a device assigned. Edit or remove it first.', 'danger')
            return redirect(url_for('tech.device_new'))
        if not _device_type_fits_grade(device_type, stu.grade_level):
            exp = _expected_device_label(stu.grade_level)
            flash(
                f'Device type does not match grade level policy: grade {stu.grade_level if stu.grade_level is not None else "N/A"} '
                f'should use a {exp or "appropriate"} — 3rd+ laptops, 2nd and below tablets.',
                'danger',
            )
            return redirect(url_for('tech.device_new'))
        if stu.grade_level is None:
            flash('This student has no grade on file; confirm the device type is correct before saving.', 'warning')
        row = StudentDevice(
            device_type=device_type,
            asset_name=asset_name,
            device_name=device_name,
            cord_number=cord_number,
            operating_system=operating_system,
            student_id=student_id,
        )
        db.session.add(row)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Could not save: duplicate asset name or student already assigned a device.', 'danger')
            return redirect(url_for('tech.device_new'))
        flash('Device assigned successfully.', 'success')
        return redirect(url_for('tech.devices'))

    students = _students_selectable_for_device()
    return render_template('tech/device_form.html', device=None, students=students)


@tech_blueprint.route('/devices/<int:device_id>/edit', methods=['GET', 'POST'])
@login_required
@tech_required
def device_edit(device_id):
    device = StudentDevice.query.get_or_404(device_id)
    if request.method == 'POST':
        device_type, asset_name, device_name, cord_number, operating_system, student_id = _parse_device_form()
        if not device_type:
            flash('Select a valid device type (laptop or tablet).', 'danger')
            return redirect(url_for('tech.device_edit', device_id=device_id))
        if not asset_name:
            flash('Asset name is required.', 'danger')
            return redirect(url_for('tech.device_edit', device_id=device_id))
        if not student_id:
            flash('Select a student.', 'danger')
            return redirect(url_for('tech.device_edit', device_id=device_id))
        stu = Student.query.get(student_id)
        if not stu:
            flash('Student not found.', 'danger')
            return redirect(url_for('tech.device_edit', device_id=device_id))
        other = StudentDevice.query.filter(
            StudentDevice.student_id == student_id,
            StudentDevice.id != device.id,
        ).first()
        if other:
            flash('That student already has a different device assigned.', 'danger')
            return redirect(url_for('tech.device_edit', device_id=device_id))
        if not _device_type_fits_grade(device_type, stu.grade_level):
            exp = _expected_device_label(stu.grade_level)
            flash(
                f'Device type does not match grade level policy (expected {exp or "appropriate type"} for this grade).',
                'danger',
            )
            return redirect(url_for('tech.device_edit', device_id=device_id))
        device.device_type = device_type
        device.asset_name = asset_name
        device.device_name = device_name
        device.cord_number = cord_number
        device.operating_system = operating_system
        device.student_id = student_id
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Could not save: duplicate asset name or conflicting assignment.', 'danger')
            return redirect(url_for('tech.device_edit', device_id=device_id))
        flash('Device updated.', 'success')
        return redirect(url_for('tech.devices'))

    students = _students_selectable_for_device(exclude_device_id=device.id)
    if device.student and device.student not in students:
        students = sorted(
            students + [device.student],
            key=lambda s: ((s.last_name or '').lower(), (s.first_name or '').lower()),
        )
    return render_template('tech/device_form.html', device=device, students=students)


@tech_blueprint.route('/devices/<int:device_id>/delete', methods=['POST'])
@login_required
@tech_required
def device_delete(device_id):
    device = StudentDevice.query.get_or_404(device_id)
    db.session.delete(device)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Could not remove device: {e}', 'danger')
        return redirect(url_for('tech.devices'))
    flash('Device assignment removed.', 'success')
    return redirect(url_for('tech.devices'))


# Bug Report Management Routes - Temporarily disabled due to circular import issues
# Will be re-enabled after database migration is complete

@tech_blueprint.route('/bug-reports')
@login_required
@tech_required
def bug_reports():
    """View all bug reports - temporarily shows placeholder."""
    flash('Bug reporting system is being set up. Please check back later.', 'info')
    return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/resources')
@login_required
@tech_required
def resources():
    """Display the resources page with MinuteMath files."""
    try:
        # Get list of PDF files in MinuteMath directory
        import os
        minute_math_dir = os.path.join(os.getcwd(), 'MinuteMath')
        study_guides_dir = os.path.join(minute_math_dir, 'StudyGuides')
        
        # Original PDF files
        pdf_files = []
        if os.path.exists(minute_math_dir):
            for filename in os.listdir(minute_math_dir):
                if filename.endswith('.pdf'):
                    pdf_files.append({
                        'name': filename,
                        'display_name': filename.replace('.pdf', ''),
                        'grade': filename.split()[0] if filename.split()[0].replace('th', '').replace('rd', '').replace('st', '').replace('nd', '').isdigit() else 'Unknown',
                        'type': 'Original',
                        'path': os.path.join('MinuteMath', filename)
                    })
        
        # Study guide files
        study_guide_files = []
        if os.path.exists(study_guides_dir):
            for filename in os.listdir(study_guides_dir):
                if filename.endswith('.txt'):
                    study_guide_files.append({
                        'name': filename,
                        'display_name': filename.replace(' - Study Guide.txt', ''),
                        'grade': filename.split()[0] if filename.split()[0].replace('th', '').replace('rd', '').replace('st', '').replace('nd', '').isdigit() else 'Unknown',
                        'type': 'Study Guide',
                        'path': os.path.join('MinuteMath', 'StudyGuides', filename)
                    })
        
        # Combine and sort by grade
        all_files = pdf_files + study_guide_files
        all_files.sort(key=lambda x: int(x['grade'].replace('th', '').replace('rd', '').replace('st', '').replace('nd', '')) if x['grade'].replace('th', '').replace('rd', '').replace('st', '').replace('nd', '').isdigit() else 999)
        
        return render_template('management/resources.html', 
                             files=all_files,
                             pdf_files=pdf_files,
                             study_guide_files=study_guide_files)
    
    except Exception as e:
        print(f"Error loading resources: {e}")
        flash('Error loading resources. Please try again.', 'error')
        return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/resources/download/<path:filename>')
@login_required
@tech_required
def download_resource(filename):
    """Download a resource file."""
    try:
        import os
        from flask import send_from_directory
        
        # Security check - ensure filename is safe
        if '..' in filename or filename.startswith('/'):
            flash('Invalid file path.', 'error')
            return redirect(url_for('tech.resources'))
        
        # Check if file exists
        file_path = os.path.join(os.getcwd(), filename)
        if not os.path.exists(file_path):
            flash('File not found.', 'error')
            return redirect(url_for('tech.resources'))
        
        # Send file for download
        directory = os.path.dirname(file_path)
        filename_only = os.path.basename(file_path)
        
        return send_from_directory(directory, filename_only, as_attachment=True)
    
    except Exception as e:
        print(f"Error downloading file {filename}: {e}")
        flash('Error downloading file. Please try again.', 'error')
        return redirect(url_for('tech.resources'))
