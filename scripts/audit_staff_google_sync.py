#!/usr/bin/env python3
"""
List every TeacherStaff row that the Google Directory cron would sync.

Run on Render (same env as the cron job):

    python scripts/audit_staff_google_sync.py

Optional filter:

    python scripts/audit_staff_google_sync.py --search muhammad
"""

from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit staff rows used by sync_all_to_google.py")
    parser.add_argument("--search", help="Filter by name or email substring (case-insensitive)")
    args = parser.parse_args()

    try:
        from app import create_app
        from config import DevelopmentConfig, ProductionConfig
        from extensions import db
        from models import TeacherStaff, User
        from services.google_ou_policy import get_staff_ou_path, staff_google_account_eligible
    except Exception as e:
        print(f"[ERROR] Bootstrap failed: {e}")
        return 1

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    ConfigClass = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=ConfigClass)

    needle = (args.search or "").strip().lower()

    with app.app_context():
        from scripts.render_db_guard import print_database_target, require_postgres_database

        require_postgres_database(app, script_name="audit_staff_google_sync.py")
        print_database_target(app)
        print("=" * 80)

        staff_rows = TeacherStaff.query.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()
        users_by_staff = {
            u.teacher_staff_id: u
            for u in User.query.filter(User.teacher_staff_id.isnot(None)).all()
        }

        matched = 0
        for staff in staff_rows:
            u = users_by_staff.get(staff.id)
            ws = (getattr(u, "google_workspace_email", None) or "").strip() if u else ""
            if not ws:
                continue

            label = f"{staff.first_name or ''} {staff.last_name or ''}".strip()
            hay = f"{label} {staff.email or ''} {ws}".lower()
            if needle and needle not in hay:
                continue

            matched += 1
            eligible = staff_google_account_eligible(staff)
            ou = get_staff_ou_path(staff, u)
            print(
                f"id={staff.id}  {label}\n"
                f"  workspace={ws}\n"
                f"  personal_email={staff.email or '(none)'}\n"
                f"  is_deleted={staff.is_deleted}  is_active={getattr(staff, 'is_active', True)}  "
                f"employment={staff.employment_status}  portal_login={staff.portal_login}\n"
                f"  cron_eligible={eligible}  target_ou={ou}\n"
            )

        print("=" * 80)
        print(f"Staff with Workspace email on file: {matched} shown / {len(staff_rows)} total TeacherStaff rows")
        if needle and matched == 0:
            print(f"No rows matched --search {args.search!r}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
