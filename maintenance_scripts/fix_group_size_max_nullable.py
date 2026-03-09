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
    """Make group_assignment.group_size_max nullable (NULL = unlimited).
    Also clear accidental default of 4 where limit was left blank by user."""
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

            # Clear accidental default 4 (user left limit blank) so groups become unlimited
            try:
                result = db.session.execute(text(
                    "UPDATE group_assignment SET group_size_max = NULL WHERE group_size_max = 4"
                ))
                db.session.commit()
                n = getattr(result, 'rowcount', 0) or 0
                if n > 0:
                    print(f"Cleared accidental max=4 limit on {n} group assignment(s) - now unlimited")
            except Exception as e:
                db.session.rollback()
                print("Note: Could not clear default 4 values:", e)
        else:
            # SQLite
            try:
                result = db.session.execute(text(
                    "UPDATE group_assignment SET group_size_max = NULL WHERE group_size_max = 4"
                ))
                db.session.commit()
                n = getattr(result, 'rowcount', 0) or 0
                if n > 0:
                    print(f"Cleared accidental max=4 limit on {n} group assignment(s) - now unlimited")
            except Exception as e:
                db.session.rollback()
                print("Note: Could not clear default 4 values:", e)


if __name__ == "__main__":
    fix_group_size_max_nullable()
