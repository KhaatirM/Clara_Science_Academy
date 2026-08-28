"""Copy bell periods from one grade's schedule to other grades.

Usage (from the repo root, e.g. a Render shell):

    python scripts/copy_bell_periods.py --source 4 --targets 5,6,7,8
    python scripts/copy_bell_periods.py --source 4 --targets 5,6,7,8 --dry-run

Each target grade's existing periods (and any class assignments attached to
them) are replaced with a copy of the source grade's periods.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from extensions import db  # noqa: E402
from models import BellPeriod, BellPeriodClassAssignment  # noqa: E402
from utils.bell_schedule import ensure_active_bell_schedule, grade_label  # noqa: E402


def parse_grades(raw: str) -> list[int]:
    grades: list[int] = []
    for chunk in raw.replace(' ', ',').split(','):
        if not chunk:
            continue
        grades.append(int(chunk))
    if not grades:
        raise ValueError('No grades provided')
    return grades


def copy_periods(source_grade: int, target_grades: list[int], *, dry_run: bool) -> int:
    source = ensure_active_bell_schedule(grade_level=source_grade)
    if not source:
        print('No active school year — nothing to copy.')
        return 1

    source_periods = sorted(source.periods or [], key=lambda p: (p.sort_order or 0, p.id or 0))
    if not source_periods:
        print(f'{grade_label(source_grade)} has no bell periods to copy.')
        return 1

    print(f'Source: {grade_label(source_grade)} — {len(source_periods)} periods')
    for period in source_periods:
        print(f'  {period.name} ({period.kind}) {period.start_time}–{period.end_time}')

    for grade in target_grades:
        if grade == source_grade:
            print(f'Skipping {grade_label(grade)} (same as source).')
            continue

        target = ensure_active_bell_schedule(grade_level=grade)
        if not target:
            print(f'Could not resolve a schedule for {grade_label(grade)}; skipping.')
            continue

        existing = list(target.periods or [])
        period_ids = [p.id for p in existing]
        assignments = (
            BellPeriodClassAssignment.query.filter(
                BellPeriodClassAssignment.bell_period_id.in_(period_ids)
            ).all()
            if period_ids
            else []
        )

        print(
            f'{grade_label(grade)}: replacing {len(existing)} periods '
            f'and {len(assignments)} class assignments'
        )
        if dry_run:
            continue

        for assignment in assignments:
            db.session.delete(assignment)
        for period in existing:
            db.session.delete(period)
        db.session.flush()

        for src in source_periods:
            copy = BellPeriod(
                bell_schedule_id=target.id,
                name=src.name,
                kind=src.kind,
                start_time=src.start_time,
                end_time=src.end_time,
                color_hex=src.color_hex,
                sort_order=src.sort_order,
                days_of_week_json=src.days_of_week_json,
            )
            db.session.add(copy)

    if dry_run:
        print('Dry run — no changes written.')
        return 0

    db.session.commit()
    print('Done. Bell periods copied.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Copy bell periods between grade schedules.')
    parser.add_argument('--source', type=int, default=4, help='Grade to copy from (default: 4)')
    parser.add_argument(
        '--targets',
        default='5,6,7,8',
        help='Comma-separated grades to copy to (default: 5,6,7,8)',
    )
    parser.add_argument('--dry-run', action='store_true', help='Show the plan without saving')
    args = parser.parse_args()

    with app.app_context():
        return copy_periods(args.source, parse_grades(args.targets), dry_run=args.dry_run)


if __name__ == '__main__':
    raise SystemExit(main())
