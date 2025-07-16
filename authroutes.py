from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db, MaintenanceMode, BugReport
from werkzeug.security import check_password_hash
from datetime import datetime
from app import log_activity
from decorators import TEACHER_ROLES

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    
    # Check for maintenance mode
    maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
    if maintenance and maintenance.end_time > datetime.now():
        # Allow tech users to login during maintenance
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            if user and password and check_password_hash(user.password_hash, password):
                if user.role == 'Tech' and maintenance.allow_tech_access:
                    login_user(user)
                    # Log successful tech login during maintenance
                    log_activity(
                        user_id=user.id,
                        action='login_maintenance',
                        details={'role': user.role, 'maintenance_mode': True},
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                    flash('Welcome back! You have access during maintenance mode.', 'info')
                    return redirect(url_for('auth.dashboard'))
                else:
                    # Log failed login attempt during maintenance
                    log_activity(
                        user_id=None,
                        action='login_failed_maintenance',
                        details={'username': username, 'role': user.role if user else 'unknown'},
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        success=False,
                        error_message='Login blocked during maintenance'
                    )
                    flash('System is currently under maintenance. Please try again later.', 'warning')
                    return redirect(url_for('auth.login'))
        
        # Show maintenance page for non-tech users
        total_duration = (maintenance.end_time - maintenance.start_time).total_seconds()
        elapsed = (datetime.now() - maintenance.start_time).total_seconds()
        progress_percentage = min(100, max(0, int((elapsed / total_duration) * 100)))
        
        return render_template('maintenance.html', 
                             maintenance=maintenance, 
                             progress_percentage=progress_percentage)
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if username and password are provided
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Convert remember to boolean
            remember = bool(request.form.get('remember'))
            login_user(user, remember=remember)
            
            # Log successful login
            log_activity(
                user_id=user.id,
                action='login',
                details={'role': user.role, 'remember': remember},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            flash('Logged in successfully.', 'success')
            return redirect(url_for('auth.dashboard'))
        else:
            # Log failed login attempt
            log_activity(
                user_id=None,
                action='login_failed',
                details={'username': username},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=False,
                error_message='Invalid credentials'
            )
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@auth_blueprint.route('/logout')
@login_required
def logout():
    # Log logout activity
    log_activity(
        user_id=current_user.id,
        action='logout',
        details={'role': current_user.role},
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_blueprint.route('/')
@auth_blueprint.route('/home')
def home():
    return render_template('home.html')

@auth_blueprint.route('/dashboard')
@login_required
def dashboard():
    """Redirects user to the appropriate dashboard based on their role."""
    flash(f"Redirecting user with role: {current_user.role}", "info")
    if current_user.role == 'Student':
        return redirect(url_for('student.student_dashboard'))
    elif current_user.role in TEACHER_ROLES:
        return redirect(url_for('teacher.teacher_dashboard'))
    elif current_user.role in ['School Administrator', 'Director']:
        return redirect(url_for('management.management_dashboard'))
    elif current_user.role == 'Tech':
        return redirect(url_for('tech.tech_dashboard'))
    else:
        # Fallback for unknown roles
        return render_template('home.html')


@auth_blueprint.route('/submit-bug-report', methods=['POST'])
@login_required
def submit_bug_report():
    """Submit a bug report from any user."""
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        severity = request.form.get('severity', 'medium')
        page_url = request.form.get('page_url', '')
        
        # Validate required fields
        if not title:
            return jsonify({'success': False, 'message': 'Please provide a title for the bug report.'})
        
        if not description:
            return jsonify({'success': False, 'message': 'Please provide a description of the bug.'})
        
        # Validate severity
        if severity not in ['low', 'medium', 'high', 'critical']:
            severity = 'medium'
        
        # Create bug report
        bug_report = BugReport()
        bug_report.user_id = current_user.id
        bug_report.title = title
        bug_report.description = description
        bug_report.contact_email = contact_email if contact_email else None
        bug_report.severity = severity
        bug_report.browser_info = request.headers.get('User-Agent', '')
        bug_report.ip_address = request.remote_addr
        bug_report.page_url = page_url
        
        db.session.add(bug_report)
        db.session.commit()
        
        # Log the bug report submission
        log_activity(
            current_user.id,
            'bug_report_submitted',
            {
                'bug_report_id': bug_report.id,
                'title': title,
                'severity': severity
            },
            request.remote_addr,
            request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True, 
            'message': 'Bug report submitted successfully. Thank you for helping us improve the system!'
        })
        
    except Exception as e:
        db.session.rollback()
        log_activity(
            current_user.id,
            'bug_report_failed',
            {'error': str(e)},
            request.remote_addr,
            request.headers.get('User-Agent'),
            False,
            str(e)
        )
        return jsonify({'success': False, 'message': 'An error occurred while submitting the bug report. Please try again.'})


@auth_blueprint.route('/bug-reports')
@login_required
def view_bug_reports():
    """View bug reports (Tech users only)."""
    if current_user.role != 'Tech':
        flash('Access denied. Only technical staff can view bug reports.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    # Get all bug reports, ordered by creation date (newest first)
    bug_reports = BugReport.query.order_by(BugReport.created_at.desc()).all()
    
    return render_template('bug_reports.html', bug_reports=bug_reports)
