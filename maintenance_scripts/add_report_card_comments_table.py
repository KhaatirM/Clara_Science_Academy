"""
Migration script to add report card comments support.

Creates table:
- report_card_comment

Run once to update the database schema.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import create_app
from extensions import db


def migrate() -> bool:
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if "report_card_comment" in tables:
            print("report_card_comment table already exists; skipping.")
            return True

        db_url = str(db.engine.url)
        is_postgres = "postgresql" in db_url.lower() or "postgres" in db_url.lower()

        if is_postgres:
            sql = """
            CREATE TABLE report_card_comment (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES student(id) ON DELETE CASCADE,
                class_id INTEGER NOT NULL REFERENCES class(id) ON DELETE CASCADE,
                school_year_id INTEGER NOT NULL REFERENCES school_year(id) ON DELETE CASCADE,
                quarter VARCHAR(10) NOT NULL,
                comment_text TEXT NULL,
                author_user_id INTEGER NULL REFERENCES "user"(id) ON DELETE SET NULL,
                author_teacher_staff_id INTEGER NULL REFERENCES teacher_staff(id) ON DELETE SET NULL,
                source VARCHAR(20) NOT NULL DEFAULT 'teacher',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_report_card_comment_key UNIQUE (student_id, class_id, school_year_id, quarter)
            );
            """
        else:
            sql = """
            CREATE TABLE report_card_comment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES student(id) ON DELETE CASCADE,
                class_id INTEGER NOT NULL REFERENCES class(id) ON DELETE CASCADE,
                school_year_id INTEGER NOT NULL REFERENCES school_year(id) ON DELETE CASCADE,
                quarter VARCHAR(10) NOT NULL,
                comment_text TEXT NULL,
                author_user_id INTEGER NULL REFERENCES user(id) ON DELETE SET NULL,
                author_teacher_staff_id INTEGER NULL REFERENCES teacher_staff(id) ON DELETE SET NULL,
                source VARCHAR(20) NOT NULL DEFAULT 'teacher',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_report_card_comment_key UNIQUE (student_id, class_id, school_year_id, quarter)
            );
            """

        print("Creating report_card_comment table...")
        db.session.execute(text(sql))
        db.session.commit()
        print("Done.")
        return True


if __name__ == "__main__":
    ok = migrate()
    sys.exit(0 if ok else 1)

