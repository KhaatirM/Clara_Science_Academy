import os

# Try to import dotenv, but it's optional
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, we'll just use environment variables as-is
    def load_dotenv():
        pass
    load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key'
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    # Set to False until all forms/APIs use CSRF tokens; then set True and exempt only API/webhooks
    WTF_CSRF_CHECK_DEFAULT = False
    
    # Prioritize the production DATABASE_URL, with SQLite as a fallback.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'app.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads')
    
    # Debug mode - only enable in development environment
    # NEVER set DEBUG=True in production for security reasons
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')

    # PDFKit configuration
    WKHTMLTOPDF_PATH = os.environ.get('WKHTMLTOPDF_PATH') or '/usr/bin/wkhtmltopdf'
    
    # Max request body size (lower to avoid MemoryError on low-memory systems)
    # Use 4MB; increase if you need larger file uploads (e.g. 16 * 1024 * 1024)
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    
    # Google OAuth 2.0 Configuration
    # IMPORTANT: Set these environment variables in production
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    # Path to the client_secret.json file (downloaded from Google Cloud Console)
    # This file should NOT be committed to git - add to .gitignore
    GOOGLE_CLIENT_SECRETS_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'client_secret.json')
    # OAuth scopes for Google Sign-In and Classroom
    GOOGLE_OAUTH_SCOPES = [
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'
    ]
    
    # Encryption key for storing sensitive data like refresh tokens
    # IMPORTANT: Set this environment variable in production
    # Generate a key using: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

    # School timezone for login-based attendance (e.g. 'America/New_York'). Used to determine
    # 7–10 AM = Present, 10 AM–3 PM = Late. Default UTC if not set.
    SCHOOL_TIMEZONE = os.environ.get('SCHOOL_TIMEZONE') or 'UTC'

    # Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)


class ProductionConfig(Config):
    """Production configuration with enhanced security."""
    DEBUG = False  # Always False in production
    TESTING = False
    
    # Additional security settings for production
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent XSS attacks
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour session timeout


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database for tests

# Note: Google OAuth configuration has been moved into the Config class above
# To set up Google OAuth:
# 1. Download client_secret.json from Google Cloud Console
# 2. Place it in the project root directory
# 3. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables (optional, can use file)
# 4. Configure authorized redirect URIs in Google Cloud Console:
#    - http://127.0.0.1:5000/auth/google/callback (development)
#    - https://your-domain.com/auth/google/callback (production)