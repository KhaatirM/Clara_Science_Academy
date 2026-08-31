"""Rename the two cleaning/lunch teams from "Team 1" and "Team 2" to real names.

Usage (from the repo root, e.g. a Render shell):

    python scripts/rename_cleaning_teams.py --dry-run
    python scripts/rename_cleaning_teams.py

By default "Team 1" becomes "Comet Crew" and "Team 2" becomes "Nova Crew".
Pass --names to choose your own pair:

    python scripts/rename_cleaning_teams.py --names "Summit Crew" "Horizon Crew"

Only the name changes: members, duties, inspections, scores and lunch checks
all stay attached to the same team.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from extensions import db  # noqa: E402
from models import CleaningTeam  # noqa: E402

DEFAULT_NAMES = ('Comet Crew', 'Nova Crew')

# "Team 1", "Cleanup Team 1", "team1" — anything ending in the number.
_NUMBERED_RE = re.compile(r'\bteam\s*0*(\d+)\b', re.IGNORECASE)


def _numbered_teams() -> dict[int, CleaningTeam]:
    """Active teams whose name still ends in a bare number, keyed by that number."""
    found: dict[int, CleaningTeam] = {}
    for team in CleaningTeam.query.filter_by(is_active=True).order_by(CleaningTeam.id).all():
        match = _NUMBERED_RE.search(team.team_name or '')
        if not match:
            continue
        number = int(match.group(1))
        found.setdefault(number, team)
    return found


def rename_teams(names: tuple[str, str], *, dry_run: bool) -> int:
    numbered = _numbered_teams()
    if not numbered:
        print('No teams named like "Team 1" / "Team 2" were found. Nothing to do.')
        for team in CleaningTeam.query.filter_by(is_active=True).all():
            print(f'  active team #{team.id}: "{team.team_name}"')
        return 0

    taken = {
        (t.team_name or '').strip().lower()
        for t in CleaningTeam.query.filter_by(is_active=True).all()
    }

    changed = False
    for index, new_name in enumerate(names, start=1):
        team = numbered.get(index)
        if not team:
            print(f'No team {index} found; skipping "{new_name}".')
            continue
        old_name = team.team_name
        if (old_name or '').strip().lower() == new_name.strip().lower():
            print(f'#{team.id} is already called "{new_name}".')
            continue
        if new_name.strip().lower() in taken:
            print(f'Another active team is already called "{new_name}"; skipping #{team.id}.')
            continue

        print(f'#{team.id} "{old_name}" -> "{new_name}"')
        if not dry_run:
            team.team_name = new_name.strip()
        taken.discard((old_name or '').strip().lower())
        taken.add(new_name.strip().lower())
        changed = True

    if not changed:
        print('Nothing to rename.')
        return 0
    if dry_run:
        db.session.rollback()
        print('Dry run — no changes written.')
        return 0

    db.session.commit()
    print('Done.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Show the renames without saving.')
    parser.add_argument(
        '--names',
        nargs=2,
        metavar=('TEAM_1', 'TEAM_2'),
        default=list(DEFAULT_NAMES),
        help='New names for team 1 and team 2.',
    )
    args = parser.parse_args()

    with app.app_context():
        return rename_teams((args.names[0], args.names[1]), dry_run=args.dry_run)


if __name__ == '__main__':
    raise SystemExit(main())
