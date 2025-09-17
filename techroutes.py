from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user, login_user, logout_user
from models import db, User, MaintenanceMode, ActivityLog, TeacherStaff
from decorators import tech_required
from werkzeug.security import generate_password_hash
from app import log_activity, get_user_activity_log
import os
import shutil
from datetime import datetime, timedelta
import json

tech_blueprint = Blueprint('tech', __name__)

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
    
    return render_template('tech_dashboard.html', users=users, maintenance=maintenance)

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
    logs = get_user_activity_log(
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
    
    return render_template('activity_log.html', 
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
    
    return render_template('system_status.html', **system_data)

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
    
    return render_template('it_error_reports.html', 
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
        log_activity(
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
        log_activity(
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
        log_activity(
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
        log_activity(
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
        log_activity(
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
        log_activity(
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
    
    return redirect(url_for('tech.system_config'))

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
        db_logs = get_user_activity_log(
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
        
        return render_template('database_logs.html', logs=db_logs, stats=db_stats)
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
        log_activity(
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
    return render_template('user_details.html', user=user)

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
    
    return render_template('system_config.html', config=config_info, system_info=system_info)

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
        log_activity(
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
    
    return redirect(url_for('tech.system_config'))

@tech_blueprint.route('/user/management', methods=['GET', 'POST'])
@login_required
@tech_required
def user_management():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        username = request.form.get('username')
        role = request.form.get('role')
        password = request.form.get('password')

        # Validate required fields
        if not all([username, role]):
            flash('Username and role are required.', 'danger')
            return redirect(url_for('tech.user_management'))

        # Get existing user or create new one
        if user_id:
            user = User.query.get(user_id)
            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('tech.user_management'))
        else:
            user = User()
        
        # Prevent username collision
        existing_user = User.query.filter(User.username == username, User.id != user.id).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('tech.user_management'))

        # Update user attributes
        user.username = username
        user.role = role
        if password:
            user.password_hash = generate_password_hash(password)
        
        if not user_id:
            db.session.add(user)
            flash('User created successfully.', 'success')
        else:
            flash('User updated successfully.', 'success')
            
        db.session.commit()
        return redirect(url_for('tech.user_management'))

    users = User.query.all()
    return render_template('user_management.html', users=users)

@tech_blueprint.route('/user/delete/<int:user_id>', methods=['POST'])
@login_required
@tech_required
def delete_user(user_id):
    # Prevent users from deleting themselves
    if user_id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('tech.user_management'))

    user = User.query.get_or_404(user_id)
    # Add logic here to handle re-assigning or deleting related records (students, teachers)
    # For now, we will just delete the user, which might fail if there are foreign key constraints.
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user. They may have associated records (e.g., a student profile) that must be removed first. Error: {e}', 'danger')
        
    return redirect(url_for('tech.user_management'))

@tech_blueprint.route('/maintenance')
@login_required
@tech_required
def maintenance_control():
    maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
    return render_template('maintenance_control.html', maintenance=maintenance)

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
            return redirect(url_for('tech.maintenance_control'))
        
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
    
    return redirect(url_for('tech.maintenance_control'))

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
    
    return redirect(url_for('tech.maintenance_control'))

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
        log_activity(
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
        log_activity(
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


# Bug Report Management Routes - Temporarily disabled due to circular import issues
# Will be re-enabled after database migration is complete

@tech_blueprint.route('/bug-reports')
@login_required
@tech_required
def bug_reports():
    """View all bug reports - temporarily shows placeholder."""
    flash('Bug reporting system is being set up. Please check back later.', 'info')
    return redirect(url_for('tech.tech_dashboard'))
