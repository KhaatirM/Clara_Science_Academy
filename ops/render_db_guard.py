"""Guardrails so Render cron/shell jobs do not silently sync against SQLite."""

from __future__ import annotations

import os
import sys


def database_uri_looks_like_sqlite(uri: str) -> bool:
    return (uri or "").strip().lower().startswith("sqlite")


def is_render_or_production() -> bool:
    if os.environ.get("RENDER") or os.environ.get("RENDER_SERVICE_ID"):
        return True
    return (os.environ.get("FLASK_ENV") or "").strip().lower() == "production"


def require_postgres_database(app, *, script_name: str = "script") -> None:
    """
    Exit with a clear message when a job would use SQLite on Render/production.

    The web app uses PostgreSQL via DATABASE_URL; cron jobs must use the same variable.
    """
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    if database_uri_looks_like_sqlite(uri) and is_render_or_production():
        print("=" * 80)
        print(f"[FATAL] {script_name}: DATABASE_URL is not set for this job.")
        print()
        print("This process would use SQLite instead of production PostgreSQL:")
        print(f"  {uri}")
        print()
        print("That explains stale staff/students in Google sync (e.g. removed people still syncing).")
        print()
        print("Fix in Render Dashboard:")
        print("  1. Open your Cron Job (or link it to the same Environment Group as the web app).")
        print("  2. Add DATABASE_URL — same value as your web service / Postgres instance.")
        print("  3. Also copy: FLASK_ENV=production, GOOGLE_DIRECTORY_*, SECRET_KEY, etc.")
        print("  4. Re-run: python scripts/audit_staff_google_sync.py --search muhammad")
        print("     Expected: Database: …render.com/…  (PostgreSQL), not sqlite:///…/app.db")
        print("=" * 80)
        sys.exit(1)


def print_database_target(app) -> None:
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    if database_uri_looks_like_sqlite(uri):
        print(f"Database source: {uri} (SQLite — local/dev only)")
    elif "@" in uri:
        print(f"Database source: {uri.split('@')[-1].split('?')[0]} (PostgreSQL)")
    elif uri:
        print(f"Database source: {uri}")
    else:
        print("Database source: (SQLALCHEMY_DATABASE_URI not set)")
