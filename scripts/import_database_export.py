"""
Script to import PostgreSQL database export into local SQLite database.
This script handles the conversion from PostgreSQL format to SQLite.
"""

import sys
import os
import tarfile
import sqlite3
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def sanitize_path(path):
    """Sanitize path for Windows by replacing invalid characters."""
    # Replace invalid Windows filename characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        path = path.replace(char, '_')
    # Remove leading/trailing dots and spaces
    path = path.strip('. ')
    # Remove leading .\ or ./
    if path.startswith('.\\') or path.startswith('./'):
        path = path[2:]
    return path

def extract_export_file(export_path):
    """Extract the tar.gz file and return the path to the SQL dump."""
    print(f"Extracting {export_path}...")
    
    if not os.path.exists(export_path):
        print(f"Error: File not found: {export_path}")
        return None
    
    # Create a directory for extracted files
    extract_dir = os.path.join(os.path.dirname(export_path), "database_export")
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        with tarfile.open(export_path, 'r:gz') as tar:
            # Extract each member individually, sanitizing paths
            for member in tar.getmembers():
                # Sanitize the member name
                original_name = member.name
                sanitized_name = sanitize_path(original_name)
                member.name = sanitized_name
                
                # Extract the member
                try:
                    tar.extract(member, extract_dir)
                except Exception as e:
                    print(f"Warning: Could not extract {original_name}: {e}")
                    continue
            
            print(f"[OK] Extracted to {extract_dir}")
            
            # Find SQL files in the extracted directory
            sql_files = list(Path(extract_dir).rglob("*.sql"))
            if sql_files:
                return str(sql_files[0])
            else:
                # Check if it's a directory with database files
                print("Looking for database files...")
                # List all files in the extracted directory
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith(('.sql', '.dump', '.db', '.sqlite')):
                            file_path = os.path.join(root, file)
                            print(f"Found: {file_path}")
                            return file_path
                return extract_dir
    except Exception as e:
        print(f"Error extracting file: {e}")
        import traceback
        traceback.print_exc()
        return None


