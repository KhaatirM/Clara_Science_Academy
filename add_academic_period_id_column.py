#!/usr/bin/env python3
"""
Script to add the academic_period_id column to the existing assignment table.
"""

from app import create_app, db
from sqlalchemy import text

def add_academic_period_id_column():
    """Add the academic_period_id column to the assignment table."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== ADDING ACADEMIC_PERIOD_ID COLUMN TO ASSIGNMENT TABLE ===\n")
            
            # Check if the academic_period_id column already exists
            result = db.session.execute(text("PRAGMA table_info(assignment)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'academic_period_id' in columns:
                print("✅ academic_period_id column already exists in assignment table")
                return
            
            # Add the academic_period_id column
            add_column_sql = "ALTER TABLE assignment ADD COLUMN academic_period_id INTEGER"
            db.session.execute(text(add_column_sql))
            db.session.commit()
            
            print("✅ Successfully added academic_period_id column to assignment table")
            
            # Verify the column was added
            result = db.session.execute(text("PRAGMA table_info(assignment)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'academic_period_id' in columns:
                print("✅ Column verification successful")
                print(f"📋 Current assignment table columns: {', '.join(columns)}")
            else:
                print("❌ Column verification failed")
            
        except Exception as e:
            print(f"❌ Error adding academic_period_id column: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    add_academic_period_id_column()
