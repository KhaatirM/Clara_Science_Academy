"""
Migration script to add timed-quiz persistence fields to QuizProgress.

Adds:
- quiz_progress.timer_started_at (DateTime/TIMESTAMP, nullable)
- quiz_progress.timer_remaining_seconds (Integer, nullable)

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
        if "quiz_progress" not in tables:
            print("quiz_progress table not found; nothing to migrate.")
            return True

        existing = [c["name"] for c in inspector.get_columns("quiz_progress")]
        db_url = str(db.engine.url)
        is_postgres = "postgresql" in db_url.lower() or "postgres" in db_url.lower()

        cols = []
        if "timer_started_at" not in existing:
            cols.append(
                "ALTER TABLE quiz_progress ADD COLUMN timer_started_at TIMESTAMP"
                if is_postgres
                else "ALTER TABLE quiz_progress ADD COLUMN timer_started_at DATETIME"
            )
        if "timer_remaining_seconds" not in existing:
            cols.append("ALTER TABLE quiz_progress ADD COLUMN timer_remaining_seconds INTEGER")

        if not cols:
            print("quiz_progress timer columns already exist; skipping.")
            return True

        for sql in cols:
            print(f"Running: {sql}")
            db.session.execute(text(sql))
            db.session.commit()

        print("Done.")
        return True


if __name__ == "__main__":
    ok = migrate()
    sys.exit(0 if ok else 1)

