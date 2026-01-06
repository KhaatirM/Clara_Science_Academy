#!/usr/bin/env python3
"""
Verify that the local application is using SQLite, not PostgreSQL.
This ensures we don't accidentally connect to the production database.
"""

import os
import sys

def verify_database_connection():
    """Verify the database connection is SQLite."""
    print("=" * 70)
    print("DATABASE CONNECTION VERIFICATION")
    print("=" * 70)
    
    # Check environment variable
    print("\n[1] Checking DATABASE_URL environment variable...")
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print(f"    [WARNING] DATABASE_URL is set: {database_url[:50]}...")
        if 'postgresql' in database_url.lower() or 'postgres' in database_url.lower():
            print("    [ERROR] DATABASE_URL points to PostgreSQL!")
            print("    [ERROR] This could connect to production database!")
            print("\n    To use local SQLite, unset DATABASE_URL:")
            print("    PowerShell: Remove-Item Env:\\DATABASE_URL")
            print("    Command Prompt: set DATABASE_URL=")
            return False
        else:
            print("    [OK] DATABASE_URL does not point to PostgreSQL")
    else:
        print("    [OK] DATABASE_URL is not set (will use SQLite)")
    
    # Check actual database connection
    print("\n[2] Checking actual database connection...")
    try:
        from app import create_app
        from extensions import db
        from config import DevelopmentConfig
        
        app = create_app(config_class=DevelopmentConfig)
        
        with app.app_context():
            db_uri = str(db.engine.url)
            print(f"    Database URI: {db_uri}")
            
            if 'sqlite' in db_uri.lower():
                print("    [OK] Using SQLite database (local, safe)")
                
                # Get the actual database file path
                if '///' in db_uri:
                    db_path = db_uri.split('///')[-1]
                    print(f"    Database file: {db_path}")
                    if os.path.exists(db_path):
                        file_size = os.path.getsize(db_path) / (1024 * 1024)  # Size in MB
                        print(f"    Database file size: {file_size:.2f} MB")
                    else:
                        print("    [INFO] Database file does not exist yet (will be created)")
                
                return True
            elif 'postgresql' in db_uri.lower() or 'postgres' in db_uri.lower():
                print("    [ERROR] Using PostgreSQL database!")
                print("    [ERROR] This could be the production database!")
                return False
            else:
                print(f"    [WARNING] Unknown database type: {db_uri}")
                return False
                
    except Exception as e:
        print(f"    [ERROR] Could not verify database connection: {e}")
        return False

if __name__ == '__main__':
    is_safe = verify_database_connection()
    
    print("\n" + "=" * 70)
    if is_safe:
        print("[OK] VERIFICATION PASSED - Using local SQLite database")
        print("=" * 70)
        sys.exit(0)
    else:
        print("[ERROR] VERIFICATION FAILED - May be connected to PostgreSQL!")
        print("=" * 70)
        print("\nDO NOT PROCEED until this is fixed!")
        sys.exit(1)

