"""Merge each grade's separate Art and Music classes into one Art/Music class.

Usage (from the repo root, e.g. a Render shell):

    python scripts/merge_art_music_classes.py --dry-run
    python scripts/merge_art_music_classes.py

For every grade level, all Art/Music classes in the school year are collapsed
into a single winner class. Enrollments, assignments, grades, attendance,
schedules, notes and every other row that points at a losing class is repointed
to the winner (dropping rows that would duplicate one the winner already has),
then the losing classes are deleted and the winner is renamed to "Art/Music N".
"""

from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select, update  # noqa: E402

from app import app  # noqa: E402
from extensions import db  # noqa: E402
from models import Class, Enrollment, SchoolYear  # noqa: E402
from utils.core_class_catalog import (  # noqa: E402
    ART_MUSIC_SUBJECT,
    SETUP_GRADE_LEVELS,
    grade_label,
    grade_name_suffix,
)

# Word-boundary matches so "Language Arts" is never treated as an art class.
_ART_MUSIC_RE = re.compile(r'\b(art|music)\b')
_COMBINED_RE = re.compile(r'\bart\s*[/&+]\s*music\b|\bart and music\b')
_EXCLUDE_RE = re.compile(r'language arts|martial|smart')

# Columns that must stay unique alongside class_id. When a losing row would
# collide with one the winner already has, the losing row is dropped instead of
# being repointed.
DEDUPE_KEYS: dict[str, tuple[str, ...]] = {
    'enrollment': ('student_id',),
    'bell_period_class_assignment': ('bell_period_id',),
    'quarter_grade': ('student_id', 'school_year_id', 'quarter'),
    'report_card_comment': ('student_id', 'school_year_id', 'quarter'),
    'student_assistant': ('student_id',),
    'class_notes_drive_link': ('drive_folder_id',),
    'class_syllabus': (),
    'class_additional_teachers': ('teacher_id',),
    'class_substitute_teachers': ('teacher_id',),
    'class_schedule': ('day_of_week', 'start_time', 'end_time'),
}


def _norm(value: str | None) -> str:
    return (value or '').strip().lower()


def is_art_music_class(class_obj: Class) -> bool:
    haystack = f'{_norm(class_obj.name)} {_norm(class_obj.subject)}'
    if _EXCLUDE_RE.search(haystack):
        return bool(_COMBINED_RE.search(haystack))
    return bool(_ART_MUSIC_RE.search(haystack))


def class_fk_columns():
    """Every (table, column) in the schema that references class.id."""
    class_table = Class.__table__
    found = []
    for table in db.metadata.sorted_tables:
        if table is class_table:
            continue
        for column in table.columns:
            for fk in column.foreign_keys:
                if fk.column.table is class_table and fk.column.name == 'id':
                    found.append((table, column))
                    break
    return found


def enrollment_counts(class_ids: list[int]) -> dict[int, int]:
    counts = dict.fromkeys(class_ids, 0)
    rows = (
        db.session.query(Enrollment.class_id, db.func.count(Enrollment.id))
        .filter(Enrollment.class_id.in_(class_ids))
        .group_by(Enrollment.class_id)
        .all()
    )
    for class_id, count in rows:
        counts[class_id] = count
    return counts


def pick_winner(candidates: list[Class]) -> Class:
    """Prefer an already-combined, active class with the most students."""
    counts = enrollment_counts([c.id for c in candidates])

    def rank(c: Class):
        haystack = f'{_norm(c.name)} {_norm(c.subject)}'
        return (
            0 if _COMBINED_RE.search(haystack) else 1,
            0 if c.is_active else 1,
            -counts.get(c.id, 0),
            c.id,
        )

    return sorted(candidates, key=rank)[0]


def repoint_class_references(winner_id: int, loser_id: int) -> tuple[int, int]:
    """Move every row pointing at loser_id over to winner_id.

    Returns (rows_moved, rows_dropped_as_duplicates).
    """
    moved = 0
    dropped = 0

    for table, column in class_fk_columns():
        dedupe_cols = DEDUPE_KEYS.get(table.name)
        if dedupe_cols is None:
            result = db.session.execute(
                update(table).where(column == loser_id).values({column.name: winner_id})
            )
            moved += result.rowcount or 0
            continue

        key_cols = [table.c[name] for name in dedupe_cols]
        existing = {
            tuple(row) for row in db.session.execute(select(*key_cols).where(column == winner_id))
        } if key_cols else set()
        winner_has_row = db.session.execute(
            select(db.func.count()).select_from(table).where(column == winner_id)
        ).scalar_one()

        pk_cols = list(table.primary_key.columns)
        loser_rows = db.session.execute(
            select(*pk_cols, *key_cols).where(column == loser_id)
        ).all()

        for row in loser_rows:
            pk_values = row[: len(pk_cols)]
            key = tuple(row[len(pk_cols):])
            collides = key in existing if key_cols else winner_has_row > 0
            where = db.and_(*[c == v for c, v in zip(pk_cols, pk_values)])
            if collides:
                db.session.execute(delete(table).where(where))
                dropped += 1
            else:
                db.session.execute(update(table).where(where).values({column.name: winner_id}))
                if key_cols:
                    existing.add(key)
                else:
                    winner_has_row += 1
                moved += 1

    return moved, dropped


