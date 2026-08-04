#!/usr/bin/env python3
"""Thin wrapper → ops/backfill_student_google_accounts.py"""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    target = os.path.join(root, "ops", "backfill_student_google_accounts.py")
    return subprocess.call([sys.executable, target, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
