"""
Migration script to add temporary access fields to teacher_staff table.
Adds is_temporary and access_expires_at columns.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import create_app, db
from sqlalchemy import inspect, text

def add_temporary_access_fields():
    """Add is_temporary and access_expires_at columns to teacher_staff table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('teacher_staff')]
            
            if 'is_temporary' not in columns:
                print("[INFO] Adding is_temporary column to teacher_staff table...")
                db.session.execute(text("ALTER TABLE teacher_staff ADD COLUMN is_temporary BOOLEAN DEFAULT 0 NOT NULL"))
                db.session.commit()
                print("[SUCCESS] Added is_temporary column")
            else:
                print("[INFO] is_temporary column already exists")
            
            if 'access_expires_at' not in columns:
                print("[INFO] Adding access_expires_at column to teacher_staff table...")
                db.session.execute(text("ALTER TABLE teacher_staff ADD COLUMN access_expires_at DATETIME"))
                db.session.commit()
                print("[SUCCESS] Added access_expires_at column")
            else:
                print("[INFO] access_expires_at column already exists")
            
            print("[SUCCESS] Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Migration failed: {e}")
            sys.exit(1)

if __name__ == '__main__':
    add_temporary_access_fields()





