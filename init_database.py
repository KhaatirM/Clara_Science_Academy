"""
Database initialization script to add missing columns.
This will run automatically when the app starts to ensure the database schema is up to date.
"""

import os
import psycopg2
from urllib.parse import urlparse

def init_database():
    """Initialize database with missing columns."""
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("DATABASE_URL not found, skipping database initialization")
            return True
        
        # Parse the database URL
        parsed = urlparse(database_url)
        
        # Connect to the database
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password,
            sslmode='require'
        )
        
        cursor = conn.cursor()
        
        # Check if assignment_type column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='assignment' AND column_name='assignment_type'
        """)
        
        if not cursor.fetchone():
            print("Adding assignment_type column to assignment table...")
            cursor.execute("""
                ALTER TABLE assignment 
                ADD COLUMN assignment_type VARCHAR(20) DEFAULT 'pdf'
            """)
            print("assignment_type column added successfully")
        else:
            print("assignment_type column already exists")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

if __name__ == '__main__':
    init_database()
