#!/usr/bin/env python3
"""
Stress test for Google Directory SSOT sync.

By default this runs in DRY RUN mode (no writes). To apply changes, set:
  APPLY_CHANGES=1

Optional tuning:
  MAX_STUDENTS=1000
  MAX_CLASSES=1000
  SLEEP_MS=50          (sleep between API calls)
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Tuple


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except Exception:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _sleep_ms(ms: int) -> None:
    if ms and ms > 0:
        time.sleep(ms / 1000.0)


@dataclass
class StressStats:
    students_scanned: int = 0
    student_reads_ok: int = 0
    student_reads_fail: int = 0
    students_need_move: int = 0
    students_moved: int = 0
    students_suspend_needed: int = 0
    students_suspended: int = 0

    classes_scanned: int = 0
    groups_synced: int = 0
    groups_failed: int = 0

    start_ts: float = 0.0
    end_ts: float = 0.0

    @property
    def elapsed_s(self) -> float:
        return max(0.0, self.end_ts - self.start_ts)


def main() -> int:
    # Ensure repo root is on sys.path when running from scripts/
    if "." not in sys.path:
        sys.path.append(".")

    try:
        from app import create_app
        from config import DevelopmentConfig
    except Exception as e:
        print(f"[ERROR] Failed to import app bootstrap: {e}")
        return 1

    try:
        from extensions import db
        from models import Class, Enrollment, Student, User
        from services.google_directory_service import (
            get_google_user,
            move_user_to_ou,
            suspend_user,
            sync_group_members,
        )
        from services.google_ou_policy import resolve_student_ou
    except Exception as e:
        print(f"[ERROR] Failed to import app modules: {e}")
        return 1

    apply_changes = _env_bool("APPLY_CHANGES", default=False)
    max_students = _env_int("MAX_STUDENTS", 1000)
    max_classes = _env_int("MAX_CLASSES", 1000)
    sleep_ms = _env_int("SLEEP_MS", 50)

    print("=" * 80)
    print("DIRECTORY STRESS TEST")
    print("=" * 80)
    print(f"Mode: {'APPLY' if apply_changes else 'DRY RUN'}")
    print(f"MAX_STUDENTS={max_students} MAX_CLASSES={max_classes} SLEEP_MS={sleep_ms}")
    print("=" * 80)

    app = create_app(config_class=DevelopmentConfig)
    stats = StressStats(start_ts=time.time())

    with app.app_context():
        # ---- Students ----
        student_rows: List[Tuple[Student, str]] = (
            db.session.query(Student, User.google_workspace_email)
            .join(User, User.student_id == Student.id)
            .filter(User.google_workspace_email.isnot(None))
            .limit(max_students)
            .all()
        )

        for student, ws_email in student_rows:
            stats.students_scanned += 1
            ws_email = (ws_email or "").strip()
            if not ws_email:
                continue

            decision = resolve_student_ou(
                grade_level=getattr(student, "grade_level", None),
                grad_year=getattr(student, "grad_year", None),
                expected_grad_date=getattr(student, "expected_grad_date", None),
                is_active=bool(getattr(student, "is_active", True)),
                marked_for_removal=bool(getattr(student, "marked_for_removal", False)),
                status_updated_at=getattr(student, "status_updated_at", None),
                expected_graduation_year=getattr(student, "expected_graduation_year", None),
            )

            g_user = get_google_user(ws_email)
            _sleep_ms(sleep_ms)
            if not g_user:
                stats.student_reads_fail += 1
                continue
            stats.student_reads_ok += 1

            current_ou = g_user.get("orgUnitPath")
            is_suspended = bool(g_user.get("suspended", False))

            if current_ou != decision.target_ou_path:
                stats.students_need_move += 1
                if apply_changes:
                    if move_user_to_ou(ws_email, decision.target_ou_path) is True:
                        stats.students_moved += 1
                    _sleep_ms(sleep_ms)

            if decision.should_suspend_now:
                stats.students_suspend_needed += 1
                if apply_changes and not is_suspended:
                    if suspend_user(ws_email):
                        stats.students_suspended += 1
                    _sleep_ms(sleep_ms)

            if stats.students_scanned % 50 == 0:
                print(
                    f"[students] scanned={stats.students_scanned} reads_ok={stats.student_reads_ok} "
                    f"need_move={stats.students_need_move} moved={stats.students_moved} "
                    f"suspend_needed={stats.students_suspend_needed} suspended={stats.students_suspended}"
                )

        # ---- Classes / Groups ----
        class_rows: List[Class] = (
            Class.query.filter(Class.google_group_email.isnot(None))
            .limit(max_classes)
            .all()
        )

        for c in class_rows:
            stats.classes_scanned += 1
            group_email = (c.google_group_email or "").strip()
            if not group_email:
                continue

            roster_rows = (
                db.session.query(User.google_workspace_email)
                .join(Student, Student.id == User.student_id)
                .join(Enrollment, Enrollment.student_id == Student.id)
                .filter(
                    Enrollment.class_id == c.id,
                    Enrollment.is_active == True,
                    Student.is_deleted == False,
                    User.google_workspace_email.isnot(None),
                )
                .all()
            )
            roster_emails = [(r[0] or "").strip() for r in roster_rows if r and r[0]]

            if apply_changes:
                ok = sync_group_members(group_email, roster_emails)
                _sleep_ms(sleep_ms)
                if ok:
                    stats.groups_synced += 1
                else:
                    stats.groups_failed += 1
            else:
                # dry run: just count as scanned
                stats.groups_synced += 1

            if stats.classes_scanned % 25 == 0:
                print(
                    f"[groups] scanned={stats.classes_scanned} ok={stats.groups_synced} failed={stats.groups_failed}"
                )

    stats.end_ts = time.time()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Elapsed: {stats.elapsed_s:.1f}s")
    print(
        "Students: "
        f"scanned={stats.students_scanned} reads_ok={stats.student_reads_ok} reads_fail={stats.student_reads_fail} "
        f"need_move={stats.students_need_move} moved={stats.students_moved} "
        f"suspend_needed={stats.students_suspend_needed} suspended={stats.students_suspended}"
    )
    print(
        "Groups: "
        f"classes_scanned={stats.classes_scanned} synced={stats.groups_synced} failed={stats.groups_failed}"
    )
    print("=" * 80)
    if not apply_changes:
        print("DRY RUN completed. Set APPLY_CHANGES=1 to perform moves/suspends/group updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

