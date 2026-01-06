"""
Migration script to add open_date and close_date columns to the assignment table.
Run this script to update your database schema.
"""

import os
import sys
from sqlalchemy import text, inspect

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db

def add_assignment_open_close_dates():
    """Add open_date and close_date columns to assignment table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('assignment')]
            
            print("[INFO] Checking assignment table columns...")
            print(f"[INFO] Existing columns: {', '.join(columns)}")
            
            columns_added = []
            
            # Add open_date column if it doesn't exist
            if 'open_date' not in columns:
                print("[INFO] Adding open_date column...")
                db.session.execute(text("""
                    ALTER TABLE assignment 
                    ADD COLUMN open_date DATETIME
                """))
                db.session.commit()
                columns_added.append('open_date')
                print("[OK] open_date column added")
            else:
                print("[INFO] open_date column already exists")
            
            # Add close_date column if it doesn't exist
            if 'close_date' not in columns:
                print("[INFO] Adding close_date column...")
                db.session.execute(text("""
                    ALTER TABLE assignment 
                    ADD COLUMN close_date DATETIME
                """))
                db.session.commit()
                columns_added.append('close_date')
                print("[OK] close_date column added")
            else:
                print("[INFO] close_date column already exists")
            
            if columns_added:
                print(f"\n[SUCCESS] Migration completed successfully!")
                print(f"   Added {len(columns_added)} column(s): {', '.join(columns_added)}")
            else:
                print(f"\n[SUCCESS] All columns already exist. Database is up to date!")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error adding columns: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Assignment Open/Close Dates Migration")
    print("=" * 60)
    print()
    
    success = add_assignment_open_close_dates()
    
    if success:
        print("\n[SUCCESS] Migration completed successfully!")
        print("\nNext steps:")
        print("  - The open_date and close_date fields are now available")
        print("  - You can use them in assignment creation forms")
    else:
        print("\n[ERROR] Migration failed. Please check the error messages above.")
        exit(1)

