#!/usr/bin/env python3
"""
Check for missing columns in SQLite database.
"""

from app import create_app
from extensions import db
from sqlalchemy import inspect, text

def check_missing_columns():
    """Check for missing columns in key tables."""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("=" * 70)
        print("CHECKING FOR MISSING COLUMNS")
        print("=" * 70)
        
        # Check Enrollment table
        print("\n[1] Checking Enrollment table...")
        try:
            enrollment_columns = [col['name'] for col in inspector.get_columns('enrollment')]
            print(f"    Columns: {', '.join(enrollment_columns)}")
            
            if 'enrolled_at' not in enrollment_columns:
                print("    [WARNING] 'enrolled_at' column is missing!")
                print("    Adding 'enrolled_at' column...")
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE enrollment ADD COLUMN enrolled_at TIMESTAMP"))
                        conn.commit()
                    print("    [OK] Added 'enrolled_at' column")
                except Exception as e:
                    print(f"    [ERROR] Failed to add column: {e}")
            else:
                print("    [OK] 'enrolled_at' column exists")
        except Exception as e:
            print(f"    [ERROR] Error checking Enrollment table: {e}")
        
        # Check Grade table for graded_at
        print("\n[2] Checking Grade table...")
        try:
            grade_columns = [col['name'] for col in inspector.get_columns('grade')]
            print(f"    Columns: {', '.join(grade_columns)}")
            
            if 'graded_at' not in grade_columns:
                print("    [WARNING] 'graded_at' column is missing!")
                print("    Adding 'graded_at' column...")
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE grade ADD COLUMN graded_at TIMESTAMP"))
                        conn.commit()
                    print("    [OK] Added 'graded_at' column")
                except Exception as e:
                    print(f"    [ERROR] Failed to add column: {e}")
            else:
                print("    [OK] 'graded_at' column exists")
        except Exception as e:
            print(f"    [ERROR] Error checking Grade table: {e}")
        
        print("\n" + "=" * 70)
        print("CHECK COMPLETED!")
        print("=" * 70)

if __name__ == '__main__':
    check_missing_columns()

