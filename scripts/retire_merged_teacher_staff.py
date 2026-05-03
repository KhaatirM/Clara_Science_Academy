"""
One-time fix: after a user merge, retire the old TeacherStaff row that no longer has a login.

  python scripts/retire_merged_teacher_staff.py --merge-staff-id 8 --keep-staff-id 7

Reassigns references merge → keep, then soft-deletes the merge staff record.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models import TeacherStaff
from utils.merge_teacher_staff_cleanup import consolidate_duplicate_teacher_staff_rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--merge-staff-id", type=int, required=True, help="TeacherStaff id to remove (orphan profile)")
    p.add_argument("--keep-staff-id", type=int, required=True, help="TeacherStaff id to keep (linked to login)")
    args = p.parse_args()

    if args.merge_staff_id == args.keep_staff_id:
        raise SystemExit("merge-staff-id and keep-staff-id must differ")

    app = create_app()
    with app.app_context():
        m = db.session.get(TeacherStaff, args.merge_staff_id)
        k = db.session.get(TeacherStaff, args.keep_staff_id)
        if not m or not k:
            raise SystemExit("One or both TeacherStaff ids not found.")
        print(f"Merge staff: {m.id} {m.first_name} {m.last_name!r} deleted={m.is_deleted}")
        print(f"Keep staff:  {k.id} {k.first_name} {k.last_name!r} deleted={k.is_deleted}")
        consolidate_duplicate_teacher_staff_rows(args.merge_staff_id, args.keep_staff_id)
        db.session.commit()
        print("Done: references reassigned; merge profile soft-deleted.")


if __name__ == "__main__":
    main()
