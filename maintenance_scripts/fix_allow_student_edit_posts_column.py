#!/usr/bin/env python3
"""
Add allow_student_edit_posts column to assignment table if missing.
Required for discussion assignments where students can edit their posts.
Used by Render releaseCommand via scripts/startup.py.
"""

import sys
import os

# Ensure project root is in path (when run from maintenance_scripts/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect


def fix_allow_student_edit_posts_column():
    """Add allow_student_edit_posts column to assignment table if it doesn't exist."""
    try:
        from app import create_app
        from extensions import db

        app = create_app()

        with app.app_context():
            inspector = inspect(db.engine)
            columns = [col["name"] for col in inspector.get_columns("assignment")]

            if "allow_student_edit_posts" in columns:
                print("allow_student_edit_posts column already exists in assignment table")
                return

            dialect = db.engine.dialect.name
            if dialect == "postgresql":
                sql = (
                    "ALTER TABLE assignment ADD COLUMN allow_student_edit_posts "
                    "BOOLEAN DEFAULT FALSE NOT NULL"
                )
            else:
                # SQLite uses INTEGER for boolean (0/1)
                sql = (
                    "ALTER TABLE assignment ADD COLUMN allow_student_edit_posts "
                    "INTEGER DEFAULT 0 NOT NULL"
                )

            with db.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()

            print("Successfully added allow_student_edit_posts column to assignment table")

    except Exception as e:
        print(f"Error adding allow_student_edit_posts column: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    fix_allow_student_edit_posts_column()
