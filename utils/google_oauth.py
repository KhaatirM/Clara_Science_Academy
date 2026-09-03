"""Google OAuth helpers for Sign-In and Settings → Connect.

Connect must use the same redirect URI as Sign in with Google
(``/auth/google/callback``). Google Cloud Console allows that path; it does
not allow ``/management/google-account/callback`` or the teacher equivalent,
which caused Error 400 redirect_uri_mismatch.
"""

from __future__ import annotations

import json
import os

from flask import current_app, flash, redirect, session, url_for
from flask_login import current_user

GOOGLE_CONNECT_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid',
    'https://www.googleapis.com/auth/classroom.courses',
    'https://www.googleapis.com/auth/classroom.rosters',
    'https://www.googleapis.com/auth/forms.responses.readonly',
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/drive',
]


def google_oauth_redirect_uri() -> str:
    """Authorized callback — must match Google Cloud Console and Sign-In."""
    return url_for('auth.google_callback', _external=True)


def google_oauth_client_config() -> dict:
    raw = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError('Invalid GOOGLE_CLIENT_SECRET_JSON') from exc
        if isinstance(parsed, dict) and parsed.get('web', {}).get('client_id'):
            return parsed

    client_id = current_app.config.get('GOOGLE_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET') or os.environ.get(
        'GOOGLE_CLIENT_SECRET'
    )
    if not client_id or not client_secret:
        raise ValueError('Google OAuth is not configured on this server.')

    redirect_uri = google_oauth_redirect_uri()
    return {
        'web': {
            'client_id': client_id,
            'client_secret': client_secret,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
            'redirect_uris': [redirect_uri],
        }
    }


def begin_google_connect(*, next_url: str | None, fallback_url: str):
    """Start the Drive/Classroom consent flow; Google returns to Sign-In callback."""
    from google_auth_oauthlib.flow import Flow
    from services.google_drive_service import safe_google_oauth_next

    try:
        redirect_uri = google_oauth_redirect_uri()
        current_app.logger.info('Google connect redirect_uri=%s', redirect_uri)
        flow = Flow.from_client_config(
            google_oauth_client_config(),
            scopes=GOOGLE_CONNECT_SCOPES,
            redirect_uri=redirect_uri,
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
        )
        session['oauth_state'] = state
        session['google_oauth_mode'] = 'connect'
        session['google_oauth_fallback'] = fallback_url
        if hasattr(flow, 'code_verifier') and flow.code_verifier:
            session['oauth_code_verifier'] = flow.code_verifier
        safe_next = safe_google_oauth_next(next_url)
        if safe_next:
            session['google_oauth_next'] = safe_next
        else:
            session.pop('google_oauth_next', None)
        return redirect(authorization_url)
    except ValueError as exc:
        current_app.logger.error('Google connect config error: %s', exc)
        flash(str(exc), 'warning')
        return redirect(fallback_url)
    except Exception as exc:
        current_app.logger.error('Error starting Google OAuth flow: %s', exc)
        flash(f'An error occurred while connecting to Google: {exc}', 'danger')
        return redirect(fallback_url)


def finish_google_connect(credentials):
    """Save the refresh token on the signed-in portal user after Google returns."""
    from extensions import db
    from models import User
    from services.google_drive_service import safe_google_oauth_next

    session.pop('google_oauth_mode', None)
    session.pop('oauth_state', None)
    session.pop('oauth_code_verifier', None)

    next_url = safe_google_oauth_next(session.pop('google_oauth_next', None))
    fallback = session.pop('google_oauth_fallback', None) or '/app/management/settings'
    done = next_url or fallback

    if not current_user.is_authenticated:
        flash('Sign in to the portal first, then connect Google from Settings.', 'warning')
        return redirect(url_for('auth.login'))

    refresh_token = getattr(credentials, 'refresh_token', None)
    if not refresh_token:
        flash(
            'Google did not return a lasting connection. Click Reconnect and approve every '
            'permission, including Drive.',
            'warning',
        )
        return redirect(done)

    user = User.query.get(current_user.id)
    user.google_refresh_token = refresh_token
    db.session.commit()
    flash('Your Google Account has been securely connected!', 'success')
    current_app.logger.info('Saved Google refresh token for user %s', user.id)
    return redirect(done)
