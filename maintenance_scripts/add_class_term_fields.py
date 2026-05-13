"""
Migration script to add class term metadata fields.

Adds:
- class.term_type (VARCHAR, default 'full_year', not null)
- class.term_value (VARCHAR, nullable)

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
        if "class" not in tables:
            print("class table not found; nothing to migrate.")
            return True

        existing = [c["name"] for c in inspector.get_columns("class")]
        db_url = str(db.engine.url)
        is_postgres = "postgresql" in db_url.lower() or "postgres" in db_url.lower()

        stmts = []
        if "term_type" not in existing:
            if is_postgres:
                stmts.append("ALTER TABLE class ADD COLUMN term_type VARCHAR(20) NOT NULL DEFAULT 'full_year'")
            else:
                stmts.append("ALTER TABLE class ADD COLUMN term_type VARCHAR(20) NOT NULL DEFAULT 'full_year'")

        if "term_value" not in existing:
            stmts.append("ALTER TABLE class ADD COLUMN term_value VARCHAR(10)")

        if not stmts:
            print("class term columns already exist; skipping.")
            return True

        for sql in stmts:
            print(f"Running: {sql}")
            db.session.execute(text(sql))
            db.session.commit()

        print("Done.")
        return True


if __name__ == "__main__":
    ok = migrate()
    sys.exit(0 if ok else 1)

