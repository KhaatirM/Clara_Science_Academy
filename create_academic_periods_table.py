#!/usr/bin/env python3
"""
Script to create the academic_periods table in the database.
"""

from app import create_app, db
from sqlalchemy import text

def create_academic_periods_table():
    """Create the academic_periods table."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== CREATING ACADEMIC PERIODS TABLE ===\n")
            
            # Create the academic_period table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS academic_period (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_year_id INTEGER NOT NULL,
                name VARCHAR(20) NOT NULL,
                period_type VARCHAR(10) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (school_year_id) REFERENCES school_year (id)
            )
            """
            
            db.session.execute(text(create_table_sql))
            db.session.commit()
            
            print("✅ Successfully created academic_period table")
            
            # Verify the table was created
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='academic_period'"))
            if result.fetchone():
                print("✅ Table verification successful")
            else:
                print("❌ Table verification failed")
            
        except Exception as e:
            print(f"❌ Error creating table: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    create_academic_periods_table()
