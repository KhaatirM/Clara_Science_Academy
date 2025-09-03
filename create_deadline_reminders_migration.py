#!/usr/bin/env python3
"""
Migration script to create deadline reminder tables.
"""

from app import create_app, db
from models import DeadlineReminder, ReminderNotification

def create_deadline_reminder_tables():
    """Create deadline reminder tables."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create the tables
            DeadlineReminder.__table__.create(db.engine, checkfirst=True)
            ReminderNotification.__table__.create(db.engine, checkfirst=True)
            
            print("✅ Deadline reminder tables created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating deadline reminder tables: {e}")
            return False
    
    return True

if __name__ == "__main__":
    create_deadline_reminder_tables()

