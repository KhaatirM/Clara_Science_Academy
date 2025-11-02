"""
Migration script to create the QuarterGrade table.
Run this after deploying to production.

Usage:
    python migrations_scripts/create_quarter_grade_table.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models import QuarterGrade
from sqlalchemy import text

def create_quarter_grade_table():
    """Create the quarter_grade table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if table already exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'quarter_grade'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("✓ quarter_grade table already exists")
                return
            
            print("Creating quarter_grade table...")
            
            # Create the table
            db.session.execute(text("""
                CREATE TABLE quarter_grade (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER NOT NULL REFERENCES student(id),
                    class_id INTEGER NOT NULL REFERENCES class(id),
                    school_year_id INTEGER NOT NULL REFERENCES school_year(id),
                    quarter VARCHAR(10) NOT NULL,
                    letter_grade VARCHAR(5),
                    percentage FLOAT,
                    assignments_count INTEGER DEFAULT 0,
                    last_calculated TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_student_class_quarter UNIQUE (student_id, class_id, school_year_id, quarter)
                );
            """))
            
            # Create indexes for better performance
            db.session.execute(text("""
                CREATE INDEX idx_quarter_grade_student ON quarter_grade(student_id);
                CREATE INDEX idx_quarter_grade_class ON quarter_grade(class_id);
                CREATE INDEX idx_quarter_grade_quarter ON quarter_grade(quarter);
                CREATE INDEX idx_quarter_grade_last_calc ON quarter_grade(last_calculated);
            """))
            
            db.session.commit()
            print("✓ Successfully created quarter_grade table with indexes")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating table: {e}")
            raise


if __name__ == '__main__':
    create_quarter_grade_table()

