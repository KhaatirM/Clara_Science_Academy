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
    
    # Prioritize the production DATABASE_URL, with SQLite as a fallback.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'app.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads')
    DEBUG = False  # Always disable debug mode for production

    # PDFKit configuration
    WKHTMLTOPDF_PATH = os.environ.get('WKHTMLTOPDF_PATH') or '/usr/bin/wkhtmltopdf'
    
    # Max file upload size (e.g., 16MB)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

