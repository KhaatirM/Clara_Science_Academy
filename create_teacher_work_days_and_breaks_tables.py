#!/usr/bin/env python3
"""
Script to create the teacher_work_days and school_breaks tables in the database.
These tables store teacher work days and school breaks for the academic calendar.
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import TeacherWorkDay, SchoolBreak

def create_teacher_work_days_and_breaks_tables():
    """Create the teacher_work_days and school_breaks tables."""
    app = create_app()
    
    with app.app_context():
        try:
            print("🚀 Creating teacher_work_days and school_breaks tables...")
            
            # Create the tables
            db.create_all()
            
            print("✅ Tables created successfully!")
            
            # Verify the tables exist
            from sqlalchemy import text
            
            # Check teacher_work_days table
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='teacher_work_days'"))
            if result.fetchone():
                print("✅ teacher_work_days table exists")
            else:
                print("❌ teacher_work_days table not found")
                return False
            
            # Check school_breaks table
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='school_breaks'"))
            if result.fetchone():
                print("✅ school_breaks table exists")
            else:
                print("❌ school_breaks table not found")
                return False
            
            # Show table structure
            print("\n📋 Table structure:")
            
            # teacher_work_days structure
            result = db.session.execute(text("PRAGMA table_info(teacher_work_days)"))
            columns = result.fetchall()
            print("\n🔧 teacher_work_days table columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULLABLE'}")
            
            # school_breaks structure
            result = db.session.execute(text("PRAGMA table_info(school_breaks)"))
            columns = result.fetchall()
            print("\n🔧 school_breaks table columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULLABLE'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("TEACHER WORK DAYS AND SCHOOL BREAKS TABLES CREATION")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = create_teacher_work_days_and_breaks_tables()
    
    print()
    if success:
        print("🎉 All tables created successfully!")
    else:
        print("💥 Failed to create tables. Please check the error messages above.")
    
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