def merge_grade(grade: int, candidates: list[Class], *, dry_run: bool) -> bool:
    """Merge one grade's art/music classes. Returns True if anything changed."""
    target_name = f'Art/Music {grade_name_suffix(grade)}'
    winner = pick_winner(candidates)
    losers = [c for c in candidates if c.id != winner.id]
    counts = enrollment_counts([c.id for c in candidates])

    needs_rename = winner.name != target_name or winner.subject != ART_MUSIC_SUBJECT
    if not losers and not needs_rename:
        print(f'{grade_label(grade)}: already a single "{target_name}" class — nothing to do.')
        return False

    print(f'{grade_label(grade)}: keeping #{winner.id} "{winner.name}" as "{target_name}"')
    for loser in losers:
        print(
            f'  merging #{loser.id} "{loser.name}" ({loser.subject}, '
            f'{counts.get(loser.id, 0)} enrollments) into #{winner.id}'
        )
    if dry_run:
        return True

    total_moved = 0
    total_dropped = 0
    for loser in losers:
        moved, dropped = repoint_class_references(winner.id, loser.id)
        total_moved += moved
        total_dropped += dropped
        db.session.execute(delete(Class.__table__).where(Class.__table__.c.id == loser.id))

    db.session.execute(
        update(Class.__table__)
        .where(Class.__table__.c.id == winner.id)
        .values(name=target_name, subject=ART_MUSIC_SUBJECT, is_active=True)
    )
    if losers:
        print(f'  moved {total_moved} rows, dropped {total_dropped} duplicate rows')
    return True


def merge_art_music(grades: list[int], *, school_year_id: int | None, dry_run: bool) -> int:
    if school_year_id is None:
        active = SchoolYear.query.filter_by(is_active=True).first()
        if not active:
            print('No active school year — pass --school-year-id explicitly.')
            return 1
        school_year_id = active.id
        print(f'School year: {active.name} (id={active.id})')
    else:
        print(f'School year: id={school_year_id}')

    all_classes = Class.query.filter_by(school_year_id=school_year_id).all()
    art_music = [c for c in all_classes if is_art_music_class(c)]
    if not art_music:
        print('No Art or Music classes found.')
        return 0

    changed = False
    for grade in grades:
        candidates = [c for c in art_music if grade in (c.get_grade_levels() or [])]
        if not candidates:
            continue
        changed |= merge_grade(grade, candidates, dry_run=dry_run)

    unassigned = [c for c in art_music if not (c.get_grade_levels() or [])]
    for c in unassigned:
        print(f'Skipping #{c.id} "{c.name}" — no grade levels set; fix it and re-run.')

    if not changed:
        print('Nothing to merge.')
        return 0
    if dry_run:
        print('Dry run — no changes written.')
        return 0

    db.session.commit()
    db.session.expire_all()
    print('Done. Art and Music merged into one class per grade.')
    return 0


def parse_grades(raw: str) -> list[int]:
    grades: list[int] = []
    for chunk in raw.replace(' ', ',').split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        grades.append(0 if chunk.lower() == 'k' else int(chunk))
    if not grades:
        raise ValueError('No grades provided')
    return grades


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Merge separate Art and Music classes into one Art/Music class per grade.'
    )
    parser.add_argument(
        '--grades',
        default=','.join(str(g) for g in SETUP_GRADE_LEVELS),
        help='Comma-separated grades to merge (0 or K = Kindergarten)',
    )
    parser.add_argument(
        '--school-year-id',
        type=int,
        default=None,
        help='School year to operate on (default: the active school year)',
    )
    parser.add_argument('--dry-run', action='store_true', help='Show the plan without saving')
    args = parser.parse_args()

    with app.app_context():
        return merge_art_music(
            parse_grades(args.grades),
            school_year_id=args.school_year_id,
            dry_run=args.dry_run,
        )


if __name__ == '__main__':
    raise SystemExit(main())
