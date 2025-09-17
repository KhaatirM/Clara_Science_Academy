"""
Add assignment_type column to assignment table in production database.
This script can be run on Render to fix the missing column issue.
"""

import os
import psycopg2
from urllib.parse import urlparse

def add_assignment_type_column():
    """Add the assignment_type column to the assignment table."""
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("ERROR: DATABASE_URL environment variable not found")
            return False
        
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
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='assignment' AND column_name='assignment_type'
        """)
        
        if cursor.fetchone():
            print("assignment_type column already exists")
            conn.close()
            return True
        
        # Add the column
        cursor.execute("""
            ALTER TABLE assignment 
            ADD COLUMN assignment_type VARCHAR(20) DEFAULT 'pdf' NOT NULL
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("SUCCESS: assignment_type column added to assignment table")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == '__main__':
    print("Adding assignment_type column to assignment table...")
    if add_assignment_type_column():
        print("Column added successfully!")
    else:
        print("Failed to add column.")
