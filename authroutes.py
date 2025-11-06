# Standard library imports
from datetime import datetime
import os

# Core Flask imports
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFError

# Database and model imports
from models import User, TeacherStaff, db, MaintenanceMode, BugReport

# Authentication and decorators
from decorators import is_teacher_role

# Application imports
from app import log_activity

# Werkzeug utilities
from werkzeug.security import check_password_hash, generate_password_hash

# Google OAuth imports
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import pathlib

# SQLAlchemy imports for OR queries
from sqlalchemy import or_

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    
    # Check for maintenance mode - handle case where table might not exist
    maintenance = None
    try:
        maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
    except Exception as e:
        # Table might not exist yet, continue without maintenance mode
        pass
    
    if maintenance and maintenance.end_time > datetime.now():
        # Allow tech users to login during maintenance
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Check if username and password are provided
            if not username or not password:
                flash('Username and password are required.', 'danger')
                return render_template('shared/maintenance.html', 
                                     maintenance=maintenance, 
                                     progress_percentage=0)
            
            user = User.query.filter_by(username=username).first()
            if user and password and check_password_hash(user.password_hash, password):
                # Tech users can access during maintenance
                if user.role in ['Tech', 'IT Support'] and maintenance.allow_tech_access:
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
                        user_id=user.id if user else None,
                        action='login_failed_maintenance',
                        details={'username': username, 'role': user.role if user else 'unknown', 'reason': 'access_denied'},
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        success=False,
                        error_message='Access denied during maintenance'
                    )
                    flash('Access denied during maintenance. Only technical staff can login.', 'warning')
                    return redirect(url_for('auth.login'))
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
        
        return render_template('shared/maintenance.html', 
                             maintenance=maintenance, 
                             progress_percentage=progress_percentage)
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Debug: Print form data
            print(f"DEBUG: Received form data - username: '{username}', password: '{password}'")
            print(f"DEBUG: Form data dict: {dict(request.form)}")
            
            # Check if username and password are provided
            if not username or not password:
                print(f"DEBUG: Missing credentials - username: {bool(username)}, password: {bool(password)}")
                flash('Username and password are required.', 'danger')
                return render_template('shared/login.html')
            
            user = User.query.filter_by(username=username).first()
            print(f"DEBUG: User found: {user}")
            if user:
                print(f"DEBUG: User details - ID: {user.id}, Role: {user.role}, Password hash exists: {bool(user.password_hash)}")
            
            if user and check_password_hash(user.password_hash, password):
                # Convert remember to boolean
                remember = bool(request.form.get('remember'))
                login_user(user, remember=remember)
                
                # Increment login count
                user.login_count += 1
                db.session.commit()
                
                # Log successful login
                log_activity(
                    user_id=user.id,
                    action='login',
                    details={'role': user.role, 'remember': remember, 'login_count': user.login_count},
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                
                # Check if user has temporary password or is first-time login
                if user.is_temporary_password or user.login_count == 1:
                    flash('You are using a temporary password or this is your first login. Please change your password for security.', 'warning')
                    return redirect(url_for('auth.dashboard'))
                else:
                    flash('Logged in successfully.', 'success')
                    return redirect(url_for('auth.dashboard'))
            else:
                print(f"DEBUG: Login failed - User: {user}, Password check: {user and check_password_hash(user.password_hash, password) if user else 'No user found'}")
                # Log failed login attempt - invalid credentials
                log_activity(
                    user_id=None,
                    action='login_failed',
                    details={'username': username, 'reason': 'invalid_credentials'},
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    success=False,
                    error_message='Invalid credentials'
                )
                flash('Invalid username or password.', 'danger')
        except CSRFError:
            flash('Invalid request. Please try again.', 'danger')
            return render_template('shared/login.html')
            
    return render_template('shared/login.html')

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
    return render_template('shared/home.html')

@auth_blueprint.route('/dashboard')
@login_required
def dashboard():
    """Redirects user to the appropriate dashboard based on their role."""
    flash(f"Redirecting user with role: {current_user.role}", "info")
    if current_user.role == 'Student':
        return redirect(url_for('student.student_dashboard'))
    elif is_teacher_role(current_user.role):
        return redirect(url_for('teacher.teacher_dashboard'))
    elif current_user.role in ['School Administrator', 'Director']:
        return redirect(url_for('management.management_dashboard'))
    elif current_user.role in ['Tech', 'IT Support']:
        return redirect(url_for('tech.tech_dashboard'))
    else:
        # Fallback for unknown roles
        return render_template('shared/home.html')


@auth_blueprint.route('/change-password-popup', methods=['POST'])
@login_required
def change_password_popup():
    """Handle password change from popup modal."""
    try:
        print(f"DEBUG: Password change popup request received from user: {current_user.username}")
        print(f"DEBUG: Request form data: {dict(request.form)}")
        print(f"DEBUG: Before change - is_temporary_password: {current_user.is_temporary_password}, login_count: {current_user.login_count}")
        
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate passwords
        if not new_password or not confirm_password:
            return jsonify({'success': False, 'message': 'Both password fields are required.'})
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'Passwords do not match.'})
        
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters long.'})
        
        # Check password strength
        has_upper = any(c.isupper() for c in new_password)
        has_lower = any(c.islower() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        
        if not (has_upper and has_lower and has_digit):
            return jsonify({'success': False, 'message': 'Password must contain at least one uppercase letter, one lowercase letter, and one number.'})
        
        # Update user password
        current_user.password_hash = generate_password_hash(new_password)
        current_user.is_temporary_password = False
        current_user.password_changed_at = datetime.utcnow()
        
        # If this was a first-time login (login_count == 1), increment it to prevent popup from showing again
        if current_user.login_count == 1:
            current_user.login_count = 2
        
        db.session.commit()
        
        print(f"DEBUG: After change - is_temporary_password: {current_user.is_temporary_password}, login_count: {current_user.login_count}")
        
        # Log password change
        log_activity(
            user_id=current_user.id,
            action='password_changed_popup',
            details={'role': current_user.role, 'login_count': current_user.login_count},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Get user ID for display
        user_id = ''
        if current_user.role == 'Student' and current_user.student_id:
            from models import Student
            student = Student.query.get(current_user.student_id)
            if student:
                user_id = student.student_id
        elif current_user.teacher_staff_id:
            teacher_staff = TeacherStaff.query.get(current_user.teacher_staff_id)
            if teacher_staff:
                user_id = teacher_staff.staff_id
        
        return jsonify({
            'success': True,
            'username': current_user.username,
            'password': new_password,  # Return the new password for display
            'user_id': user_id
        })
        
    except Exception as e:
        print(f"Error in change_password_popup: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while changing password.'})

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
        
    except CSRFError:
        return jsonify({'success': False, 'message': 'Invalid request. Please try again.'})
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
def bug_reports():
    """Bug reports page - all users can submit, tech users can view all reports."""
    # Get bug reports based on user role
    if current_user.role in ['Tech', 'IT Support']:
        # Tech users can see all bug reports
        bug_reports = BugReport.query.order_by(BugReport.created_at.desc()).all()
        can_manage = True
    else:
        # Other users can only see their own bug reports
        bug_reports = BugReport.query.filter_by(user_id=current_user.id).order_by(BugReport.created_at.desc()).all()
        can_manage = False
    
    return render_template('tech/bug_reports.html', 
                         bug_reports=bug_reports, 
                         can_manage=can_manage,
                         current_user=current_user)


@auth_blueprint.route('/bug-reports/<int:report_id>/update-status', methods=['POST'])
@login_required
def update_bug_report_status(report_id):
    """Update bug report status (Tech users only)."""
    if current_user.role not in ['Tech', 'IT Support']:
        return jsonify({'success': False, 'message': 'Access denied. Only technical staff can update bug report status.'})
    
    try:
        bug_report = BugReport.query.get_or_404(report_id)
        new_status = request.form.get('status', '').strip()
        
        if new_status not in ['open', 'in_progress', 'resolved', 'closed']:
            return jsonify({'success': False, 'message': 'Invalid status.'})
        
        bug_report.status = new_status
        db.session.commit()
        
        # Log the status update
        log_activity(
            current_user.id,
            'bug_report_status_updated',
            {
                'bug_report_id': report_id,
                'new_status': new_status,
                'title': bug_report.title
            },
            request.remote_addr,
            request.headers.get('User-Agent')
        )
        
        return jsonify({'success': True, 'message': f'Bug report status updated to {new_status.replace("_", " ")}.'})
        
    except CSRFError:
        return jsonify({'success': False, 'message': 'Invalid request. Please try again.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while updating the bug report status.'})

@auth_blueprint.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password for any authenticated user."""
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_new_password')
            
            # Validate input
            if not current_password or not new_password or not confirm_password:
                flash('All fields are required.', 'danger')
                return redirect(url_for('auth.change_password'))
            
            # Check if current password is correct
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('auth.change_password'))
            
            # Check if new password matches confirmation
            if new_password != confirm_password:
                flash('New password and confirmation do not match.', 'danger')
                return redirect(url_for('auth.change_password'))
            
            # Validate new password strength (minimum 8 characters)
            if len(new_password) < 8:
                flash('New password must be at least 8 characters long.', 'danger')
                return redirect(url_for('auth.change_password'))
            
            # Check if new password is different from current
            if check_password_hash(current_user.password_hash, new_password):
                flash('New password must be different from current password.', 'danger')
                return redirect(url_for('auth.change_password'))
            
            # Update password
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            # Log the password change
            log_activity(
                current_user.id,
                'password_changed',
                {'role': current_user.role},
                request.remote_addr,
                request.headers.get('User-Agent')
            )
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.dashboard'))
            
        except CSRFError:
            flash('Invalid request. Please try again.', 'danger')
            return redirect(url_for('auth.change_password'))
        except Exception as e:
            db.session.rollback()
            log_activity(
                current_user.id,
                'password_change_failed',
                {'error': str(e)},
                request.remote_addr,
                request.headers.get('User-Agent'),
                False,
                str(e)
            )
            flash('An error occurred while changing your password. Please try again.', 'danger')
            return redirect(url_for('auth.change_password'))
    
    # GET request - show password change form
    return render_template('shared/change_password.html')

@auth_blueprint.route('/change-password', methods=['POST'])
@login_required
def change_password_ajax():
    """Handle password change via AJAX for temporary password users."""
    try:
        data = request.get_json() if request.is_json else request.form
        
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        # Validate input
        if not current_password or not new_password or not confirm_password:
            return jsonify({
                'success': False,
                'message': 'All fields are required.'
            }), 400
        
        if new_password != confirm_password:
            return jsonify({
                'success': False,
                'message': 'New passwords do not match.'
            }), 400
        
        if len(new_password) < 8:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 8 characters long.'
            }), 400
        
        # Verify current password
        if not check_password_hash(current_user.password_hash, current_password):
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect.'
            }), 400
        
        # Check if user has temporary password (required for this route)
        if not current_user.is_temporary_password:
            return jsonify({
                'success': False,
                'message': 'This route is only for users with temporary passwords.'
            }), 403
        
        # Generate new password hash
        new_password_hash = generate_password_hash(new_password)
        
        # Update user password and clear temporary flag
        current_user.password_hash = new_password_hash
        current_user.is_temporary_password = False
        current_user.password_changed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log the password change
        log_activity(
            current_user.id,
            'password_changed_from_temporary',
            {'user_id': current_user.id, 'username': current_user.username},
            request.remote_addr,
            request.headers.get('User-Agent'),
            True,
            'Password changed from temporary password'
        )
        
        # Determine redirect URL based on user role
        if current_user.role in ['Director', 'School Administrator']:
            redirect_url = url_for('management.dashboard')
        elif current_user.role == 'Teacher':
            redirect_url = url_for('teacher.dashboard')
        elif current_user.role == 'Student':
            redirect_url = url_for('student.dashboard')
        else:
            redirect_url = url_for('auth.dashboard')
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully!',
            'redirect_url': redirect_url
        })
        
    except Exception as e:
        db.session.rollback()
        log_activity(
            current_user.id,
            'password_change_ajax_failed',
            {'error': str(e)},
            request.remote_addr,
            request.headers.get('User-Agent'),
            False,
            str(e)
        )
        return jsonify({
            'success': False,
            'message': 'An error occurred while changing your password. Please try again.'
        }), 500


# ==================== GOOGLE OAUTH 2.0 ROUTES ====================

# Disable HTTPS requirement for local development (ONLY FOR DEVELOPMENT)
# In production, remove this line - HTTPS is required
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def get_google_oauth_flow():
    """Create and return a Google OAuth Flow object."""
    import json
    import tempfile
    
    # Try to get client secret from environment variable first (for production)
    client_secret_json = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
    
    if client_secret_json:
        # Parse JSON from environment variable
        try:
            client_config = json.loads(client_secret_json)
            
            # Create flow from client config dictionary
            flow = Flow.from_client_config(
                client_config,
                scopes=current_app.config.get('GOOGLE_OAUTH_SCOPES'),
                redirect_uri=url_for('auth.google_callback', _external=True)
            )
            
            current_app.logger.info("Google OAuth flow created from environment variable")
            return flow
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Invalid JSON in GOOGLE_CLIENT_SECRET_JSON: {str(e)}")
            raise ValueError("Invalid Google OAuth configuration in environment variable")
    
    # Fallback to file-based configuration (for local development)
    client_secrets_file = current_app.config.get('GOOGLE_CLIENT_SECRETS_FILE')
    
    if not os.path.exists(client_secrets_file):
        current_app.logger.error(f"Google client_secret.json not found at {client_secrets_file}")
        raise FileNotFoundError(
            "Google OAuth configuration file (client_secret.json) not found. "
            "Please download it from Google Cloud Console and place it in the project root, "
            "or set the GOOGLE_CLIENT_SECRET_JSON environment variable."
        )
    
    flow = Flow.from_client_secrets_file(
        client_secrets_file,
        scopes=current_app.config.get('GOOGLE_OAUTH_SCOPES'),
        redirect_uri=url_for('auth.google_callback', _external=True)
    )
    
    current_app.logger.info("Google OAuth flow created from client_secret.json file")
    return flow


@auth_blueprint.route('/google-login')
def google_login():
    """Initiate Google OAuth login flow."""
    try:
        # Check for maintenance mode
        maintenance = None
        try:
            maintenance = MaintenanceMode.query.filter_by(is_active=True).first()
        except:
            pass
        
        if maintenance and maintenance.end_time > datetime.now():
            flash('System is currently under maintenance. Please try again later.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Create OAuth flow
        flow = get_google_oauth_flow()
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            # Enable offline access so you can refresh an access token without re-prompting the user
            access_type='offline',
            # Enable incremental authorization
            include_granted_scopes='true',
            # Force account selection (optional - uncomment if you want users to always choose account)
            # prompt='select_account'
        )
        
        # Store the state in session to verify in callback
        session['oauth_state'] = state
        
        # Log the Google login initiation
        log_activity(
            user_id=None,
            action='google_login_initiated',
            details={'redirect_uri': url_for('auth.google_callback', _external=True)},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return redirect(authorization_url)
        
    except FileNotFoundError as e:
        current_app.logger.error(f"Google OAuth config error: {str(e)}")
        flash('Google Sign-In is not configured. Please contact your administrator.', 'danger')
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Error initiating Google login: {str(e)}")
        log_activity(
            user_id=None,
            action='google_login_failed',
            details={'error': str(e)},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=False,
            error_message=str(e)
        )
        flash('An error occurred while connecting to Google. Please try again or use your password.', 'danger')
        return redirect(url_for('auth.login'))


@auth_blueprint.route('/auth/google/callback')
def google_callback():
    """Handle the Google OAuth callback."""
    try:
        import json
        
        # Verify state to prevent CSRF attacks
        state = session.get('oauth_state')
        if not state:
            flash('Invalid login session. Please try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Try to get client secret from environment variable first (for production)
        client_secret_json = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
        
        if client_secret_json:
            # Parse JSON from environment variable
            try:
                client_config = json.loads(client_secret_json)
                
                # Create OAuth flow with the stored state from config
                flow = Flow.from_client_config(
                    client_config,
                    scopes=None,  # Don't need to specify scopes for callback
                    state=state,
                    redirect_uri=url_for('auth.google_callback', _external=True)
                )
            except json.JSONDecodeError as e:
                current_app.logger.error(f"Invalid JSON in GOOGLE_CLIENT_SECRET_JSON: {str(e)}")
                flash('Google Sign-In configuration error. Please contact your administrator.', 'danger')
                return redirect(url_for('auth.login'))
        else:
            # Fallback to file-based configuration
            flow = Flow.from_client_secrets_file(
                current_app.config.get('GOOGLE_CLIENT_SECRETS_FILE'),
                scopes=None,  # Don't need to specify scopes for callback
                state=state,
                redirect_uri=url_for('auth.google_callback', _external=True)
            )
        
        # Fetch the token using the authorization response
        flow.fetch_token(authorization_response=request.url)
        
        # Get user credentials
        credentials = flow.credentials
        
        # Verify the token and get user info
        request_session = google_requests.Request()
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request_session,
            current_app.config.get('GOOGLE_CLIENT_ID')
        )
        
        # Extract user information
        google_email = id_info.get('email')
        google_name = id_info.get('name')
        google_given_name = id_info.get('given_name')
        google_family_name = id_info.get('family_name')
        google_picture = id_info.get('picture')
        
        current_app.logger.info(f"Google OAuth successful for email: {google_email}")
        
        # Check if user exists in the database (check both personal email and Google Workspace email)
        user = User.query.filter(
            or_(
                User.email == google_email,  # Check personal email
                User.google_workspace_email == google_email  # Check Google Workspace email
            )
        ).first()
        
        if user:
            # User exists - log them in
            login_user(user, remember=True)
            
            # Increment login count
            user.login_count += 1
            db.session.commit()
            
            # Log successful Google login
            log_activity(
                user_id=user.id,
                action='google_login_success',
                details={
                    'email': google_email,
                    'role': user.role,
                    'login_count': user.login_count,
                    'google_name': google_name
                },
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            flash(f'Welcome back, {user.first_name or google_given_name}! Logged in successfully with Google.', 'success')
            
            # Clear the OAuth state from session
            session.pop('oauth_state', None)
            
            return redirect(url_for('auth.dashboard'))
        else:
            # User does not exist in the system
            current_app.logger.warning(f"Google login attempted with unregistered email: {google_email}")
            
            # Log failed Google login attempt
            log_activity(
                user_id=None,
                action='google_login_failed',
                details={
                    'email': google_email,
                    'reason': 'email_not_registered',
                    'google_name': google_name
                },
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=False,
                error_message='Email not registered in system'
            )
            
            flash(
                'Your Google Account is not associated with an account at Clara Science Academy. '
                'Please log in with your username and password, or contact an administrator to link your Google account.',
                'warning'
            )
            
            # Clear the OAuth state from session
            session.pop('oauth_state', None)
            
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        current_app.logger.error(f"Error in Google OAuth callback: {str(e)}")
        
        # Log the error
        log_activity(
            user_id=None,
            action='google_callback_error',
            details={'error': str(e), 'url': request.url},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=False,
            error_message=str(e)
        )
        
        flash(
            'An error occurred while signing in with Google. Please try again or use your password to login.',
            'danger'
        )
        
        # Clear the OAuth state from session
        session.pop('oauth_state', None)
        
        return redirect(url_for('auth.login'))
