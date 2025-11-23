"""
Migration script to add missing columns to grade and assignment tables.
This fixes the production database schema mismatch errors.

Columns to add:
- grade.extra_credit_points
- grade.late_penalty_applied
- grade.days_late
- assignment.total_points
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
        
        print("\n[SUCCESS] All missing columns have been added successfully!")

if __name__ == '__main__':
    add_missing_columns()

