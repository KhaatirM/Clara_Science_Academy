#!/usr/bin/env python3
"""Add teacher_staff.google_workspace_email if missing (Postgres / SQLite)."""

from __future__ import annotations

import os
import sys


def main() -> int:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)

    from app import create_app
    from config import DevelopmentConfig, ProductionConfig
    from sqlalchemy import text

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    ConfigClass = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=ConfigClass)

    with app.app_context():
        from extensions import db

        dialect = db.engine.dialect.name
        with db.engine.connect() as conn:
            if dialect == "postgresql":
                exists = conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'teacher_staff' "
                        "AND column_name = 'google_workspace_email'"
                    )
                ).fetchone()
                if exists:
                    print("teacher_staff.google_workspace_email already exists")
                    return 0
                conn.execute(
                    text(
                        "ALTER TABLE teacher_staff "
                        "ADD COLUMN google_workspace_email VARCHAR(120)"
                    )
                )
                conn.commit()
                print("Added teacher_staff.google_workspace_email")
            else:
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info(teacher_staff)"))]
                if "google_workspace_email" in cols:
                    print("teacher_staff.google_workspace_email already exists")
                    return 0
                conn.execute(
                    text(
                        "ALTER TABLE teacher_staff "
                        "ADD COLUMN google_workspace_email VARCHAR(120)"
                    )
                )
                conn.commit()
                print("Added teacher_staff.google_workspace_email")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
