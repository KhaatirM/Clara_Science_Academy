"""
Migration script to add Google Classroom integration fields.
Adds google_refresh_token to User table and google_classroom_id to Class table.

Usage:
    python migrations_scripts/add_google_classroom_fields.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text

def add_google_classroom_fields():
    """Add google_refresh_token to User and google_classroom_id to Class"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if _google_refresh_token column exists in user table (SQLite compatible)
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt FROM pragma_table_info('user') 
                WHERE name='_google_refresh_token';
            """))
            refresh_token_exists = result.scalar() > 0
            
            if not refresh_token_exists:
                print("Adding _google_refresh_token column to user table...")
                db.session.execute(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN _google_refresh_token VARCHAR(512);
                """))
                print("[OK] Successfully added _google_refresh_token column to user table")
            else:
                print("[OK] _google_refresh_token column already exists in user table")
            
            # Check if google_classroom_id column exists in class table (SQLite compatible)
            result = db.session.execute(text("""
                SELECT COUNT(*) as cnt FROM pragma_table_info('class') 
                WHERE name='google_classroom_id';
            """))
            classroom_id_exists = result.scalar() > 0
            
            if not classroom_id_exists:
                print("Adding google_classroom_id column to class table...")
                db.session.execute(text("""
                    ALTER TABLE class 
                    ADD COLUMN google_classroom_id VARCHAR(100);
                """))
                print("[OK] Successfully added google_classroom_id column to class table")
            else:
                print("[OK] google_classroom_id column already exists in class table")
            
            # Note: SQLite doesn't support adding UNIQUE constraint to existing column
            # The unique constraint will be enforced at the application level
            
            db.session.commit()
            print("\n[OK] Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Error during migration: {e}")
            raise


if __name__ == '__main__':
    add_google_classroom_fields()

