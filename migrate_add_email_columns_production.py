"""
Production-safe migration script to add email and google_workspace_email columns to User table.
This script is designed to run on Render or any production PostgreSQL database.

IMPORTANT: Run this script on your production server to fix the database schema.
"""

from app import app, db
from sqlalchemy import text, inspect

def add_email_columns_to_user_table():
    """Add email and google_workspace_email columns to User table if they don't exist."""
    
    with app.app_context():
        try:
            print("=" * 70)
            print("Production Database Migration: Add Email Columns to User Table")
            print("=" * 70)
            print()
            
            # Check current columns in user table
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            print(f"Current columns in 'user' table: {', '.join(columns)}")
            print()
            
            # Track what needs to be added
            columns_to_add = []
            
            # Check if 'email' column exists
            if 'email' not in columns:
                columns_to_add.append('email')
                print("⚠️  Column 'email' does NOT exist - will be added")
            else:
                print("✅ Column 'email' already exists")
            
            # Check if 'google_workspace_email' column exists
            if 'google_workspace_email' not in columns:
                columns_to_add.append('google_workspace_email')
                print("⚠️  Column 'google_workspace_email' does NOT exist - will be added")
            else:
                print("✅ Column 'google_workspace_email' already exists")
            
            print()
            
            # If no columns need to be added, we're done
            if not columns_to_add:
                print("=" * 70)
                print("✅ All required columns already exist. No migration needed!")
                print("=" * 70)
                return
            
            # Add missing columns
            print(f"Adding {len(columns_to_add)} column(s) to 'user' table...")
            print()
            
            with db.engine.connect() as conn:
                # Add email column if needed
                if 'email' in columns_to_add:
                    print("Adding 'email' column...")
                    conn.execute(text(
                        "ALTER TABLE \"user\" ADD COLUMN email VARCHAR(120) UNIQUE"
                    ))
                    conn.commit()
                    print("✅ Successfully added 'email' column")
                
                # Add google_workspace_email column if needed
                if 'google_workspace_email' in columns_to_add:
                    print("Adding 'google_workspace_email' column...")
                    conn.execute(text(
                        "ALTER TABLE \"user\" ADD COLUMN google_workspace_email VARCHAR(120) UNIQUE"
                    ))
                    conn.commit()
                    print("✅ Successfully added 'google_workspace_email' column")
            
            print()
            print("=" * 70)
            print("✅ Migration completed successfully!")
            print("=" * 70)
            print()
            print("Next steps:")
            print("1. Restart your application (it should restart automatically on Render)")
            print("2. Run 'python populate_google_workspace_emails.py' to populate emails")
            print("3. Test the application to ensure everything works")
            print()
            
        except Exception as e:
            print()
            print("=" * 70)
            print("❌ ERROR during migration:")
            print("=" * 70)
            print(f"{str(e)}")
            print()
            print("Troubleshooting:")
            print("1. Make sure you have database write permissions")
            print("2. Check that the database connection is working")
            print("3. Verify you're connected to the correct database")
            print("4. Try running the migration again")
            print()
            print("If the error persists, you can manually run these SQL commands:")
            print()
            if 'email' in columns_to_add:
                print('  ALTER TABLE "user" ADD COLUMN email VARCHAR(120) UNIQUE;')
            if 'google_workspace_email' in columns_to_add:
                print('  ALTER TABLE "user" ADD COLUMN google_workspace_email VARCHAR(120) UNIQUE;')
            print()

def verify_migration():
    """Verify that the migration was successful."""
    
    with app.app_context():
        try:
            print("=" * 70)
            print("Verifying Migration...")
            print("=" * 70)
            print()
            
            # Check columns again
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            required_columns = ['email', 'google_workspace_email']
            all_present = all(col in columns for col in required_columns)
            
            if all_present:
                print("✅ All required columns are present:")
                for col in required_columns:
                    print(f"   ✅ {col}")
                print()
                print("=" * 70)
                print("✅ Migration verification PASSED!")
                print("=" * 70)
                return True
            else:
                print("❌ Some columns are missing:")
                for col in required_columns:
                    if col in columns:
                        print(f"   ✅ {col}")
                    else:
                        print(f"   ❌ {col} - MISSING")
                print()
                print("=" * 70)
                print("❌ Migration verification FAILED!")
                print("=" * 70)
                return False
                
        except Exception as e:
            print(f"❌ Error during verification: {str(e)}")
            return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        # Verification mode
        verify_migration()
    else:
        # Migration mode
        print()
        print("🚀 Starting production database migration...")
        print()
        add_email_columns_to_user_table()
        print()
        print("🔍 Verifying migration...")
        print()
        verify_migration()

