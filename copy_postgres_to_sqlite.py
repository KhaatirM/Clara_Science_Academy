"""
Copy data from PostgreSQL database to SQLite database using SQLAlchemy.
This script connects to a local PostgreSQL database and copies all data to SQLite.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import *  # Import all models
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

def copy_postgres_to_sqlite(pg_uri, sqlite_path):
    """Copy all data from PostgreSQL to SQLite."""
    print("=" * 70)
    print("COPYING DATA FROM POSTGRESQL TO SQLITE")
    print("=" * 70)
    
    # Connect to PostgreSQL
    print(f"\nConnecting to PostgreSQL: {pg_uri.split('@')[1] if '@' in pg_uri else pg_uri}")
    pg_engine = create_engine(pg_uri)
    pg_session = sessionmaker(bind=pg_engine)()
    
    # Connect to SQLite
    print(f"Connecting to SQLite: {sqlite_path}")
    sqlite_engine = create_engine(f'sqlite:///{sqlite_path}')
    sqlite_session = sessionmaker(bind=sqlite_engine)()
    
    # Get all table names
    pg_inspector = inspect(pg_engine)
    tables = pg_inspector.get_table_names()
    
    print(f"\nFound {len(tables)} tables to copy")
    
    # Copy each table
    for table_name in tables:
        try:
            print(f"\nCopying {table_name}...")
            
            # Get data from PostgreSQL
            result = pg_session.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            columns = result.keys()
            
            if not rows:
                print(f"  (empty table, skipping)")
                continue
            
            # Clear SQLite table
            sqlite_session.execute(text(f"DELETE FROM {table_name}"))
            
            # Insert data into SQLite
            # Note: This is simplified. Complex data types may need conversion.
            for row in rows:
                values = dict(zip(columns, row))
                # Build INSERT statement
                cols = ', '.join(columns)
                placeholders = ', '.join([':' + col for col in columns])
                insert_sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                sqlite_session.execute(text(insert_sql), values)
            
            sqlite_session.commit()
            print(f"  [OK] Copied {len(rows)} rows")
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            sqlite_session.rollback()
            continue
    
    pg_session.close()
    sqlite_session.close()
    
    print("\n" + "=" * 70)
    print("[OK] Copy completed!")
    print("=" * 70)

def main():
    """Main function."""
    # PostgreSQL connection string
    # Update these with your local PostgreSQL credentials
    pg_host = os.environ.get('PG_HOST', 'localhost')
    pg_port = os.environ.get('PG_PORT', '5432')
    pg_user = os.environ.get('PG_USER', 'postgres')
    pg_password = os.environ.get('PGPASSWORD') or os.environ.get('PG_PASSWORD', 'Lithium_3')
    pg_database = os.environ.get('PG_DATABASE', 'clara_science_local')
    
    if not pg_password:
        print("=" * 70)
        print("POSTGRESQL PASSWORD REQUIRED")
        print("=" * 70)
        print("\nPlease set your PostgreSQL password using one of these methods:")
        print("\n1. Set environment variable (PowerShell):")
        print("   $env:PGPASSWORD = 'your_password'")
        print("\n2. Set environment variable (Command Prompt):")
        print("   set PGPASSWORD=your_password")
        print("\n3. Or update this script directly with your password")
        print("\nThen run this script again.")
        return
    
    pg_uri = f'postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}'
    
    # SQLite path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sqlite_path = os.path.join(project_root, "instance", "app.db")
    
    copy_postgres_to_sqlite(pg_uri, sqlite_path)

if __name__ == '__main__':
    main()

