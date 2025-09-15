#!/usr/bin/env python3
"""
Simple migration script to create AssignmentExtension table
Run this in Render shell: python create_assignment_extension_simple.py
"""

import os
import psycopg2
from urllib.parse import urlparse

def create_assignment_extension_table():
    """Create the AssignmentExtension table using direct PostgreSQL connection"""
    
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
        
        # Check if table already exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'assignment_extension'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ AssignmentExtension table already exists. Skipping creation.")
            return
        
        # Create the table
        cursor.execute("""
            CREATE TABLE assignment_extension (
                id SERIAL PRIMARY KEY,
                assignment_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                extended_due_date TIMESTAMP NOT NULL,
                reason TEXT,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (assignment_id) REFERENCES assignment (id),
                FOREIGN KEY (student_id) REFERENCES student (id),
                FOREIGN KEY (granted_by) REFERENCES teacher_staff (id)
            );
        """)
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX idx_assignment_extension_assignment_id ON assignment_extension (assignment_id);
        """)
        
        cursor.execute("""
            CREATE INDEX idx_assignment_extension_student_id ON assignment_extension (student_id);
        """)
        
        cursor.execute("""
            CREATE INDEX idx_assignment_extension_active ON assignment_extension (is_active);
        """)
        
        # Commit the changes
        conn.commit()
        
        print("✅ AssignmentExtension table created successfully!")
        print("✅ Indexes created for better performance!")
        
        # Verify the table was created
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'assignment_extension';
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Verification: Table '{result[0]}' exists in database")
        else:
            print("❌ Verification failed: Table not found")
        
    except Exception as e:
        print(f"❌ Error creating AssignmentExtension table: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    create_assignment_extension_table()
