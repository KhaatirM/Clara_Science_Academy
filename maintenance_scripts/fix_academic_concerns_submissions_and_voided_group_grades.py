"""
One-off maintenance: align submission rows and group grades with Academic Concerns rules.

1) Individual assignments: if a student has a non-voided Grade with no positive earned
   credit (0% / 0 points per grade_data), set their Submission row to
   submission_type='not_submitted' when it was 'online' or 'in_person', so the
   concerns UI matches "no credit = not submitted".

2) Group assignments: if GroupAssignment.status is 'Voided', ensure every GroupGrade
   for that assignment has is_voided=True (fixes stale rows that still drove 0%
   alerts after voiding).

Run from project root:
  python maintenance_scripts/fix_academic_concerns_submissions_and_voided_group_grades.py
  python maintenance_scripts/fix_academic_concerns_submissions_and_voided_group_grades.py --dry-run

Requires DATABASE_URL / app config (same as other maintenance scripts).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models import Grade, Assignment, Submission, GroupAssignment, GroupGrade
from utils.at_risk_alerts import _percentage_from_grade_data
from utils.academic_concern_submission import grade_shows_positive_earned_credit


def _sync_submissions_for_zero_credit(dry_run: bool) -> int:
    changed = 0
    submissions = (
        Submission.query.filter(Submission.submission_type.in_(("online", "in_person"))).all()
    )
    for sub in submissions:
        grade = (
            Grade.query.filter_by(
                student_id=sub.student_id,
                assignment_id=sub.assignment_id,
            )
            .filter(Grade.is_voided.is_(False))
            .first()
        )
        if not grade or not grade.grade_data:
            continue
        assignment = Assignment.query.get(sub.assignment_id)
        if not assignment or assignment.status == "Voided":
            continue
        if grade_shows_positive_earned_credit(grade):
            continue
        # Parseable non-positive credit (includes explicit 0)
        try:
            import json

            gd = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
        except (TypeError, ValueError):
            continue
        if not isinstance(gd, dict):
            continue
        total_pts = float(assignment.total_points or 100.0)
        pct, _ = _percentage_from_grade_data(gd, total_pts)
        if pct is None:
            continue
        if pct > 0:
            continue
        if dry_run:
            print(
                f"[dry-run] Would set submission id={sub.id} student={sub.student_id} "
                f"assignment={sub.assignment_id} to not_submitted (grade pct={pct})"
            )
        else:
            sub.submission_type = "not_submitted"
        changed += 1
    return changed


def _void_group_grades_for_voided_assignments(dry_run: bool) -> int:
    changed = 0
    voided_ga_ids = [
        r[0]
        for r in db.session.query(GroupAssignment.id)
        .filter(GroupAssignment.status == "Voided")
        .all()
    ]
    if not voided_ga_ids:
        return 0
    stale = (
        GroupGrade.query.filter(
            GroupGrade.group_assignment_id.in_(voided_ga_ids),
            GroupGrade.is_voided.is_(False),
        )
        .all()
    )
    from datetime import datetime

    for gg in stale:
        if dry_run:
            print(
                f"[dry-run] Would void GroupGrade id={gg.id} ga_id={gg.group_assignment_id} "
                f"student_id={gg.student_id}"
            )
        else:
            gg.is_voided = True
            gg.voided_at = datetime.utcnow()
            gg.voided_reason = "maintenance: align with voided group assignment"
        changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without committing",
    )
    args = parser.parse_args()
    dry = bool(args.dry_run)

    app = create_app()
    with app.app_context():
        n_sub = _sync_submissions_for_zero_credit(dry)
        n_grp = _void_group_grades_for_voided_assignments(dry)
        if dry:
            print(f"Dry run complete. Submission rows to update: {n_sub}; group grades to void: {n_grp}")
            return 0
        db.session.commit()
        print(
            f"Committed. Updated {n_sub} submission(s) to not_submitted; "
            f"voided {n_grp} stale group_grade row(s) for voided group assignments."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
