#!/usr/bin/env python3
"""
Unified entry point for the Clara Science Academy application.
Handles both development (run.py) and production (wsgi.py) scenarios.
"""

from app import create_app
from config import DevelopmentConfig  # Import DevelopmentConfig

# Create the application instance
# Explicitly use DevelopmentConfig for local development to ensure DEBUG=True
app = create_app(config_class=DevelopmentConfig)

# WSGI application object for production servers (Gunicorn, etc.)
application = app

if __name__ == '__main__':
    # Development mode - run with Flask's built-in server
    # The debug setting is now guaranteed to be True via DevelopmentConfig
    app.run(debug=app.config.get('DEBUG', True))

