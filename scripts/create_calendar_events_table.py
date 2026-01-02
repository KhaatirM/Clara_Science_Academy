#!/usr/bin/env python3
"""
Script to create the calendar_events table in the database.
This table stores calendar events extracted from uploaded PDF calendars.
"""

import os
import sys
from sqlalchemy import text

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def create_calendar_events_table():
    """Create the calendar_events table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create the calendar_events table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_year_id INTEGER NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                name VARCHAR(100) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                description TEXT,
                pdf_filename VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (school_year_id) REFERENCES school_year (id)
            )
            """
            
            db.session.execute(text(create_table_sql))
            db.session.commit()
            
            print("✅ calendar_events table created successfully!")
            
            # Verify the table was created
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='calendar_events'"))
            if result.fetchone():
                print("✅ Table verification successful!")
                
                # Show table structure
                result = db.session.execute(text("PRAGMA table_info(calendar_events)"))
                columns = result.fetchall()
                print("\n📋 Table structure:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
            else:
                print("❌ Table verification failed!")
                
        except Exception as e:
            print(f"❌ Error creating table: {str(e)}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Creating calendar_events table...")
    success = create_calendar_events_table()
    
    if success:
        print("\n🎉 Database migration completed successfully!")
    else:
        print("\n💥 Database migration failed!")
        sys.exit(1)
