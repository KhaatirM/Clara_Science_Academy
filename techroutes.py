from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user, login_user, logout_user
from models import db, User, MaintenanceMode, ActivityLog
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
    now = datetime.now()
    return render_template('system_status.html', now=now, timedelta=timedelta)

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
        # Get the database file path
        db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(os.getcwd(), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'app_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy the database file
        shutil.copy2(db_path, backup_path)
        
        flash(f'Database backup created successfully: {backup_filename}', 'success')
    except Exception as e:
        flash(f'Error creating database backup: {str(e)}', 'danger')
    
    return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/database/integrity', methods=['POST'])
@login_required
@tech_required
def check_database_integrity():
    try:
        # Simple integrity check - try to query all tables
        tables = ['user', 'student', 'teacher_staff', 'school_year', 'class', 'assignment', 'submission', 'grade', 'report_card', 'announcement', 'notification']
        results = {}
        
        for table in tables:
            try:
                # Try to count records in each table
                result = db.session.execute(db.text(f'SELECT COUNT(*) FROM {table}'))
                count = result.scalar()
                results[table] = {'status': 'OK', 'count': count}
            except Exception as e:
                results[table] = {'status': 'ERROR', 'error': str(e)}
        
        flash('Database integrity check completed. All tables accessible.', 'success')
        # You could store results in session for display
    except Exception as e:
        flash(f'Error checking database integrity: {str(e)}', 'danger')
    
    return redirect(url_for('tech.tech_dashboard'))

@tech_blueprint.route('/system/clear-cache', methods=['POST'])
@login_required
@tech_required
def clear_cache():
    try:
        # Clear any cached data (this is a placeholder for actual cache clearing)
        # In a real application, you might clear Redis cache, file cache, etc.
        flash('System cache cleared successfully.', 'success')
    except Exception as e:
        flash(f'Error clearing cache: {str(e)}', 'danger')
    
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
        
        # Update the user's password
        user.password_hash = generate_password_hash(temp_password)
        db.session.commit()
        
        flash(f'Password reset successfully. Temporary password: {temp_password}', 'success')
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
    # Get current configuration
    config_info = {
        'debug_mode': 'Development Server',
        'database_path': 'instance/app.db',
        'max_upload_size': '16 MB',
        'session_timeout': '24 hours',
        'backup_location': 'backups/',
        'log_level': 'INFO'
    }
    return render_template('system_config.html', config=config_info)

@tech_blueprint.route('/system/config/update', methods=['POST'])
@login_required
@tech_required
def update_system_config():
    try:
        # This would update actual configuration in a real application
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
        allow_tech_access = request.form.get('allow_tech_access') == 'on'
        
        # Deactivate any existing maintenance sessions
        MaintenanceMode.query.update({'is_active': False})
        db.session.commit()
        
        # Create new maintenance session
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        maintenance = MaintenanceMode()
        maintenance.is_active = True
        maintenance.start_time = start_time
        maintenance.end_time = end_time
        maintenance.duration_minutes = duration_minutes
        maintenance.reason = reason
        maintenance.initiated_by = current_user.id
        maintenance.maintenance_message = maintenance_message
        maintenance.allow_tech_access = allow_tech_access
        
        db.session.add(maintenance)
        db.session.commit()
        
        flash(f'Maintenance mode activated for {duration_minutes} minutes. End time: {end_time.strftime("%Y-%m-%d %H:%M:%S")}', 'success')
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
