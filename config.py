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
    
    # Max file upload size (e.g., 16MB)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

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

