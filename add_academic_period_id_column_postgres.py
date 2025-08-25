#!/usr/bin/env python3
"""
Script to add the academic_period_id column to the existing assignment table.
This version is compatible with PostgreSQL (used on Render).
"""

from app import create_app, db
from sqlalchemy import text

def add_academic_period_id_column():
    """Add the academic_period_id column to the assignment table."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=== ADDING ACADEMIC_PERIOD_ID COLUMN TO ASSIGNMENT TABLE (PostgreSQL) ===\n")
            
            # Check if the academic_period_id column already exists
            # PostgreSQL version of checking column existence
            check_column_sql = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'assignment' 
                AND column_name = 'academic_period_id'
            """
            result = db.session.execute(text(check_column_sql))
            column_exists = result.fetchone() is not None
            
            if column_exists:
                print("✅ academic_period_id column already exists in assignment table")
                return
            
            print("📋 academic_period_id column not found. Adding it now...")
            
            # Add the academic_period_id column
            add_column_sql = "ALTER TABLE assignment ADD COLUMN academic_period_id INTEGER"
            db.session.execute(text(add_column_sql))
            
            # Add foreign key constraint
            add_fk_sql = """
                ALTER TABLE assignment 
                ADD CONSTRAINT fk_assignment_academic_period 
                FOREIGN KEY (academic_period_id) REFERENCES academic_period(id)
            """
            db.session.execute(text(add_fk_sql))
            
            db.session.commit()
            print("✅ Successfully added academic_period_id column and foreign key constraint")
            
            # Verify the column was added
            result = db.session.execute(text(check_column_sql))
            column_exists = result.fetchone() is not None
            
            if column_exists:
                print("✅ Column verification successful")
                
                # Show current table structure
                show_columns_sql = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'assignment'
                    ORDER BY ordinal_position
                """
                result = db.session.execute(text(show_columns_sql))
                columns = result.fetchall()
                
                print("📋 Current assignment table columns:")
                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    print(f"  - {col[0]} ({col[1]}) {nullable}")
            else:
                print("❌ Column verification failed")
            
        except Exception as e:
            print(f"❌ Error adding academic_period_id column: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == "__main__":
    add_academic_period_id_column()
