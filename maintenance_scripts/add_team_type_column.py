#!/usr/bin/env python3
"""
Migration script to add team_type column to cleaning_team table.
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

def add_team_type_column():
    """Add team_type column to cleaning_team table if it doesn't exist"""
    with app.app_context():
        try:
            print("="*70)
            print("ADDING TEAM_TYPE COLUMN TO CLEANING_TEAM TABLE")
            print("="*70)
            
            # Get database engine
            engine = db.engine
            inspector = inspect(engine)
            
            # Check if column already exists
            columns = [col['name'] for col in inspector.get_columns('cleaning_team')]
            
            if 'team_type' in columns:
                print("[OK] team_type column already exists. Skipping migration.")
                return
            
            # Determine database type
            db_url = str(engine.url)
            is_sqlite = 'sqlite' in db_url.lower()
            
            if is_sqlite:
                # SQLite: Use PRAGMA to check, then ALTER TABLE
                print("\n[1] Adding team_type column to cleaning_team table (SQLite)...")
                db.session.execute(text("""
                    ALTER TABLE cleaning_team 
                    ADD COLUMN team_type VARCHAR(50) DEFAULT 'cleaning'
                """))
            else:
                # PostgreSQL: Check first, then ALTER TABLE
                print("\n[1] Adding team_type column to cleaning_team table (PostgreSQL)...")
                # Check if column exists
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='cleaning_team' 
                    AND column_name='team_type'
                """))
                
                if not result.fetchone():
                    db.session.execute(text("""
                        ALTER TABLE cleaning_team 
                        ADD COLUMN team_type VARCHAR(50) DEFAULT 'cleaning'
                    """))
                else:
                    print("[OK] team_type column already exists.")
                    return
            
            db.session.commit()
            
            print("[OK] Successfully added team_type column")
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
    add_team_type_column()
