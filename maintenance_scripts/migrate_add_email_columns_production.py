"""
Production-safe migration to add email and google_workspace_email columns to User table.
This script is designed to run on the live production database without downtime.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

def run_migration():
    """Add email columns to User table if they don't exist."""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set!")
        return False
    
    # Fix postgres:// to postgresql:// if needed
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"Connecting to database...")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Check current schema
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        print(f"Current User table columns: {columns}")
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Add email column if it doesn't exist
                if 'email' not in columns:
                    print("Adding 'email' column...")
                    conn.execute(text("""
                        ALTER TABLE "user" 
                        ADD COLUMN email VARCHAR(120) UNIQUE NULL
                    """))
                    print("✓ 'email' column added successfully")
                else:
                    print("✓ 'email' column already exists")
                
                # Add google_workspace_email column if it doesn't exist
                if 'google_workspace_email' not in columns:
                    print("Adding 'google_workspace_email' column...")
                    conn.execute(text("""
                        ALTER TABLE "user" 
                        ADD COLUMN google_workspace_email VARCHAR(120) UNIQUE NULL
                    """))
                    print("✓ 'google_workspace_email' column added successfully")
                else:
                    print("✓ 'google_workspace_email' column already exists")
                
                # Commit transaction
                trans.commit()
                print("\n✓ Migration completed successfully!")
                return True
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                print(f"\n✗ Error during migration: {e}")
                return False
                
    except SQLAlchemyError as e:
        print(f"\n✗ Database connection error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Production Database Migration")
    print("Adding email columns to User table")
    print("=" * 60)
    print()
    
    success = run_migration()
    
    if success:
        print("\n" + "=" * 60)
        print("MIGRATION SUCCESSFUL!")
        print("Next step: Restart your Render web service")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("MIGRATION FAILED!")
        print("Please check the errors above")
        print("=" * 60)
        sys.exit(1)
