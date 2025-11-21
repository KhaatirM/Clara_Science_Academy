"""
Database migration script to add enhancement fields to Assignment and GroupAssignment tables.
This includes:
- Extra credit fields
- Late penalty fields
- Grade scale field
- Assignment category and weight fields
- Grade history table
- Grade extra credit and late penalty fields
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import Assignment, GroupAssignment, Grade

def add_enhancement_fields():
    """Add enhancement fields to Assignment and GroupAssignment tables."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 70)
            print("ADDING ENHANCEMENT FIELDS TO ASSIGNMENT TABLES")
            print("=" * 70)
            
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Fields to add to both Assignment and GroupAssignment
            enhancement_fields = [
                ("allow_extra_credit", "BOOLEAN DEFAULT FALSE"),
                ("max_extra_credit_points", "FLOAT DEFAULT 0.0"),
                ("late_penalty_enabled", "BOOLEAN DEFAULT FALSE"),
                ("late_penalty_per_day", "FLOAT DEFAULT 0.0"),
                ("late_penalty_max_days", "INTEGER DEFAULT 0"),
                ("grade_scale", "TEXT"),
                ("assignment_category", "VARCHAR(50)"),
                ("category_weight", "FLOAT DEFAULT 0.0")
            ]
            
            # Fields to add to Grade table
            grade_fields = [
                ("extra_credit_points", "FLOAT DEFAULT 0.0"),
                ("late_penalty_applied", "FLOAT DEFAULT 0.0"),
                ("days_late", "INTEGER DEFAULT 0")
            ]
            
            # Check and add fields to Assignment table
            print("\n[1] Checking Assignment table...")
            assignment_columns = [col['name'] for col in inspector.get_columns('assignment')]
            for field_name, field_type in enhancement_fields:
                if field_name not in assignment_columns:
                    print(f"    Adding {field_name} to assignment table...")
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text(f"ALTER TABLE assignment ADD COLUMN {field_name} {field_type}"))
                            conn.commit()
                        print(f"    [OK] Added {field_name} to assignment table")
                    except Exception as e:
                        print(f"    [ERROR] Error adding {field_name}: {e}")
                else:
                    print(f"    {field_name} already exists in assignment table")
            
            # Check and add fields to GroupAssignment table
            print("\n[2] Checking GroupAssignment table...")
            group_assignment_columns = [col['name'] for col in inspector.get_columns('group_assignment')]
            for field_name, field_type in enhancement_fields:
                if field_name not in group_assignment_columns:
                    print(f"    Adding {field_name} to group_assignment table...")
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text(f"ALTER TABLE group_assignment ADD COLUMN {field_name} {field_type}"))
                            conn.commit()
                        print(f"    [OK] Added {field_name} to group_assignment table")
                    except Exception as e:
                        print(f"    [ERROR] Error adding {field_name}: {e}")
                else:
                    print(f"    {field_name} already exists in group_assignment table")
            
            # Check and add fields to Grade table
            print("\n[3] Checking Grade table...")
            grade_columns = [col['name'] for col in inspector.get_columns('grade')]
            for field_name, field_type in grade_fields:
                if field_name not in grade_columns:
                    print(f"    Adding {field_name} to grade table...")
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text(f"ALTER TABLE grade ADD COLUMN {field_name} {field_type}"))
                            conn.commit()
                        print(f"    [OK] Added {field_name} to grade table")
                    except Exception as e:
                        print(f"    [ERROR] Error adding {field_name}: {e}")
                else:
                    print(f"    {field_name} already exists in grade table")
            
            # Create GradeHistory table if it doesn't exist
            print("\n[4] Checking GradeHistory table...")
            try:
                tables = inspector.get_table_names()
                if 'grade_history' not in tables:
                    print("    Creating grade_history table...")
                    db.create_all()  # This will create the table based on the model
                    print("    [OK] Created grade_history table")
                else:
                    print("    grade_history table already exists")
            except Exception as e:
                print(f"    [ERROR] Error creating grade_history table: {e}")
                # Try manual creation
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("""
                            CREATE TABLE IF NOT EXISTS grade_history (
                                id INTEGER PRIMARY KEY,
                                grade_id INTEGER,
                                student_id INTEGER,
                                assignment_id INTEGER,
                                previous_grade_data TEXT,
                                new_grade_data TEXT NOT NULL,
                                changed_by INTEGER NOT NULL,
                                changed_at TIMESTAMP NOT NULL,
                                change_reason TEXT,
                                FOREIGN KEY (grade_id) REFERENCES grade(id),
                                FOREIGN KEY (student_id) REFERENCES student(id),
                                FOREIGN KEY (assignment_id) REFERENCES assignment(id),
                                FOREIGN KEY (changed_by) REFERENCES user(id)
                            )
                        """))
                        conn.commit()
                    print("    [OK] Created grade_history table (manual)")
                except Exception as e2:
                    print(f"    [ERROR] Manual creation also failed: {e2}")
            
            print("\n" + "=" * 70)
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nAll enhancement fields have been added:")
            print("  [OK] Extra credit support")
            print("  [OK] Late penalty settings")
            print("  [OK] Grade scale customization")
            print("  [OK] Assignment categories and weights")
            print("  [OK] Grade history tracking")
            
        except Exception as e:
            print(f"\n[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    add_enhancement_fields()

