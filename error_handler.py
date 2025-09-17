"""
Error handling and bug reporting system for Clara Science App.
Automatically captures errors and sends bug reports to tech staff.
"""

import traceback
import json
import sys
from datetime import datetime
from flask import request, current_app, g
from flask_login import current_user
from models import db, BugReport, TeacherStaff, Notification
from app import create_notification
import logging

# Configure logging for error tracking
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def get_client_info():
    """Extract client information from the request."""
    try:
        user_agent = request.headers.get('User-Agent', 'Unknown')
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
        
        # Extract browser info
        browser_info = {
            'user_agent': user_agent,
            'accept_language': request.headers.get('Accept-Language', 'Unknown'),
            'accept_encoding': request.headers.get('Accept-Encoding', 'Unknown'),
            'connection': request.headers.get('Connection', 'Unknown')
        }
        
        return {
            'user_agent': user_agent,
            'ip_address': ip_address,
            'browser_info': json.dumps(browser_info)
        }
    except Exception:
        return {
            'user_agent': 'Unknown',
            'ip_address': 'Unknown',
            'browser_info': '{}'
        }

def get_request_data():
    """Safely extract request data for bug reports."""
    try:
        data = {}
        
        # Get form data (excluding sensitive fields)
        sensitive_fields = ['password', 'password_hash', 'csrf_token', 'secret']
        if request.form:
            for key, value in request.form.items():
                if key.lower() not in sensitive_fields:
                    data[f'form_{key}'] = str(value)[:500]  # Limit length
        
        # Get JSON data
        if request.is_json:
            try:
                json_data = request.get_json()
                if json_data:
                    # Filter out sensitive data
                    filtered_json = {k: v for k, v in json_data.items() 
                                   if k.lower() not in sensitive_fields}
                    data['json_data'] = str(filtered_json)[:1000]
            except Exception:
                pass
        
        # Get query parameters
        if request.args:
            data['query_params'] = dict(request.args)
        
        return json.dumps(data) if data else None
    except Exception:
        return None

def determine_error_severity(error_type, error_message):
    """Determine the severity level of an error."""
    critical_keywords = ['database', 'connection', 'timeout', 'memory', 'disk']
    high_keywords = ['permission', 'authorization', 'authentication', 'validation']
    medium_keywords = ['not found', 'missing', 'invalid']
    
    error_text = f"{error_type} {error_message}".lower()
    
    if any(keyword in error_text for keyword in critical_keywords):
        return 'critical'
    elif any(keyword in error_text for keyword in high_keywords):
        return 'high'
    elif any(keyword in error_text for keyword in medium_keywords):
        return 'medium'
    else:
        return 'low'

def create_bug_report(error_type, error_message, error_traceback=None, severity=None):
    """Create a bug report and send notification to tech staff."""
    try:
        # Get client information
        client_info = get_client_info()
        
        # Determine severity if not provided
        if not severity:
            severity = determine_error_severity(error_type, error_message)
        
        # Get user information
        user_id = current_user.id if current_user.is_authenticated else None
        user_role = current_user.role if current_user.is_authenticated else None
        
        # Create bug report
        bug_report = BugReport(
            error_type=error_type,
            error_message=error_message,
            error_traceback=error_traceback,
            user_id=user_id,
            user_role=user_role,
            url=request.url if request else None,
            method=request.method if request else None,
            user_agent=client_info['user_agent'],
            ip_address=client_info['ip_address'],
            request_data=get_request_data(),
            browser_info=client_info['browser_info'],
            severity=severity
        )
        
        db.session.add(bug_report)
        db.session.commit()
        
        # Send notification to tech staff
        send_tech_notification(bug_report)
        
        # Log the error
        logger.error(f"Bug Report #{bug_report.id}: {error_type} - {error_message}")
        
        return bug_report
        
    except Exception as e:
        # If we can't create a bug report, at least log it
        logger.error(f"Failed to create bug report: {e}")
        return None

def send_tech_notification(bug_report):
    """Send notification to tech staff about new bug reports."""
    try:
        # Get all tech staff (users with role 'Tech' or 'Director')
        tech_staff = TeacherStaff.query.join(TeacherStaff.user).filter(
            User.role.in_(['Tech', 'Director'])
        ).all()
        
        if not tech_staff:
            # Fallback: get any staff member
            tech_staff = TeacherStaff.query.join(TeacherStaff.user).filter(
                User.role.in_(['School Administrator', 'Director'])
            ).all()
        
        for staff in tech_staff:
            if staff.user:
                create_notification(
                    user_id=staff.user.id,
                    notification_type='bug_report',
                    title=f'New Bug Report - {bug_report.severity.upper()}',
                    message=f'Error: {bug_report.error_message[:100]}... (Report #{bug_report.id})',
                    link=f'/tech/bug-reports/{bug_report.id}'
                )
                
    except Exception as e:
        logger.error(f"Failed to send tech notification: {e}")

def handle_server_error(error):
    """Handle 500 server errors."""
    error_type = 'server_error'
    error_message = str(error)
    error_traceback = traceback.format_exc()
    
    bug_report = create_bug_report(error_type, error_message, error_traceback, 'high')
    
    # Log the error
    logger.error(f"Server Error: {error_message}")
    logger.error(f"Traceback: {error_traceback}")
    
    return bug_report

def handle_client_error(error):
    """Handle 400 client errors."""
    error_type = 'client_error'
    error_message = str(error)
    
    bug_report = create_bug_report(error_type, error_message, severity='medium')
    
    return bug_report

def handle_validation_error(error):
    """Handle validation errors."""
    error_type = 'validation_error'
    error_message = str(error)
    
    bug_report = create_bug_report(error_type, error_message, severity='low')
    
    return bug_report

def handle_database_error(error):
    """Handle database errors."""
    error_type = 'database_error'
    error_message = str(error)
    error_traceback = traceback.format_exc()
    
    bug_report = create_bug_report(error_type, error_message, error_traceback, 'critical')
    
    return bug_report

def log_application_error(error, context=None):
    """Log application errors with context."""
    try:
        error_type = 'application_error'
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        # Add context to error message
        if context:
            error_message = f"{error_message} | Context: {context}"
        
        bug_report = create_bug_report(error_type, error_message, error_traceback, 'medium')
        
        return bug_report
    except Exception as e:
        logger.error(f"Failed to log application error: {e}")
        return None

def error_handler_decorator(error_type='application_error', severity='medium'):
    """Decorator to automatically handle errors in routes."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create bug report
                create_bug_report(
                    error_type=error_type,
                    error_message=str(e),
                    error_traceback=traceback.format_exc(),
                    severity=severity
                )
                
                # Re-raise the exception to maintain normal error handling
                raise
        return wrapper
    return decorator

def capture_frontend_error(error_data):
    """Capture frontend JavaScript errors."""
    try:
        error_type = 'client_error'
        error_message = error_data.get('message', 'Unknown frontend error')
        error_traceback = error_data.get('stack', 'No stack trace available')
        
        # Add additional context
        context = {
            'url': error_data.get('url', 'Unknown'),
            'line': error_data.get('line', 'Unknown'),
            'column': error_data.get('column', 'Unknown'),
            'filename': error_data.get('filename', 'Unknown')
        }
        
        error_message = f"{error_message} | File: {context['filename']}:{context['line']}:{context['column']}"
        
        bug_report = create_bug_report(error_type, error_message, error_traceback, 'low')
        
        return bug_report
    except Exception as e:
        logger.error(f"Failed to capture frontend error: {e}")
        return None
