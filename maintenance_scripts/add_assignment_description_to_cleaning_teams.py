#!/usr/bin/env python3
"""
Migration script to add assignment_description column to cleaning_team_member table
This allows storing detailed job assignments for each team member.
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

def add_assignment_description_column():
    """Add assignment_description column to cleaning_team_member table"""
    with app.app_context():
        try:
            print("="*70)
            print("ADDING ASSIGNMENT_DESCRIPTION COLUMN TO CLEANING_TEAM_MEMBER")
            print("="*70)
            
            # Get database engine
            engine = db.engine
            inspector = inspect(engine)
            
            # Check if column already exists
            columns = [col['name'] for col in inspector.get_columns('cleaning_team_member')]
            
            if 'assignment_description' in columns:
                print("[OK] Column 'assignment_description' already exists. Skipping migration.")
                return
            
            # Determine database type
            db_url = str(engine.url)
            is_sqlite = 'sqlite' in db_url.lower()
            
            # Add the column
            print("\n[1] Adding assignment_description column to cleaning_team_member table...")
            db.session.execute(text("""
                ALTER TABLE cleaning_team_member 
                ADD COLUMN assignment_description TEXT
            """))
            
            db.session.commit()
            print("[OK] Successfully added assignment_description column")
            
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
    add_assignment_description_column()

