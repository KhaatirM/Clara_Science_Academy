"""
Database migration script to add discussion_attachment table for discussion file uploads.
Run this script to enable students to attach images and documents when creating threads and replies.

Usage (from project root):
    python migrations_scripts/add_discussion_attachments.py

Or with Flask shell:
    flask shell
    >>> from migrations_scripts.add_discussion_attachments import create_discussion_attachment_table
    >>> create_discussion_attachment_table()
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

app = create_app()
from sqlalchemy import text


def create_discussion_attachment_table():
    """Create discussion_attachment table if it doesn't exist."""
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            if db.engine.dialect.name == 'sqlite':
                tables = inspector.get_table_names()
                if 'discussion_attachment' in tables:
                    print("Table 'discussion_attachment' already exists.")
                    return
            else:
                tables = inspector.get_table_names()
                if 'discussion_attachment' in tables:
                    print("Table 'discussion_attachment' already exists.")
                    return

            print("Creating 'discussion_attachment' table...")

            if db.engine.dialect.name == 'sqlite':
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE discussion_attachment (
                            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            thread_id INTEGER,
                            post_id INTEGER,
                            attachment_filename VARCHAR(255) NOT NULL,
                            attachment_original_filename VARCHAR(255),
                            attachment_file_path VARCHAR(500),
                            attachment_file_size INTEGER,
                            attachment_mime_type VARCHAR(100),
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(thread_id) REFERENCES discussion_thread (id) ON DELETE CASCADE,
                            FOREIGN KEY(post_id) REFERENCES discussion_post (id) ON DELETE CASCADE
                        )
                    """))
                    conn.commit()
            else:
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE discussion_attachment (
                            id SERIAL PRIMARY KEY,
                            thread_id INTEGER REFERENCES discussion_thread(id) ON DELETE CASCADE,
                            post_id INTEGER REFERENCES discussion_post(id) ON DELETE CASCADE,
                            attachment_filename VARCHAR(255) NOT NULL,
                            attachment_original_filename VARCHAR(255),
                            attachment_file_path VARCHAR(500),
                            attachment_file_size INTEGER,
                            attachment_mime_type VARCHAR(100),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.commit()

            print("Successfully created 'discussion_attachment' table!")
            print("Students can now upload images and documents when creating discussion threads and replies.")

        except Exception as e:
            print(f"Error creating table: {str(e)}")
            raise


if __name__ == '__main__':
    create_discussion_attachment_table()
