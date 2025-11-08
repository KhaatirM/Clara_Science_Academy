"""
Settings and utilities routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin
from models import db, User
from google_auth_oauthlib.flow import Flow

bp = Blueprint('settings', __name__)

@bp.route('/settings')
@login_required
@teacher_required
def settings():
    """Teacher settings page."""
    # Check if teacher has connected their Google account
    user = User.query.get(current_user.id)
    google_connected = user.google_refresh_token is not None
    return render_template('teacher_settings.html', google_connected=google_connected)


@bp.route('/google-account/connect')
@login_required
@teacher_required
def google_connect_account():
    """
    Route 1: Starts the OAuth flow for getting a REFRESH token.
    """
    try:
        flow = Flow.from_client_secrets_file(
            current_app.config.get('GOOGLE_CLIENT_SECRETS_FILE', 'client_secret.json'),
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid',
                'https://www.googleapis.com/auth/classroom.courses',
                'https://www.googleapis.com/auth/classroom.rosters'
            ],
            redirect_uri=url_for('teacher.settings.google_connect_callback', _external=True)
        )
        
        # 'access_type=offline' is what gives us the refresh_token
        # 'prompt=consent' forces Google to show the consent screen
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
        
        session['oauth_state'] = state
        return redirect(authorization_url)
    except Exception as e:
        current_app.logger.error(f"Error starting Google OAuth flow: {e}")
        flash(f"An error occurred while connecting to Google: {e}", "danger")
        return redirect(url_for('teacher.settings.settings'))


@bp.route('/google-account/callback')
@login_required
@teacher_required
def google_connect_callback():
    """
    Route 2: Google redirects here. We grab the refresh token and save it.
    """
    if 'oauth_state' not in session or session['oauth_state'] != request.args.get('state'):
        flash('State mismatch. Please try linking again.', 'danger')
        return redirect(url_for('teacher.settings.settings'))

    try:
        flow = Flow.from_client_secrets_file(
            current_app.config.get('GOOGLE_CLIENT_SECRETS_FILE', 'client_secret.json'),
            scopes=None,
            state=session.pop('oauth_state'),
            redirect_uri=url_for('teacher.settings.google_connect_callback', _external=True)
        )
        
        flow.fetch_token(authorization_response=request.url)
        
        # This is the magic token!
        refresh_token = flow.credentials.refresh_token

        if not refresh_token:
            flash("Failed to get a refresh token. Please ensure you are fully granting permission.", "warning")
            return redirect(url_for('teacher.settings.settings'))
        
        # Securely save the encrypted token to the logged-in user
        user = User.query.get(current_user.id)
        user.google_refresh_token = refresh_token
        db.session.commit()

        flash("Your Google Account has been securely connected!", "success")

    except Exception as e:
        current_app.logger.error(f"Error in Google connect callback: {e}")
        flash(f"An error occurred: {e}", "danger")

    return redirect(url_for('teacher.settings.settings'))


@bp.route('/google-account/disconnect', methods=['POST'])
@login_required
@teacher_required
def google_disconnect_account():
    """
    Disconnect the teacher's Google account by removing the refresh token.
    """
    try:
        user = User.query.get(current_user.id)
        user.google_refresh_token = None
        db.session.commit()
        flash("Your Google Account has been disconnected.", "info")
    except Exception as e:
        current_app.logger.error(f"Error disconnecting Google account: {e}")
        flash(f"An error occurred while disconnecting: {e}", "danger")
    
    return redirect(url_for('teacher.settings.settings'))

# Placeholder for settings-related routes
# This module will contain all settings functionality
# from the original teacherroutes.py file

