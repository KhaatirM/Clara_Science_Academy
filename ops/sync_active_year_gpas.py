#!/usr/bin/env python3
"""Force-refresh Student.gpa for roster (K-8 active year; HS cumulative tenure)."""

from __future__ import annotations

import json
import os
import sys


def _bootstrap_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


def main() -> int:
    _bootstrap_path()
    from app import create_app
    from config import DevelopmentConfig, ProductionConfig

    config_name = (os.environ.get("FLASK_ENV") or "development").strip().lower()
    config_class = ProductionConfig if config_name == "production" else DevelopmentConfig
    app = create_app(config_class=config_class)
    with app.app_context():
        from utils.student_gpa import sync_active_year_gpas

        result = sync_active_year_gpas(commit=True, force=True)
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
