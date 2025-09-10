# Import the factory function from our new app.py
from app import create_app

# Create the application instance
app = create_app()

# This is the WSGI application object that Gunicorn will use
application = app

if __name__ == '__main__':
    # Run the application
    # The debug setting is controlled from config.py for security
    app.run(debug=app.config.get('DEBUG', False))
