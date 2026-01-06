"""
Migration script to create the extension_request table.
Run this script to update your database schema.
"""

import os
import sys
from sqlalchemy import text, inspect

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db

def create_extension_request_table():
    """Create extension_request table if it doesn't exist."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if table already exists
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'extension_request' in tables:
                print("[INFO] extension_request table already exists")
                return True
            
            print("[INFO] Creating extension_request table...")
            
            # Create the table
            db.session.execute(text("""
                CREATE TABLE extension_request (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assignment_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    requested_due_date DATETIME NOT NULL,
                    reason TEXT,
                    status VARCHAR(20) DEFAULT 'Pending' NOT NULL,
                    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    reviewed_at DATETIME,
                    reviewed_by INTEGER,
                    review_notes TEXT,
                    FOREIGN KEY (assignment_id) REFERENCES assignment(id),
                    FOREIGN KEY (student_id) REFERENCES student(id),
                    FOREIGN KEY (reviewed_by) REFERENCES teacher_staff(id)
                )
            """))
            db.session.commit()
            
            print("[OK] extension_request table created successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error creating table: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Extension Request Table Migration")
    print("=" * 60)
    print()
    
    success = create_extension_request_table()
    
    if success:
        print("\n[SUCCESS] Migration completed successfully!")
        print("\nNext steps:")
        print("  - The extension_request table is now available")
        print("  - Students can now request extensions")
        print("  - Teachers can view and manage extension requests")
    else:
        print("\n[ERROR] Migration failed. Please check the error messages above.")
        exit(1)





