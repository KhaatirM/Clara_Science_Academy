"""
Migration script to add quiz sections support.
Creates quiz_section table and adds section_id to quiz_question.

Run this script once to update the database schema.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text, inspect


def add_quiz_sections():
    """Create quiz_section table and add section_id to quiz_question."""
    app = create_app()

    with app.app_context():
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            db_url = str(db.engine.url)
            is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()

            # 1. Create quiz_section table if it doesn't exist
            if 'quiz_section' not in tables:
                print("Creating quiz_section table...")
                with db.engine.connect() as conn:
                    if is_postgres:
                        conn.execute(text("""
                            CREATE TABLE quiz_section (
                                id SERIAL PRIMARY KEY,
                                assignment_id INTEGER NOT NULL REFERENCES assignment(id) ON DELETE CASCADE,
                                title VARCHAR(200) NOT NULL,
                                "order" INTEGER NOT NULL DEFAULT 0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                    else:
                        conn.execute(text("""
                            CREATE TABLE quiz_section (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                assignment_id INTEGER NOT NULL REFERENCES assignment(id) ON DELETE CASCADE,
                                title VARCHAR(200) NOT NULL,
                                "order" INTEGER NOT NULL DEFAULT 0,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                    conn.commit()
                print("  quiz_section table created.")
            else:
                print("quiz_section table already exists.")

            # 2. Add section_id to quiz_question if missing
            if 'quiz_question' not in tables:
                print("quiz_question table not found; skipping section_id column.")
                return True

            existing_columns = [c['name'] for c in inspector.get_columns('quiz_question')]
            if 'section_id' not in existing_columns:
                print("Adding section_id column to quiz_question...")
                with db.engine.connect() as conn:
                    if is_postgres:
                        conn.execute(text(
                            "ALTER TABLE quiz_question ADD COLUMN section_id INTEGER REFERENCES quiz_section(id) ON DELETE SET NULL"
                        ))
                    else:
                        conn.execute(text(
                            "ALTER TABLE quiz_question ADD COLUMN section_id INTEGER REFERENCES quiz_section(id) ON DELETE SET NULL"
                        ))
                    conn.commit()
                print("  section_id column added.")
            else:
                print("quiz_question.section_id already exists.")

            return True
        except Exception as e:
            print(f"Error: {e}")
            raise


if __name__ == '__main__':
    print("Running quiz sections migration...")
    success = add_quiz_sections()
    print("Done." if success else "Migration failed.")
    sys.exit(0 if success else 1)
