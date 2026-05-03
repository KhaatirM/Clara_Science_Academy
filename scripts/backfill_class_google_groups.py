#!/usr/bin/env python3
"""
Ensure every class has a Google Group (class-{id}-{YYYY}@clarascienceacademy.org) and
membership matches enrolled students + assigned teachers.

Run once after deploy or from cron alongside Directory sync:

  python scripts/backfill_class_google_groups.py

Requires GOOGLE_DIRECTORY_* and a delegated admin with Groups API access.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if "." not in sys.path:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    try:
        from app import create_app
        from config import DevelopmentConfig, ProductionConfig
    except Exception as e:
        print(f"[ERROR] Bootstrap import failed: {e}")
        return 1

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    ConfigClass = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=ConfigClass)

    from models import Class
    from services.class_google_group import provision_and_sync_class_google_group

    ok = 0
    fail = 0
    with app.app_context():
        for c in Class.query.order_by(Class.id).all():
            if provision_and_sync_class_google_group(c.id):
                ok += 1
            else:
                fail += 1
                print(f"[WARN] class_id={c.id} name={c.name!r} sync returned False")

    print(f"Done. classes_ok={ok} classes_failed={fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
