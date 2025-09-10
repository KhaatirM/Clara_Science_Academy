#!/usr/bin/env python3
"""
WSGI entry point for the Clara Science Academy application.
This file is used by Gunicorn and other WSGI servers to run the application.
"""

from app import create_app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    app.run()
