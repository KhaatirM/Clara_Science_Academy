"""
Import PostgreSQL directory format export using pg_restore or direct connection.
This handles the PostgreSQL custom format (.dat files).
"""

import sys
import os
import subprocess
from pathlib import Path

def check_pg_restore():
    """Check if pg_restore is available."""
    try:
        result = subprocess.run(['pg_restore', '--version'], 
                              capture_output=True, text=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def import_with_pg_restore(export_dir, db_name='clara_science_local'):
    """Import using pg_restore to PostgreSQL, then copy to SQLite."""
    print("=" * 70)
    print("IMPORTING POSTGRESQL DIRECTORY FORMAT EXPORT")
    print("=" * 70)
    
    # Find the database directory
    db_dirs = list(Path(export_dir).rglob("*.dat"))
    if not db_dirs:
        print(f"Error: No database files found in {export_dir}")
        return False
    
    # Get the directory containing toc.dat (table of contents)
    toc_files = list(Path(export_dir).rglob("toc.dat"))
    if not toc_files:
        print("Error: No toc.dat file found (required for pg_restore)")
        return False
    
    db_dir = toc_files[0].parent
    print(f"\nDatabase directory: {db_dir}")
    
    if not check_pg_restore():
        print("\n[ERROR] pg_restore not found!")
        print("\nYou have two options:")
        print("\n1. Install PostgreSQL (includes pg_restore):")
        print("   Download from: https://www.postgresql.org/download/windows/")
        print("   Then run: pg_restore -d clara_science_local database_export/...")
        print("\n2. Use direct database connection (requires credentials):")
        print("   We can create a script to copy data directly from production.")
        return False
    
    print("\n[OK] pg_restore found!")
    print(f"\nImporting to PostgreSQL database: {db_name}")
    print("Note: This will create a new PostgreSQL database.")
    
    # Create database command
    create_db_cmd = ['createdb', db_name]
    restore_cmd = ['pg_restore', '-d', db_name, '-v', str(db_dir)]
    
    try:
        # Create database
        print(f"\nCreating database: {db_name}...")
        result = subprocess.run(create_db_cmd, capture_output=True, text=True)
        if result.returncode != 0 and 'already exists' not in result.stderr:
            print(f"Warning: {result.stderr}")
        
        # Restore database
        print(f"\nRestoring from {db_dir}...")
        result = subprocess.run(restore_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[OK] Successfully imported to PostgreSQL database: {db_name}")
            print("\nNext step: Copy data from PostgreSQL to SQLite")
            print("Run: python copy_postgres_to_sqlite.py")
            return True
        else:
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main function."""
    export_dir = os.path.join(os.path.dirname(__file__), "database_export")
    
    # Find the actual database directory
    for root, dirs, files in os.walk(export_dir):
        if 'toc.dat' in files:
            db_dir = root
            print(f"Found database directory: {db_dir}")
            import_with_pg_restore(export_dir, db_name='clara_science_local')
            return
    
    print(f"Error: Could not find database directory in {export_dir}")
    print("\nPlease check the extracted files.")

if __name__ == '__main__':
    main()

