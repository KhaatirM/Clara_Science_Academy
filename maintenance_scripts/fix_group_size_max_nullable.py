#!/usr/bin/env python3
"""
Make group_size_max nullable so blank = unlimited.
Run once; safe to run multiple times.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text


def fix_group_size_max_nullable():
    """Make group_assignment.group_size_max nullable (NULL = unlimited)."""
    app = create_app()
    with app.app_context():
        dialect = db.engine.dialect.name
        if dialect == "postgresql":
            try:
                db.session.execute(text(
                    "ALTER TABLE group_assignment ALTER COLUMN group_size_max DROP NOT NULL"
                ))
                db.session.commit()
                print("Made group_assignment.group_size_max nullable (PostgreSQL)")
            except Exception as e:
                db.session.rollback()
                err = str(e).lower()
                if "does not exist" in err or "already" in err or "cannot drop" in err:
                    print("Column already nullable or unchanged:", e)
                else:
                    print("Error:", e)
        else:
            print("SQLite: column is typically nullable by default. No change needed.")


if __name__ == "__main__":
    fix_group_size_max_nullable()
