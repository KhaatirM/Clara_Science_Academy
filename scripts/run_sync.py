import os
import sys

# Assuming your main application factory is importable from app.py
# You may need to adjust the Python path or import based on your exact app structure.
# If your app initialization is complex, you may need to wrap this in a helper function.
from app import create_app  # Import your app factory
from google_sync_tasks import sync_google_classroom_data
from models import User
from flask import current_app


def run_google_sync():
    """Initializes the Flask app context and runs the sync task for all connected teachers."""
    # Temporarily add the current directory to path if imports fail
    if '.' not in sys.path:
        sys.path.append('.') 
        
    # Initialize the Flask app (loads config, db, etc.)
    # Assuming create_app() does not require arguments or uses default config
    app = create_app() 
    
    with app.app_context():
        current_app.logger.info("Starting scheduled Google Classroom sync.")
        
        # Query for all teachers who have successfully stored a refresh token
        # We check the internal field directly since the property getter decrypts it
        teachers_to_sync = User.query.filter(
            User._google_refresh_token.isnot(None), 
            User.role == 'Teacher'
        ).all()
        
        if not teachers_to_sync:
            current_app.logger.info("No connected teachers found for sync.")
            return

        for teacher in teachers_to_sync:
            if teacher.teacher_staff_id:
                try:
                    current_app.logger.info(f"Syncing data for teacher: {teacher.username} (ID: {teacher.id})")
                    # Pass the User ID to the main sync function
                    sync_google_classroom_data(teacher.id)
                    current_app.logger.info(f"Successfully finished sync for teacher: {teacher.username}")
                except Exception as e:
                    current_app.logger.error(f"Error during sync for teacher {teacher.id}: {e}")


if __name__ == '__main__':
    run_google_sync()