def convert_postgres_to_sqlite(postgres_dump_path, sqlite_db_path):
    """
    Convert PostgreSQL dump to SQLite format.
    Note: This is a simplified conversion. Some PostgreSQL-specific features may need manual adjustment.
    """
    print(f"\nConverting PostgreSQL dump to SQLite...")
    print(f"Source: {postgres_dump_path}")
    print(f"Target: {sqlite_db_path}")
    
    # Read the PostgreSQL dump
    try:
        with open(postgres_dump_path, 'r', encoding='utf-8') as f:
            pg_dump = f.read()
    except Exception as e:
        print(f"Error reading PostgreSQL dump: {e}")
        return False
    
    # Basic PostgreSQL to SQLite conversions
    sqlite_dump = pg_dump
    
    # Remove PostgreSQL-specific commands
    sqlite_dump = sqlite_dump.replace('SET statement_timeout = 0;', '')
    sqlite_dump = sqlite_dump.replace('SET lock_timeout = 0;', '')
    sqlite_dump = sqlite_dump.replace('SET idle_in_transaction_session_timeout = 0;', '')
    sqlite_dump = sqlite_dump.replace('SET client_encoding = \'UTF8\';', '')
    sqlite_dump = sqlite_dump.replace('SET standard_conforming_strings = on;', '')
    sqlite_dump = sqlite_dump.replace('SELECT pg_catalog.set_config(\'search_path\', \'\', false);', '')
    sqlite_dump = sqlite_dump.replace('SET check_function_bodies = false;', '')
    sqlite_dump = sqlite_dump.replace('SET xmloption = content;', '')
    sqlite_dump = sqlite_dump.replace('SET default_tablespace = \'\';', '')
    sqlite_dump = sqlite_dump.replace('SET default_table_access_method = heap;', '')
    
    # Replace PostgreSQL data types
    sqlite_dump = sqlite_dump.replace('SERIAL', 'INTEGER')
    sqlite_dump = sqlite_dump.replace('BIGSERIAL', 'INTEGER')
    sqlite_dump = sqlite_dump.replace('TIMESTAMP WITHOUT TIME ZONE', 'TIMESTAMP')
    sqlite_dump = sqlite_dump.replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP')
    sqlite_dump = sqlite_dump.replace('TEXT', 'TEXT')
    sqlite_dump = sqlite_dump.replace('VARCHAR', 'TEXT')
    sqlite_dump = sqlite_dump.replace('BOOLEAN', 'INTEGER')
    sqlite_dump = sqlite_dump.replace('TRUE', '1')
    sqlite_dump = sqlite_dump.replace('FALSE', '0')
    
    # Remove CREATE EXTENSION commands
    import re
    sqlite_dump = re.sub(r'CREATE EXTENSION.*?;', '', sqlite_dump, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove ALTER TABLE ... OWNER TO commands
    sqlite_dump = re.sub(r'ALTER TABLE.*?OWNER TO.*?;', '', sqlite_dump, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove COMMENT ON commands
    sqlite_dump = re.sub(r'COMMENT ON.*?;', '', sqlite_dump, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove COPY commands and replace with INSERT (simplified)
    # Note: This is a basic conversion. Complex COPY statements may need manual handling.
    
    # Write the converted SQLite dump
    sqlite_dump_path = postgres_dump_path.replace('.sql', '_sqlite.sql')
    try:
        with open(sqlite_dump_path, 'w', encoding='utf-8') as f:
            f.write(sqlite_dump)
        print(f"[OK] Converted dump saved to: {sqlite_dump_path}")
        return sqlite_dump_path
    except Exception as e:
        print(f"Error writing SQLite dump: {e}")
        return None


def import_to_sqlite(sqlite_dump_path, db_path):
    """Import the SQLite dump into the database file."""
    print(f"\nImporting into SQLite database: {db_path}")
    
    # Ensure the instance directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Read and execute the SQL dump
        with open(sqlite_dump_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Execute the script (split by semicolons for better error handling)
        # Note: This is simplified. Complex scripts may need more sophisticated parsing.
        cursor.executescript(sql_script)
        conn.commit()
        print(f"[OK] Successfully imported data into {db_path}")
        return True
    except Exception as e:
        print(f"Error importing data: {e}")
        print("\nNote: PostgreSQL to SQLite conversion may require manual adjustments.")
        print("Consider using a tool like 'pgloader' or importing directly to PostgreSQL.")
        conn.rollback()
        return False
    finally:
        conn.close()


def main():
    """Main function to import database export."""
    print("=" * 70)
    print("DATABASE EXPORT IMPORT TOOL")
    print("=" * 70)
    
    # Get the export file path
    if len(sys.argv) > 1:
        export_path = sys.argv[1]
    else:
        # Look for common export file names in the project root
        project_root = os.path.dirname(os.path.abspath(__file__))
        possible_files = [
            os.path.join(project_root, "2025-11-20T14_32Z.dir.tar.gz"),
            os.path.join(project_root, "database_export.tar.gz"),
            os.path.join(project_root, "export.tar.gz"),
        ]
        
        # Also check Downloads folder
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(downloads_path):
            for file in os.listdir(downloads_path):
                if file.endswith('.tar.gz') and '2025' in file:
                    possible_files.append(os.path.join(downloads_path, file))
        
        export_path = None
        for path in possible_files:
            if os.path.exists(path):
                export_path = path
                break
        
        if not export_path:
            print("\nPlease provide the path to your database export file:")
            print("Usage: python import_database_export.py <path_to_export.tar.gz>")
            print("\nOr place the file in one of these locations:")
            for path in possible_files:
                print(f"  - {path}")
            return
    
    print(f"\nUsing export file: {export_path}")
    
    # Extract the file
    extracted_path = extract_export_file(export_path)
    if not extracted_path:
        return
    
    # Determine the database path
    project_root = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(project_root, "instance", "app.db")
    
    print(f"\nTarget database: {db_path}")
    
    # Check if database already exists
    if os.path.exists(db_path):
        # In non-interactive mode, create backup and proceed
        import shutil
        backup_path = db_path + ".backup"
        if not os.path.exists(backup_path):
            shutil.copy2(db_path, backup_path)
            print(f"[OK] Backed up existing database to {backup_path}")
        print(f"Note: Existing database will be overwritten.")
    
    # If it's a SQL file, convert and import
    if extracted_path.endswith('.sql'):
        sqlite_dump = convert_postgres_to_sqlite(extracted_path, db_path)
        if sqlite_dump:
            import_to_sqlite(sqlite_dump, db_path)
    else:
        print(f"\nFound directory: {extracted_path}")
        print("Please specify the SQL dump file, or use a PostgreSQL import tool.")
        print("\nAlternative: Use pgloader or psql to import directly to PostgreSQL,")
        print("then use SQLAlchemy to copy data to SQLite.")


if __name__ == '__main__':
    main()

