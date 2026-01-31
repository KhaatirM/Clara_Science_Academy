"""
Migration script to add missing fields to group_assignment table.
This adds open_date and close_date fields to match the Assignment model.

Run this script once to update the database schema.
"""

import os
import sys

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def add_group_assignment_fields():
    """Add open_date and close_date fields to group_assignment table."""
    app = create_app()
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            
            # Check if group_assignment table exists
            if 'group_assignment' not in inspector.get_table_names():
                print("ERROR: group_assignment table does not exist!")
                return False
            
            # Get existing columns
            existing_columns = [col['name'] for col in inspector.get_columns('group_assignment')]
            print(f"Existing columns in group_assignment: {existing_columns}")
            
            # Check database type for correct SQL syntax
            db_url = str(db.engine.url)
            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
            
            columns_added = []
            
            # Add open_date column if it doesn't exist
            if 'open_date' not in existing_columns:
                print("Adding open_date column...")
                with db.engine.connect() as connection:
                    if is_postgres:
                        connection.execute(text("ALTER TABLE group_assignment ADD COLUMN open_date TIMESTAMP NULL"))
                    else:
                        connection.execute(text("ALTER TABLE group_assignment ADD COLUMN open_date DATETIME NULL"))
                    connection.commit()
                columns_added.append('open_date')
                print("[OK] Added open_date column")
            else:
                print("[OK] open_date column already exists")
            
            # Add close_date column if it doesn't exist
            if 'close_date' not in existing_columns:
                print("Adding close_date column...")
                with db.engine.connect() as connection:
                    if is_postgres:
                        connection.execute(text("ALTER TABLE group_assignment ADD COLUMN close_date TIMESTAMP NULL"))
                    else:
                        connection.execute(text("ALTER TABLE group_assignment ADD COLUMN close_date DATETIME NULL"))
                    connection.commit()
                columns_added.append('close_date')
                print("[OK] Added close_date column")
            else:
                print("[OK] close_date column already exists")
            
            if columns_added:
                print(f"\n[SUCCESS] Successfully added {len(columns_added)} column(s): {', '.join(columns_added)}")
            else:
                print("\n[SUCCESS] All columns already exist - no changes needed")
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Error adding columns: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Group Assignment Fields Migration Script")
    print("=" * 60)
    print("\nThis script will add the following fields to group_assignment:")
    print("  - open_date (TIMESTAMP/DATETIME)")
    print("  - close_date (TIMESTAMP/DATETIME)")
    print("\nThese fields match the Assignment model and allow:")
    print("  - Setting when an assignment becomes available")
    print("  - Setting when an assignment closes for submissions")
    print("\n" + "=" * 60)
    
    success = add_group_assignment_fields()
    
    if success:
        print("\n[SUCCESS] Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Migration failed!")
        sys.exit(1)
