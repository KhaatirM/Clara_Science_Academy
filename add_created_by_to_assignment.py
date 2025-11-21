#!/usr/bin/env python3
"""
Migration script to add created_by column to assignment table.
"""

import sys
from sqlalchemy import text, inspect

def add_created_by_column():
    """Add created_by column to assignment table if it doesn't exist."""
    try:
        from app import create_app
        from extensions import db
        
        app = create_app()
        
        with app.app_context():
            print("=" * 70)
            print("ADDING created_by COLUMN TO ASSIGNMENT TABLE")
            print("=" * 70)
            
            # Check if column already exists
            inspector = inspect(db.engine)
            assignment_columns = [col['name'] for col in inspector.get_columns('assignment')]
            
            if 'created_by' in assignment_columns:
                print("\n[OK] created_by column already exists in assignment table")
                return
            
            print("\n[1] Adding created_by column to assignment table...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE assignment ADD COLUMN created_by INTEGER"))
                    conn.commit()
                print("    [OK] Added created_by column to assignment table")
            except Exception as e:
                print(f"    [ERROR] Error adding column: {e}")
                raise
            
            print("\n" + "=" * 70)
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    add_created_by_column()

