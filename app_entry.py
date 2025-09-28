#!/usr/bin/env python3
"""
Unified entry point for the Clara Science Academy application.
Handles both development (run.py) and production (wsgi.py) scenarios.
"""

from app import create_app

# Create the application instance
app = create_app()

# WSGI application object for production servers (Gunicorn, etc.)
application = app

if __name__ == '__main__':
    # Development mode - run with Flask's built-in server
    # The debug setting is controlled from config.py for security
    app.run(debug=app.config.get('DEBUG', False))

