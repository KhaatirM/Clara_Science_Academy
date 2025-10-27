#!/usr/bin/env python3
"""
Migration script to add team_type to cleaning_team and inspection_type to cleaning_inspection tables
This allows storing different types of teams and inspections (cleaning, lunch duty, experiment duty, etc.)
"""

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def add_team_and_inspection_types():
    """Add team_type and inspection_type columns"""
    with app.app_context():
        try:
            print("="*70)
            print("ADDING TEAM_TYPE AND INSPECTION_TYPE COLUMNS")
            print("="*70)
            
            # Check if columns already exist
            result1 = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='cleaning_team' 
                AND column_name='team_type'
            """))
            
            result2 = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='cleaning_inspection' 
                AND column_name='inspection_type'
            """))
            
            if result1.fetchone() and result2.fetchone():
                print("✓ Columns already exist. Skipping migration.")
                return
            
            # Add team_type column if it doesn't exist
            if not result1.fetchone():
                print("\n[1] Adding team_type column to cleaning_team table...")
                db.session.execute(text("""
                    ALTER TABLE cleaning_team 
                    ADD COLUMN team_type VARCHAR(50) DEFAULT 'cleaning'
                """))
                print("✓ Successfully added team_type column")
            
            # Add inspection_type column if it doesn't exist
            if not result2.fetchone():
                print("\n[2] Adding inspection_type column to cleaning_inspection table...")
                db.session.execute(text("""
                    ALTER TABLE cleaning_inspection 
                    ADD COLUMN inspection_type VARCHAR(50) DEFAULT 'cleaning'
                """))
                print("✓ Successfully added inspection_type column")
            
            db.session.commit()
            
            print("\n" + "="*70)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("="*70)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error during migration: {e}")
            print("Please check the database connection and permissions.")
            raise

if __name__ == "__main__":
    add_team_and_inspection_types()

