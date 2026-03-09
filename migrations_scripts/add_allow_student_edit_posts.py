"""
Database migration script to add allow_student_edit_posts column to Assignment model.
Run this script to enable the "allow students to edit their posts" setting for discussion assignments.

Usage (from project root):
    python migrations_scripts/add_allow_student_edit_posts.py

Or with Flask shell:
    flask shell
    >>> from migrations_scripts.add_allow_student_edit_posts import add_allow_student_edit_posts_column
    >>> add_allow_student_edit_posts_column()
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

app = create_app()
from sqlalchemy import text


def add_allow_student_edit_posts_column():
    """Add allow_student_edit_posts column to Assignment table if it doesn't exist."""
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('assignment')]

            if 'allow_student_edit_posts' in columns:
                print("Column 'allow_student_edit_posts' already exists in Assignment table.")
                return

            print("Adding 'allow_student_edit_posts' column to Assignment table...")

            # Use INTEGER for boolean (0/1) - works with SQLite and PostgreSQL
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE assignment ADD COLUMN allow_student_edit_posts INTEGER DEFAULT 0 NOT NULL"
                ))
                conn.commit()

            print("Successfully added 'allow_student_edit_posts' column to Assignment table!")
            print("Teachers and administrators can now enable post editing when creating discussion assignments.")

        except Exception as e:
            print(f"Error adding column: {str(e)}")
            raise


if __name__ == '__main__':
    add_allow_student_edit_posts_column()
