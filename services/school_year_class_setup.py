"""
Auto-create core (non-elective) classes for a school year.

Idempotent: skips classes that already exist for the same grade + subject area.
Each new class gets the primary teacher assigned per subject (with optional grade default).
"""

from __future__ import annotations

from flask import Request

from extensions import db
from models import Class, TeacherStaff
from utils.core_class_catalog import (
    SETUP_GRADE_LEVELS,
    all_catalog_entries,
    catalog_entries_for_grade,
    setup_key_for_entry,
)


def _normalize(text: str | None) -> str:
    return (text or '').strip().lower()


def teacher_assignment_key(grade_level: int, setup_key: str) -> str:
    return f'{int(grade_level)}:{setup_key}'


def parse_teacher_assignments_from_request(
    req: Request,
    grade_levels: list[int],
) -> dict[str, int]:
    """
    Read per-subject and per-grade-default teacher picks from the form.

    Field names: teacher_id_{grade}_{index}, grade_default_teacher_{grade}
    Subject index matches catalog_entries_for_grade order.
    """
    assignments: dict[str, int] = {}
    for g in grade_levels:
        grade_default = req.values.get(f'grade_default_teacher_{g}', type=int)
        for i, entry in enumerate(catalog_entries_for_grade(g)):
            tid = req.values.get(f'teacher_id_{g}_{i}', type=int)
            if not tid:
                tid = grade_default
            if tid:
                assignments[teacher_assignment_key(g, setup_key_for_entry(entry))] = tid
    return assignments


def _teacher_display_name(teacher_id: int | None, cache: dict[int, TeacherStaff]) -> str:
    if not teacher_id:
        return ''
    if teacher_id not in cache:
        cache[teacher_id] = TeacherStaff.query.get(teacher_id)
    t = cache[teacher_id]
    if not t or getattr(t, 'is_deleted', False):
        return ''
    return f'{t.first_name} {t.last_name}'.strip()


def _validate_teacher_assignments(
    to_create: list[dict],
    teacher_assignments: dict[str, int],
) -> list[str]:
    errors = []
    seen_staff: dict[int, TeacherStaff | None] = {}
    for row in to_create:
        key = teacher_assignment_key(row['grade_level'], row.get('setup_key') or row['subject'])
        tid = teacher_assignments.get(key)
        if not tid:
            errors.append(
                f'Assign a primary teacher for {row["name"]}.'
            )
            continue
        name = _teacher_display_name(tid, seen_staff)
        if not name:
            errors.append(
                f'Invalid or unavailable teacher for {row["name"]}.'
            )
    return errors


def _entry_matches_class(class_obj: Class, grade_level: int, entry: dict) -> bool:
    levels = class_obj.get_grade_levels() if hasattr(class_obj, 'get_grade_levels') else []
    if int(grade_level) not in (levels or []):
        return False
    haystack = f'{_normalize(class_obj.name)} {_normalize(class_obj.subject)}'
    tokens = entry.get('match_tokens') or (entry.get('subject', '').lower(),)
    return any(_normalize(tok) in haystack for tok in tokens if tok)


def _existing_for_school_year(school_year_id: int) -> list[Class]:
    return Class.query.filter_by(school_year_id=school_year_id).all()


def preview_core_class_setup(
    school_year_id: int,
    grade_levels: list[int] | None,
    teacher_assignments: dict[str, int] | None = None,
) -> dict:
    """
    Return what would be created vs skipped.
    {
      'to_create': [{grade_level, name, subject, teacher_id, teacher_name, ...}, ...],
      'skipped': [...],
      'errors': [str, ...],
    }
    """
    errors = []
    teacher_assignments = teacher_assignments or {}
    grades = [int(g) for g in (grade_levels or SETUP_GRADE_LEVELS) if str(g).isdigit() or isinstance(g, int)]
    if not grades:
        errors.append('Select at least one grade level.')
        return {'to_create': [], 'skipped': [], 'errors': errors}

    existing = _existing_for_school_year(school_year_id)
    to_create = []
    skipped = []
    staff_cache: dict[int, TeacherStaff] = {}

    for spec in all_catalog_entries(grades):
        g = spec['grade_level']
        entry = {
            'display_name': spec['display_name'],
            'subject': spec['subject'],
            'match_tokens': spec['match_tokens'],
        }
        match = None
        for c in existing:
            if _entry_matches_class(c, g, entry):
                match = c
                break
        if match:
            skipped.append({
                'grade_level': g,
                'grade_label': spec['grade_label'],
                'name': spec['suggested_name'],
                'subject': spec['subject'],
                'existing_class_id': match.id,
                'existing_class_name': match.name,
            })
        else:
            key = teacher_assignment_key(g, spec['setup_key'])
            tid = teacher_assignments.get(key)
            to_create.append({
                'grade_level': g,
                'grade_label': spec['grade_label'],
                'name': spec['suggested_name'],
                'subject': spec['subject'],
                'setup_key': spec['setup_key'],
                'teacher_id': tid,
                'teacher_name': _teacher_display_name(tid, staff_cache) or None,
            })

    if to_create:
        assignment_errors = _validate_teacher_assignments(to_create, teacher_assignments)
        errors.extend(assignment_errors)

    return {'to_create': to_create, 'skipped': skipped, 'errors': errors}


def run_core_class_setup(
    school_year_id: int,
    grade_levels: list[int] | None,
    teacher_assignments: dict[str, int],
) -> dict:
    """Create missing core classes with per-subject primary teachers."""
    preview = preview_core_class_setup(school_year_id, grade_levels, teacher_assignments)
    if preview['errors']:
        preview['created'] = []
        preview['created_count'] = 0
        return preview

    created = []
    for row in preview['to_create']:
        key = teacher_assignment_key(row['grade_level'], row.get('setup_key') or row['subject'])
        teacher_id = teacher_assignments.get(key)
        teacher = TeacherStaff.query.get(teacher_id)
        if not teacher:
            preview['errors'] = [f"Teacher not found for {row['name']}."]
            preview['created'] = []
            preview['created_count'] = 0
            db.session.rollback()
            return preview

        new_class = Class(
            name=row['name'],
            subject=row['subject'],
            teacher_id=teacher.id,
            school_year_id=school_year_id,
            term_type='full_year',
            is_active=True,
            description='Auto-created core class (School Year Class Setup).',
        )
        new_class.set_grade_levels([row['grade_level']])
        db.session.add(new_class)
        db.session.flush()
        created.append({
            'id': new_class.id,
            'name': new_class.name,
            'grade_level': row['grade_level'],
            'teacher_name': row.get('teacher_name') or f'{teacher.first_name} {teacher.last_name}',
        })

    if created:
        db.session.commit()
    else:
        db.session.rollback()

    preview['created'] = created
    preview['created_count'] = len(created)
    return preview
