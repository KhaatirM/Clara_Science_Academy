#!/usr/bin/env python3
"""
Migration script to add google_workspace_email column to user table.
"""

import sys
from sqlalchemy import text, inspect

def add_google_workspace_email_column():
    """Add google_workspace_email column to user table if it doesn't exist."""
    try:
        from app import create_app
        from extensions import db
        
        app = create_app()
        
        with app.app_context():
            print("=" * 70)
            print("ADDING google_workspace_email COLUMN TO USER TABLE")
            print("=" * 70)
            
            # Check if column already exists
            inspector = inspect(db.engine)
            user_columns = [col['name'] for col in inspector.get_columns('user')]
            
            if 'google_workspace_email' in user_columns:
                print("\n[OK] google_workspace_email column already exists in user table")
                return
            
            print("\n[1] Adding google_workspace_email column to user table...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN google_workspace_email VARCHAR(120)"))
                    conn.commit()
                print("    [OK] Added google_workspace_email column to user table")
            except Exception as e:
                print(f"    [ERROR] Error adding column: {e}")
                raise
            
            print("\n" + "=" * 70)
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nThe google_workspace_email column has been added to the user table.")
            
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    add_google_workspace_email_column()

