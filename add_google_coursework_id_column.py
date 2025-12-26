"""
Database migration script to add google_coursework_id column to Assignment table.
This fixes the SQL error: "no such column: assignment.google_coursework_id"
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def add_google_coursework_id_column():
    """Add google_coursework_id column to Assignment table."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 70)
            print("ADDING google_coursework_id COLUMN TO ASSIGNMENT TABLE")
            print("=" * 70)
            
            inspector = inspect(db.engine)
            
            # Check if assignment table exists
            if 'assignment' not in inspector.get_table_names():
                print("[ERROR] Assignment table does not exist!")
                return False
            
            # Check Assignment table columns
            assignment_columns = [col['name'] for col in inspector.get_columns('assignment')]
            
            if 'google_coursework_id' not in assignment_columns:
                print("\n[1] Adding google_coursework_id column to assignment table...")
                try:
                    # Detect database type
                    is_postgres = 'postgresql' in str(db.engine.url).lower()
                    
                    if is_postgres:
                        # PostgreSQL syntax
                        db.session.execute(text("""
                            ALTER TABLE assignment 
                            ADD COLUMN google_coursework_id VARCHAR(100) UNIQUE
                        """))
                    else:
                        # SQLite syntax (UNIQUE constraint added separately)
                        db.session.execute(text("""
                            ALTER TABLE assignment 
                            ADD COLUMN google_coursework_id VARCHAR(100)
                        """))
                    
                    db.session.commit()
                    print("    [OK] Added google_coursework_id column to assignment table")
                    
                    # For SQLite, add unique constraint via index
                    if not is_postgres:
                        try:
                            # Create unique index for SQLite
                            db.session.execute(text("""
                                CREATE UNIQUE INDEX IF NOT EXISTS idx_assignment_google_coursework_id 
                                ON assignment(google_coursework_id) 
                                WHERE google_coursework_id IS NOT NULL
                            """))
                            db.session.commit()
                            print("    [OK] Added unique index on google_coursework_id column")
                        except Exception as e:
                            print(f"    [WARNING] Could not create unique index (may already exist): {e}")
                            db.session.rollback()
                    
                except Exception as e:
                    print(f"    [ERROR] Error adding column to assignment table: {e}")
                    db.session.rollback()
                    raise
            else:
                print("\n[1] google_coursework_id column already exists in assignment table")
            
            print("\n" + "=" * 70)
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nThe google_coursework_id column has been added to the assignment table.")
            print("This column is used to link assignments with Google Classroom coursework.")
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_google_coursework_id_column()
    sys.exit(0 if success else 1)

