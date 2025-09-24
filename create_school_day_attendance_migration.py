#!/usr/bin/env python3
"""
Migration script to create the school_day_attendance table
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db

def create_school_day_attendance_table():
    """Create the school_day_attendance table"""
    with app.app_context():
        try:
            # Create the table
            db.create_all()
            
            # Check if the table was created successfully
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'school_day_attendance' in tables:
                print("✅ School Day Attendance table created successfully!")
                
                # Show table structure
                columns = inspector.get_columns('school_day_attendance')
                print("\nTable structure:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
                    
            else:
                print("❌ Failed to create School Day Attendance table")
                
        except Exception as e:
            print(f"❌ Error creating School Day Attendance table: {e}")
            return False
            
    return True

if __name__ == '__main__':
    print("Creating School Day Attendance table...")
    create_school_day_attendance_table()
