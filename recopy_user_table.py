#!/usr/bin/env python3
"""
Re-copy the user table from PostgreSQL to SQLite.
"""

import sys
import os
from sqlalchemy import create_engine, text, inspect

def recopy_user_table():
    """Re-copy user table from PostgreSQL to SQLite."""
    try:
        from app import create_app
        from extensions import db
        
        app = create_app()
        
        with app.app_context():
            print("=" * 70)
            print("RE-COPYING USER TABLE FROM POSTGRESQL TO SQLITE")
            print("=" * 70)
            
            # PostgreSQL connection
            pg_password = os.environ.get('PGPASSWORD') or os.environ.get('PG_PASSWORD', 'Lithium_3')
            pg_uri = f'postgresql://postgres:{pg_password}@localhost:5432/clara_science_local'
            pg_engine = create_engine(pg_uri)
            
            # SQLite connection
            sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "app.db")
            sqlite_engine = create_engine(f'sqlite:///{sqlite_path}')
            
            print("\n[1] Getting user data from PostgreSQL...")
            with pg_engine.connect() as pg_conn:
                # Get all columns from PostgreSQL user table
                pg_inspector = inspect(pg_engine)
                pg_columns = [col['name'] for col in pg_inspector.get_columns('user')]
                print(f"    Found columns: {', '.join(pg_columns)}")
                
                # Get all rows
                result = pg_conn.execute(text('SELECT * FROM "user"'))
                rows = result.fetchall()
                print(f"    Found {len(rows)} users in PostgreSQL")
            
            if not rows:
                print("\n[WARNING] No users found in PostgreSQL!")
                return
            
            print("\n[2] Getting SQLite user table columns...")
            sqlite_inspector = inspect(sqlite_engine)
            sqlite_columns = [col['name'] for col in sqlite_inspector.get_columns('user')]
            print(f"    SQLite columns: {', '.join(sqlite_columns)}")
            
            # Find columns that exist in both
            common_columns = [col for col in pg_columns if col in sqlite_columns]
            print(f"\n[3] Common columns: {', '.join(common_columns)}")
            
            print("\n[4] Clearing SQLite user table...")
            with sqlite_engine.connect() as sqlite_conn:
                sqlite_conn.execute(text("DELETE FROM user"))
                sqlite_conn.commit()
            
            print("\n[5] Copying users to SQLite...")
            copied = 0
            with sqlite_engine.connect() as sqlite_conn:
                for row in rows:
                    try:
                        # Build values dict with only common columns
                        row_dict = dict(zip(pg_columns, row))
                        values = {col: row_dict.get(col) for col in common_columns if col in row_dict}
                        
                        # Build INSERT statement
                        cols = ', '.join(common_columns)
                        placeholders = ', '.join([':' + col for col in common_columns])
                        insert_sql = f"INSERT INTO user ({cols}) VALUES ({placeholders})"
                        
                        sqlite_conn.execute(text(insert_sql), values)
                        copied += 1
                    except Exception as e:
                        print(f"    [ERROR] Failed to copy user {row_dict.get('username', 'unknown')}: {e}")
                        continue
                
                sqlite_conn.commit()
            
            print(f"\n[OK] Successfully copied {copied} out of {len(rows)} users")
            
            print("\n" + "=" * 70)
            print("COPY COMPLETED!")
            print("=" * 70)
            
    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    recopy_user_table()

