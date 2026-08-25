#!/usr/bin/env python3
"""Thin wrapper → ops/sync_class_google_classroom_rosters.py"""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    target = os.path.join(root, "ops", "sync_class_google_classroom_rosters.py")
    return subprocess.call([sys.executable, target, *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
