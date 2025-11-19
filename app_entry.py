#!/usr/bin/env python3
"""
Unified entry point for the Clara Science Academy application.
Handles both development (run.py) and production (wsgi.py) scenarios.
"""

import os
import sys

try:
    from app import create_app
    from config import DevelopmentConfig
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're in the correct directory and all dependencies are installed.")
    print("Try running: pip install -r requirements.txt")
    sys.exit(1)

try:
    # Create the application instance
    # Explicitly use DevelopmentConfig for local development to ensure DEBUG=True
    print("🚀 Creating Flask application...")
    app = create_app(config_class=DevelopmentConfig)
    print("✅ Application created successfully!")
except Exception as e:
    print(f"❌ Error creating application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# WSGI application object for production servers (Gunicorn, etc.)
application = app

if __name__ == '__main__':
    try:
        # Development mode - run with Flask's built-in server
        print("🌐 Starting Flask development server...")
        print("📍 Server will be available at: http://127.0.0.1:5000")
        print("🛑 Press CTRL+C to stop the server\n")
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error running server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)