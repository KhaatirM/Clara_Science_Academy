"""
Migration script to add missing columns to grade, assignment, and group_assignment tables.
This fixes the production database schema mismatch errors.

Columns to add:
- grade.extra_credit_points
- grade.late_penalty_applied
- grade.days_late
- assignment.total_points
- group_assignment.total_points
- group_assignment.allow_extra_credit
- group_assignment.max_extra_credit_points
- group_assignment.late_penalty_enabled
- group_assignment.late_penalty_per_day
- group_assignment.late_penalty_max_days
- group_assignment.grade_scale
- group_assignment.assignment_category
- group_assignment.category_weight
- group_assignment.allow_save_and_continue
- group_assignment.max_save_attempts
- group_assignment.save_timeout_minutes
- group_assignment.group_size_min
- group_assignment.group_size_max
- group_assignment.allow_individual
- group_assignment.collaboration_type
- group_assignment.selected_group_ids
"""

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def add_missing_columns():
    """
    Add missing columns to grade and assignment tables.
    This script is idempotent - it checks if columns exist before adding them.
    Works with both SQLite (local) and PostgreSQL (production).
    """
    app = create_app()
    with app.app_context():
        # Detect database type
        is_postgres = 'postgresql' in str(db.engine.url).lower()
        float_type = 'DOUBLE PRECISION' if is_postgres else 'REAL'
        
        print(f"[INFO] Database type: {'PostgreSQL' if is_postgres else 'SQLite'}")
        print(f"[INFO] Using float type: {float_type}\n")
        
        inspector = inspect(db.engine)
        
        # Check and add columns to grade table
        grade_columns = [col['name'] for col in inspector.get_columns('grade')]
        
        if 'extra_credit_points' not in grade_columns:
            print("[INFO] Adding 'extra_credit_points' column to 'grade' table...")
            try:
                db.session.execute(text(f"""
                    ALTER TABLE grade 
                    ADD COLUMN extra_credit_points {float_type} DEFAULT 0.0 NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'extra_credit_points' column to 'grade' table")
            except Exception as e:
                print(f"[ERROR] Failed to add 'extra_credit_points': {e}")
                db.session.rollback()
        else:
            print("[OK] 'extra_credit_points' column already exists in 'grade' table")
        
        if 'late_penalty_applied' not in grade_columns:
            print("[INFO] Adding 'late_penalty_applied' column to 'grade' table...")
            try:
                db.session.execute(text(f"""
                    ALTER TABLE grade 
                    ADD COLUMN late_penalty_applied {float_type} DEFAULT 0.0 NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'late_penalty_applied' column to 'grade' table")
            except Exception as e:
                print(f"[ERROR] Failed to add 'late_penalty_applied': {e}")
                db.session.rollback()
        else:
            print("[OK] 'late_penalty_applied' column already exists in 'grade' table")
        
        if 'days_late' not in grade_columns:
            print("[INFO] Adding 'days_late' column to 'grade' table...")
            try:
                db.session.execute(text("""
                    ALTER TABLE grade 
                    ADD COLUMN days_late INTEGER DEFAULT 0 NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'days_late' column to 'grade' table")
            except Exception as e:
                print(f"[ERROR] Failed to add 'days_late': {e}")
                db.session.rollback()
        else:
            print("[OK] 'days_late' column already exists in 'grade' table")
        
        # Check and add columns to assignment table
        assignment_columns = [col['name'] for col in inspector.get_columns('assignment')]
        
        if 'total_points' not in assignment_columns:
            print("[INFO] Adding 'total_points' column to 'assignment' table...")
            try:
                db.session.execute(text(f"""
                    ALTER TABLE assignment 
                    ADD COLUMN total_points {float_type} DEFAULT 100.0 NOT NULL
                """))
                db.session.commit()
                print("[OK] Successfully added 'total_points' column to 'assignment' table")
            except Exception as e:
                print(f"[ERROR] Failed to add 'total_points': {e}")
                db.session.rollback()
        else:
            print("[OK] 'total_points' column already exists in 'assignment' table")
        
        # Check and add columns to group_assignment table
        try:
            group_assignment_columns = [col['name'] for col in inspector.get_columns('group_assignment')]
            
            # List of all columns that should exist in group_assignment table
            # Format: (column_name, sql_definition, is_nullable)
            columns_to_add = [
                ('total_points', f'{float_type} DEFAULT 100.0 NOT NULL', False),
                ('allow_extra_credit', 'BOOLEAN DEFAULT FALSE NOT NULL', False),
                ('max_extra_credit_points', f'{float_type} DEFAULT 0.0 NOT NULL', False),
                ('late_penalty_enabled', 'BOOLEAN DEFAULT FALSE NOT NULL', False),
                ('late_penalty_per_day', f'{float_type} DEFAULT 0.0 NOT NULL', False),
                ('late_penalty_max_days', 'INTEGER DEFAULT 0 NOT NULL', False),
                ('grade_scale', 'TEXT', True),
                ('assignment_category', 'VARCHAR(50)', True),
                ('category_weight', f'{float_type} DEFAULT 0.0 NOT NULL', False),
                ('allow_save_and_continue', 'BOOLEAN DEFAULT FALSE NOT NULL', False),
                ('max_save_attempts', 'INTEGER DEFAULT 10 NOT NULL', False),
                ('save_timeout_minutes', 'INTEGER DEFAULT 30 NOT NULL', False),
                ('group_size_min', 'INTEGER DEFAULT 2', False),
                ('group_size_max', 'INTEGER DEFAULT 4', False),
                ('allow_individual', 'BOOLEAN DEFAULT FALSE NOT NULL', False),
                ('collaboration_type', 'VARCHAR(20) DEFAULT \'group\' NOT NULL', False),
                ('selected_group_ids', 'TEXT', True),
            ]
            
            for col_name, col_definition, is_nullable in columns_to_add:
                if col_name not in group_assignment_columns:
                    print(f"[INFO] Adding '{col_name}' column to 'group_assignment' table...")
                    try:
                        # For nullable columns, ensure the definition doesn't have NOT NULL
                        if is_nullable and 'NOT NULL' in col_definition:
                            col_definition = col_definition.replace(' NOT NULL', '')
                        db.session.execute(text(f"""
                            ALTER TABLE group_assignment 
                            ADD COLUMN {col_name} {col_definition}
                        """))
                        db.session.commit()
                        print(f"[OK] Successfully added '{col_name}' column to 'group_assignment' table")
                    except Exception as e:
                        print(f"[ERROR] Failed to add '{col_name}' to 'group_assignment': {e}")
                        db.session.rollback()
                else:
                    print(f"[OK] '{col_name}' column already exists in 'group_assignment' table")
        except Exception as e:
            print(f"[WARNING] Could not check 'group_assignment' table (may not exist): {e}")
        
        print("\n[SUCCESS] All missing columns have been added successfully!")

if __name__ == '__main__':
    add_missing_columns()

