#!/usr/bin/env python3
"""
Migration script to add team_type to cleaning_team and inspection_type to cleaning_inspection tables
This allows storing different types of teams and inspections (cleaning, lunch duty, experiment duty, etc.)
This works with both SQLite and PostgreSQL databases.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect

app = create_app()

def add_team_and_inspection_types():
    """Add team_type and inspection_type columns"""
    with app.app_context():
        try:
            print("="*70)
            print("ADDING TEAM_TYPE AND INSPECTION_TYPE COLUMNS")
            print("="*70)
            
            # Get database engine
            engine = db.engine
            inspector = inspect(engine)
            
            # Check if columns already exist
            team_columns = [col['name'] for col in inspector.get_columns('cleaning_team')]
            inspection_columns = [col['name'] for col in inspector.get_columns('cleaning_inspection')]
            
            has_team_type = 'team_type' in team_columns
            has_inspection_type = 'inspection_type' in inspection_columns
            
            if has_team_type and has_inspection_type:
                print("[OK] Columns already exist. Skipping migration.")
                return
            
            # Add team_type column if it doesn't exist
            if not has_team_type:
                print("\n[1] Adding team_type column to cleaning_team table...")
                db.session.execute(text("""
                    ALTER TABLE cleaning_team 
                    ADD COLUMN team_type VARCHAR(50) DEFAULT 'cleaning'
                """))
                print("[OK] Successfully added team_type column")
            
            # Add inspection_type column if it doesn't exist
            if not has_inspection_type:
                print("\n[2] Adding inspection_type column to cleaning_inspection table...")
                db.session.execute(text("""
                    ALTER TABLE cleaning_inspection 
                    ADD COLUMN inspection_type VARCHAR(50) DEFAULT 'cleaning'
                """))
                print("[OK] Successfully added inspection_type column")
            
            db.session.commit()
            
            print("\n" + "="*70)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("="*70)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Error during migration: {e}")
            print("Please check the database connection and permissions.")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    add_team_and_inspection_types()

