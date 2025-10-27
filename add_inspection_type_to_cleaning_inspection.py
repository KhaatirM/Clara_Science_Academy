#!/usr/bin/env python3
"""
Migration script to add inspection_type column to cleaning_inspection table
This allows storing different types of inspections (cleaning, lunch duty, experiment duty, etc.)
"""

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

def add_inspection_type_column():
    """Add inspection_type column to cleaning_inspection table"""
    with app.app_context():
        try:
            print("="*70)
            print("ADDING INSPECTION_TYPE COLUMN TO CLEANING_INSPECTION")
            print("="*70)
            
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='cleaning_inspection' 
                AND column_name='inspection_type'
            """))
            
            if result.fetchone():
                print("✓ Column 'inspection_type' already exists. Skipping migration.")
                return
            
            # Add the column
            print("\n[1] Adding inspection_type column to cleaning_inspection table...")
            db.session.execute(text("""
                ALTER TABLE cleaning_inspection 
                ADD COLUMN inspection_type VARCHAR(50) DEFAULT 'cleaning'
            """))
            
            db.session.commit()
            print("✓ Successfully added inspection_type column")
            
            print("\n" + "="*70)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("="*70)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error during migration: {e}")
            print("Please check the database connection and permissions.")
            raise

if __name__ == "__main__":
    add_inspection_type_column()

