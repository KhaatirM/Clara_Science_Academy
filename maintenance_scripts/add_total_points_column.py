"""
Database migration script to add total_points column to Assignment and GroupAssignment tables.
This script adds the total_points field with a default value of 100.0 for backward compatibility.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import Assignment, GroupAssignment

def add_total_points_column():
    """Add total_points column to Assignment and GroupAssignment tables."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 70)
            print("ADDING total_points COLUMN TO ASSIGNMENT TABLES")
            print("=" * 70)
            
            # Check if we're using SQLite (local) or PostgreSQL (production)
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Check Assignment table
            assignment_columns = [col['name'] for col in inspector.get_columns('assignment')]
            if 'total_points' not in assignment_columns:
                print("\n[1] Adding total_points column to assignment table...")
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE assignment ADD COLUMN total_points FLOAT DEFAULT 100.0"))
                        conn.commit()
                    print("    [OK] Added total_points column to assignment table")
                except Exception as e:
                    print(f"    [ERROR] Error adding column to assignment table: {e}")
                    # Try alternative syntax
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text("ALTER TABLE assignment ADD COLUMN total_points REAL DEFAULT 100.0"))
                            conn.commit()
                        print("    [OK] Added total_points column to assignment table (using REAL type)")
                    except Exception as e2:
                        print(f"    [ERROR] Alternative syntax also failed: {e2}")
                        raise
            else:
                print("\n[1] total_points column already exists in assignment table")
            
            # Check GroupAssignment table
            group_assignment_columns = [col['name'] for col in inspector.get_columns('group_assignment')]
            if 'total_points' not in group_assignment_columns:
                print("\n[2] Adding total_points column to group_assignment table...")
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE group_assignment ADD COLUMN total_points FLOAT DEFAULT 100.0"))
                        conn.commit()
                    print("    [OK] Added total_points column to group_assignment table")
                except Exception as e:
                    print(f"    [ERROR] Error adding column to group_assignment table: {e}")
                    # Try alternative syntax
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text("ALTER TABLE group_assignment ADD COLUMN total_points REAL DEFAULT 100.0"))
                            conn.commit()
                        print("    [OK] Added total_points column to group_assignment table (using REAL type)")
                    except Exception as e2:
                        print(f"    [ERROR] Alternative syntax also failed: {e2}")
                        raise
            else:
                print("\n[2] total_points column already exists in group_assignment table")
            
            # Update existing assignments to have total_points = 100.0 if NULL
            print("\n[3] Updating existing assignments with NULL total_points...")
            try:
                updated_assignments = db.session.execute(
                    text("UPDATE assignment SET total_points = 100.0 WHERE total_points IS NULL")
                )
                updated_group_assignments = db.session.execute(
                    text("UPDATE group_assignment SET total_points = 100.0 WHERE total_points IS NULL")
                )
                db.session.commit()
                print(f"    [OK] Updated {updated_assignments.rowcount} regular assignments")
                print(f"    [OK] Updated {updated_group_assignments.rowcount} group assignments")
            except Exception as e:
                print(f"    [ERROR] Error updating existing assignments: {e}")
                db.session.rollback()
            
            print("\n" + "=" * 70)
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nAll assignments now support customizable total points.")
            print("Default value is 100.0 for backward compatibility.")
            print("\nYou can now:")
            print("  - Set custom point values when creating assignments")
            print("  - Grade students using points instead of just percentages")
            print("  - See both points and percentage in the grading interface")
            
        except Exception as e:
            print(f"\n[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    add_total_points_column()

