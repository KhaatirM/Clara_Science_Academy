#!/usr/bin/env python3
"""
Migration script to add assignment_type field to Assignment table
Run this in Render shell: python add_assignment_type_field.py
"""

import os
import psycopg2
from urllib.parse import urlparse

def add_assignment_type_field():
    """Add assignment_type field to Assignment table using direct PostgreSQL connection"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return
    
    try:
        # Parse the database URL
        parsed_url = urlparse(database_url)
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            database=parsed_url.path[1:],  # Remove leading slash
            user=parsed_url.username,
            password=parsed_url.password
        )
        
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'assignment' 
            AND column_name = 'assignment_type'
        """)
        
        if cursor.fetchone():
            print("✅ assignment_type column already exists")
            return
        
        # Add the assignment_type column
        cursor.execute("""
            ALTER TABLE assignment 
            ADD COLUMN assignment_type VARCHAR(20) DEFAULT 'pdf' NOT NULL
        """)
        
        # Update existing assignments to have 'pdf' as default type
        cursor.execute("""
            UPDATE assignment 
            SET assignment_type = 'pdf' 
            WHERE assignment_type IS NULL
        """)
        
        conn.commit()
        print("✅ Successfully added assignment_type field to Assignment table")
        print("✅ Set default value 'pdf' for existing assignments")
        
    except Exception as e:
        print(f"❌ Error adding assignment_type field: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    add_assignment_type_field()
