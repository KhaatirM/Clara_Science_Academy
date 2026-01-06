#!/usr/bin/env python3
"""
Migration script to add created_by column to GroupAssignment table
"""
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from config import DevelopmentConfig
from sqlalchemy import text

def add_created_by_column():
    """Add created_by column to GroupAssignment table if it doesn't exist"""
    app = create_app(DevelopmentConfig)
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('group_assignment')]
            
            if 'created_by' in columns:
                print("[OK] Column 'created_by' already exists in group_assignment table")
                return
            
            # Add the column
            print("[INFO] Adding 'created_by' column to group_assignment table...")
            db.session.execute(text("""
                ALTER TABLE group_assignment 
                ADD COLUMN created_by INTEGER REFERENCES user(id)
            """))
            db.session.commit()
            print("[OK] Column 'created_by' added successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error adding column: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Add created_by to GroupAssignment")
    print("=" * 60)
    
    if add_created_by_column():
        print("\n[OK] Migration completed successfully!")
    else:
        print("\n[ERROR] Migration failed!")
        sys.exit(1)

