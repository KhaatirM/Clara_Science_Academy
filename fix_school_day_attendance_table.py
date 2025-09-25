#!/usr/bin/env python3
"""
Production-safe script to create the school_day_attendance table
This script can be run via the Render webservice shell
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import SchoolDayAttendance

def create_school_day_attendance_table():
    """Create the school_day_attendance table safely"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Creating school_day_attendance table...")
            
            # Check if table already exists
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'school_day_attendance' in existing_tables:
                print("✅ school_day_attendance table already exists!")
                return True
            
            # Create the table using raw SQL to ensure it matches the model
            create_table_sql = """
            CREATE TABLE school_day_attendance (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES student(id),
                date DATE NOT NULL,
                status VARCHAR(32) NOT NULL,
                notes TEXT,
                recorded_by INTEGER REFERENCES "user"(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX idx_school_day_attendance_student_date ON school_day_attendance(student_id, date);
            CREATE INDEX idx_school_day_attendance_date ON school_day_attendance(date);
            """
            
            # Execute the SQL
            db.session.execute(text(create_table_sql))
            db.session.commit()
            
            print("✅ school_day_attendance table created successfully!")
            
            # Verify the table was created
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'school_day_attendance' in tables:
                print("✅ Table verification successful!")
                
                # Show table structure
                columns = inspector.get_columns('school_day_attendance')
                print("\nTable structure:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
                    
                return True
            else:
                print("❌ Table verification failed!")
                return False
                
        except Exception as e:
            print(f"❌ Error creating school_day_attendance table: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("Starting school_day_attendance table creation...")
    success = create_school_day_attendance_table()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        sys.exit(1)
