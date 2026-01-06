#!/usr/bin/env python3
"""
Script to add the semester column to the existing assignment table.
"""

from app import create_app, db
from sqlalchemy import text

def add_semester_column():
    """Add the semester column to the assignment table."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== ADDING SEMESTER COLUMN TO ASSIGNMENT TABLE ===\n")
            
            # Check if the semester column already exists
            result = db.session.execute(text("PRAGMA table_info(assignment)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'semester' in columns:
                print("✅ Semester column already exists in assignment table")
                return
            
            # Add the semester column
            add_column_sql = "ALTER TABLE assignment ADD COLUMN semester VARCHAR(10)"
            db.session.execute(text(add_column_sql))
            db.session.commit()
            
            print("✅ Successfully added semester column to assignment table")
            
            # Verify the column was added
            result = db.session.execute(text("PRAGMA table_info(assignment)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'semester' in columns:
                print("✅ Column verification successful")
                print(f"📋 Current assignment table columns: {', '.join(columns)}")
            else:
                print("❌ Column verification failed")
            
        except Exception as e:
            print(f"❌ Error adding semester column: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    add_semester_column()
