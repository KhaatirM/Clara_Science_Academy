#!/usr/bin/env python3
"""
Migration script to add grade_levels column to Class table
This script can be run through the Flask application on Render
"""

from app import create_app, db
from sqlalchemy import text
import traceback

def add_grade_levels_column():
    """Add grade_levels column to the class table"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if the column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'class' AND column_name = 'grade_levels'
            """))
            
            if result.fetchone():
                print("✓ grade_levels column already exists in class table")
                return True
            
            # Add the grade_levels column
            db.session.execute(text("ALTER TABLE class ADD COLUMN grade_levels VARCHAR(100)"))
            db.session.commit()
            
            print("✓ Successfully added grade_levels column to class table")
            
            # Verify the column was added
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'class' AND column_name = 'grade_levels'
            """))
            
            column_info = result.fetchone()
            if column_info:
                print(f"✓ grade_levels column verified: {column_info}")
                return True
            else:
                print("✗ Failed to verify grade_levels column")
                return False
                
        except Exception as e:
            print(f"✗ Error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("Adding grade_levels column to Class table...")
    print("-" * 60)
    
    success = add_grade_levels_column()
    
    if success:
        print("-" * 60)
        print("✓ Migration completed successfully!")
        print("The grade_levels column has been added to the class table.")
        print("You can now uncomment the grade_levels field in models.py")
    else:
        print("-" * 60)
        print("✗ Migration failed!")
        print("Please check the error messages above.")
