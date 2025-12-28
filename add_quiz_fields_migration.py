"""
Migration script to add quiz-related fields to the Assignment table.

This script adds the following columns:
- time_limit_minutes (Integer, nullable)
- max_attempts (Integer, default=1)
- shuffle_questions (Boolean, default=False)
- show_correct_answers (Boolean, default=True)
- google_form_id (String(255), nullable)
- google_form_url (String(500), nullable)
- google_form_linked (Boolean, default=False)

Run this script to update your database schema.
"""

import os
import sys
from sqlalchemy import text, inspect

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def migrate_database():
    """Add quiz-related columns to the Assignment table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get database connection
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('assignment')]
            
            print("Checking Assignment table columns...")
            print(f"   Current columns: {len(columns)}")
            
            # List of columns to add with their SQL definitions
            columns_to_add = [
                {
                    'name': 'time_limit_minutes',
                    'sql': 'ALTER TABLE assignment ADD COLUMN time_limit_minutes INTEGER',
                    'check': 'time_limit_minutes' not in columns
                },
                {
                    'name': 'max_attempts',
                    'sql': 'ALTER TABLE assignment ADD COLUMN max_attempts INTEGER DEFAULT 1 NOT NULL',
                    'check': 'max_attempts' not in columns
                },
                {
                    'name': 'shuffle_questions',
                    'sql': 'ALTER TABLE assignment ADD COLUMN shuffle_questions BOOLEAN DEFAULT 0 NOT NULL',
                    'check': 'shuffle_questions' not in columns
                },
                {
                    'name': 'show_correct_answers',
                    'sql': 'ALTER TABLE assignment ADD COLUMN show_correct_answers BOOLEAN DEFAULT 1 NOT NULL',
                    'check': 'show_correct_answers' not in columns
                },
                {
                    'name': 'google_form_id',
                    'sql': 'ALTER TABLE assignment ADD COLUMN google_form_id VARCHAR(255)',
                    'check': 'google_form_id' not in columns
                },
                {
                    'name': 'google_form_url',
                    'sql': 'ALTER TABLE assignment ADD COLUMN google_form_url VARCHAR(500)',
                    'check': 'google_form_url' not in columns
                },
                {
                    'name': 'google_form_linked',
                    'sql': 'ALTER TABLE assignment ADD COLUMN google_form_linked BOOLEAN DEFAULT 0 NOT NULL',
                    'check': 'google_form_linked' not in columns
                }
            ]
            
            # Track what we're adding
            columns_added = []
            
            # Add each column if it doesn't exist
            for col_info in columns_to_add:
                if col_info['check']:
                    try:
                        print(f"   [+] Adding column: {col_info['name']}...")
                        db.session.execute(text(col_info['sql']))
                        db.session.commit()
                        columns_added.append(col_info['name'])
                        print(f"   [OK] Successfully added: {col_info['name']}")
                    except Exception as e:
                        db.session.rollback()
                        # Check if column already exists (some databases give different errors)
                        if 'duplicate' in str(e).lower() or 'already exists' in str(e).lower():
                            print(f"   [WARN] Column {col_info['name']} already exists, skipping...")
                        else:
                            print(f"   [ERROR] Error adding {col_info['name']}: {e}")
                            raise
                else:
                    print(f"   [SKIP] Column {col_info['name']} already exists, skipping...")
            
            if columns_added:
                print(f"\n[SUCCESS] Migration completed successfully!")
                print(f"   Added {len(columns_added)} column(s): {', '.join(columns_added)}")
            else:
                print(f"\n[SUCCESS] All columns already exist. Database is up to date!")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Quiz Fields Migration Script")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] Migration completed successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("[ERROR] Migration failed. Please check the error messages above.")
        print("=" * 60)
        sys.exit(1)

