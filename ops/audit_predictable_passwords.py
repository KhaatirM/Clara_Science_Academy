#!/usr/bin/env python3
"""
Audit portal accounts for predictable (legacy) passwords and optionally reset them.

Legacy patterns this script detects:
  - Students:  firstname + 4-digit birth year (e.g. john2012)
  - Staff:     firstname + year 2000–2010 (e.g. jane2007)
  - Parents:   Parent + last 4 digits of linked student guardian phone
  - Shared:    legacy shared Google onboarding password (optional AUDIT_LEGACY_GOOGLE_PASSWORDS env)

Usage:
  python scripts/audit_predictable_passwords.py              # report only
  python scripts/audit_predictable_passwords.py --json
  python scripts/audit_predictable_passwords.py --apply      # reset flagged accounts
  python scripts/audit_predictable_passwords.py --apply --output creds.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from typing import Optional

# Project root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from werkzeug.security import check_password_hash, generate_password_hash

from utils.google_workspace_passwords import legacy_google_passwords_for_audit
from utils.temporary_passwords import generate_temporary_password


@dataclass
class FlaggedAccount:
    user_id: int
    username: str
    role: str
    reason: str
    matched_pattern: str
    is_temporary_password: bool
    new_password: Optional[str] = None


def _birth_year_from_dob(dob: str) -> Optional[str]:
    if not dob:
        return None
    dob = dob.strip()
    if "-" in dob:
        return dob.split("-", 1)[0]
    if "/" in dob:
        parts = dob.split("/")
        if len(parts) == 3:
            return parts[2]
    return None


def _student_predictable_candidates(student) -> list[str]:
    first = (student.first_name or "").strip().lower()
    year = _birth_year_from_dob(getattr(student, "dob", "") or "")
    if not first or not year or len(year) < 4:
        return []
    return [f"{first}{year[-4:]}"]


def _staff_predictable_candidates(staff) -> list[str]:
    first = (staff.first_name or "staff").strip().lower()
    return [f"{first}{year}" for year in range(2000, 2011)]


def _parent_predictable_candidates(user, db_session) -> list[str]:
    from models import ParentStudentLink, Student

    candidates: set[str] = set()
    links = db_session.query(ParentStudentLink).filter_by(parent_user_id=user.id).all()
    for link in links:
        student = db_session.get(Student, link.student_id)
        if not student:
            continue
        for phone in (student.parent1_phone, student.parent2_phone):
            digits = re.sub(r"\D", "", phone or "")
            if len(digits) >= 4:
                candidates.add(f"Parent{digits[-4:]}")
    return sorted(candidates)


def _matches_any(user, candidates: list[str]) -> Optional[str]:
    for candidate in candidates:
        if check_password_hash(user.password_hash, candidate):
            return candidate
    return None


def audit_users(*, apply: bool = False) -> list[FlaggedAccount]:
    from app import create_app
    from extensions import db
    from models import Student, TeacherStaff, User

    app = create_app()
    flagged: list[FlaggedAccount] = []

    with app.app_context():
        users = User.query.order_by(User.id).all()
        shared_candidates = legacy_google_passwords_for_audit()
        if os.environ.get("AUDIT_INCLUDE_COMMON_TEST_PASSWORDS", "").strip().lower() in ("1", "true", "yes"):
            shared_candidates = [*shared_candidates, "password123"]
        reset_user_ids: set[int] = set()

        for user in users:
            reasons: list[tuple[str, str]] = []

            matched = _matches_any(user, shared_candidates)
            if matched:
                reasons.append(("shared_default_password", matched))

            if user.role == "Student" and user.student_id:
                student = db.session.get(Student, user.student_id)
                if student:
                    matched = _matches_any(user, _student_predictable_candidates(student))
                    if matched:
                        reasons.append(("predictable_student_password", matched))

            if user.teacher_staff_id:
                staff = db.session.get(TeacherStaff, user.teacher_staff_id)
                if staff:
                    matched = _matches_any(user, _staff_predictable_candidates(staff))
                    if matched:
                        reasons.append(("predictable_staff_password", matched))

            if user.role == "Parent":
                matched = _matches_any(user, _parent_predictable_candidates(user, db.session))
                if matched:
                    reasons.append(("predictable_parent_password", matched))

            if user.is_temporary_password and not reasons:
                reasons.append(("temporary_password_not_changed", "(unknown — force reset recommended)"))

            if not reasons:
                continue

            new_pwd: Optional[str] = None
            if apply and user.id not in reset_user_ids:
                new_pwd = generate_temporary_password()
                user.password_hash = generate_password_hash(new_pwd)
                user.is_temporary_password = True
                user.password_changed_at = None
                reset_user_ids.add(user.id)

            for reason, pattern in reasons:
                flagged.append(
                    FlaggedAccount(
                        user_id=user.id,
                        username=user.username,
                        role=user.role,
                        reason=reason,
                        matched_pattern=pattern,
                        is_temporary_password=bool(user.is_temporary_password),
                        new_password=new_pwd if reason == reasons[0][0] else None,
                    )
                )

        if apply and reset_user_ids:
            db.session.commit()

    return flagged


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit or reset predictable portal passwords.")
    parser.add_argument("--apply", action="store_true", help="Reset flagged accounts to random passwords.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="When using --apply, write username,new_password CSV for distribution.",
    )
    args = parser.parse_args()

    if args.apply:
        print("Applying password resets for flagged accounts...", flush=True)
    else:
        print("Dry run — no passwords will be changed. Pass --apply to reset.", flush=True)

    flagged = audit_users(apply=args.apply)

    if args.json:
        print(json.dumps([asdict(row) for row in flagged], indent=2))
    else:
        if not flagged:
            print("No predictable or stale temporary passwords found.")
        else:
            print(f"Flagged {len(flagged)} account(s):\n")
            for row in flagged:
                line = (
                    f"  id={row.user_id} user={row.username} role={row.role} "
                    f"reason={row.reason} pattern={row.matched_pattern}"
                )
                if row.new_password:
                    line += f" -> NEW PASSWORD SET (see --output)"
                print(line)

    if args.apply and args.output and flagged:
        with open(args.output, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["user_id", "username", "role", "reason", "new_password"])
            for row in flagged:
                if row.new_password:
                    writer.writerow([row.user_id, row.username, row.role, row.reason, row.new_password])
        print(f"\nWrote new credentials to {args.output}")

    if args.apply and flagged:
        print("\nDone. Users must change password on next login (is_temporary_password=True).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
