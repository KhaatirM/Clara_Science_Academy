"""
Auto-create core (non-elective) classes for a school year.

Idempotent: skips classes that already exist for the same grade + subject area.
Each new class gets the primary teacher assigned per subject (with optional grade default).
"""

from __future__ import annotations

from flask import Request

from extensions import db
from models import Class, Enrollment, SchoolYear, Student, TeacherStaff
from utils.core_class_catalog import (
    SETUP_GRADE_LEVELS,
    all_catalog_entries,
    catalog_entries_for_grade,
    is_elective_subject,
    setup_key_for_entry,
)
from utils.student_roster import active_roster_student_filters, student_is_archived


def _normalize(text: str | None) -> str:
    return (text or '').strip().lower()


def _inferred_grade_from_class_name(name: str | None) -> int | None:
    """
    Best-effort grade from names like "Art 6", "Art 6th", "Language Arts 7".
    Used when Class.grade_levels is empty so remaps still work.
    """
    import re

    text = (name or '').strip().lower()
    if not text:
        return None
    # Prefer an explicit trailing grade token.
    patterns = (
        r'(?:^|[\s\-\[(])k(?:indergarten)?(?:[\s\-\])]|$)',
        r'(?:^|[\s\-\[(])(\d{1,2})(?:st|nd|rd|th)?(?:\s*grade)?(?:[\s\-\])]|$)',
    )
    if re.search(patterns[0], text):
        return 0
    matches = list(re.finditer(patterns[1], text))
    if not matches:
        return None
    try:
        grade = int(matches[-1].group(1))
    except (TypeError, ValueError):
        return None
    if 0 <= grade <= 12:
        return grade
    return None


def _class_grade_levels(class_obj: Class) -> list[int]:
    levels = class_obj.get_grade_levels() if hasattr(class_obj, 'get_grade_levels') else []
    if levels:
        return [int(g) for g in levels]
    inferred = _inferred_grade_from_class_name(getattr(class_obj, 'name', None))
    return [inferred] if inferred is not None else []


def _entry_matches_class(class_obj: Class, grade_level: int, entry: dict) -> bool:
    levels = _class_grade_levels(class_obj)
    if int(grade_level) not in (levels or []):
        return False
    subject = _normalize(getattr(class_obj, 'subject', None))
    entry_subject = _normalize(entry.get('subject'))
    if entry_subject and subject == entry_subject:
        return True
    haystack = f'{_normalize(class_obj.name)} {subject}'
    tokens = entry.get('match_tokens') or (entry.get('subject', '').lower(),)
    return any(_normalize(tok) in haystack for tok in tokens if tok)


def _deactivate_enrollment(enr: Enrollment, out_list: list[dict]) -> None:
    enr.is_active = False
    if hasattr(enr, 'dropped_at') and enr.dropped_at is None:
        from datetime import datetime, timezone

        enr.dropped_at = datetime.now(timezone.utc)
    cls = db.session.get(Class, enr.class_id)
    out_list.append(
        {
            'class_id': enr.class_id,
            'class_name': getattr(cls, 'name', None),
        }
    )


def _should_drop_enrollment_for_grade_change(
    class_obj: Class | None,
    *,
    old_grade: int,
    new_grade: int,
) -> bool:
    """
    Drop grade-banded classes that belong to the old grade but not the new one.

    Keeps true electives (islamic/quran/arabic) and multi-grade bands that still
    include the new grade.
    """
    if class_obj is None:
        return False
    if is_elective_subject(getattr(class_obj, 'subject', None)):
        return False
    levels = _class_grade_levels(class_obj)
    if not levels:
        return False
    if new_grade in levels:
        return False
    return old_grade in levels


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


def _class_ids_for_setup(preview: dict) -> list[int]:
    """Class IDs touched by a core setup run (newly created + already-existing skipped)."""
    ids: list[int] = []
    for row in preview.get('created') or []:
        cid = row.get('id')
        if cid:
            ids.append(int(cid))
    for row in preview.get('skipped') or []:
        cid = row.get('existing_class_id')
        if cid:
            ids.append(int(cid))
    seen: set[int] = set()
    out: list[int] = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def auto_enroll_students_by_grade(class_ids: list[int], school_year_id: int) -> dict:
    """
    Enroll active students whose grade level matches each class's grade band.
    Idempotent: skips students already enrolled in the class.
    """
    enrolled_count = 0
    by_class: list[dict] = []

    for class_id in class_ids:
        class_obj = Class.query.get(class_id)
        if not class_obj or class_obj.school_year_id != school_year_id:
            continue
        grade_levels = class_obj.get_grade_levels() or []
        if not grade_levels:
            continue

        students = (
            Student.query.filter(
                Student.grade_level.in_(grade_levels),
                active_roster_student_filters(),
            ).all()
        )
        added = 0
        for student in students:
            if student.grade_level is None:
                continue
            exists = Enrollment.query.filter_by(
                class_id=class_id,
                student_id=student.id,
                is_active=True,
            ).first()
            if exists:
                continue
            db.session.add(
                Enrollment(student_id=student.id, class_id=class_id, is_active=True)
            )
            added += 1

        if added:
            enrolled_count += added
            by_class.append(
                {
                    'class_id': class_id,
                    'class_name': class_obj.name,
                    'enrolled': added,
                }
            )

    if enrolled_count:
        db.session.commit()

    return {'enrolled_count': enrolled_count, 'by_class': by_class}


def _core_class_ids_for_grade(school_year_id: int, grade_level: int) -> set[int]:
    """Active-year class IDs that match the core catalog for ``grade_level``."""
    from utils.core_class_catalog import all_catalog_entries

    grade = int(grade_level)
    existing = (
        Class.query.filter_by(school_year_id=school_year_id, is_active=True).all()
    )
    ids: set[int] = set()
    for spec in all_catalog_entries([grade]):
        entry = {
            'subject': spec['subject'],
            'match_tokens': spec['match_tokens'],
        }
        for c in existing:
            if _entry_matches_class(c, grade, entry):
                ids.add(int(c.id))
                break
    return ids


def class_is_core_catalog_class(class_obj: Class | None) -> bool:
    """
    True when ``class_obj`` matches a School Year Class Setup core catalog row
    (Language Arts, Math, Science, History/Social Studies, Art/Music, PE, etc.).

    Electives and manually added classes (e.g. Programming) return False.
    """
    if class_obj is None:
        return False
    if is_elective_subject(getattr(class_obj, 'subject', None)):
        return False
    levels = _class_grade_levels(class_obj)
    if not levels:
        return False
    for grade in levels:
        for spec in catalog_entries_for_grade(int(grade)):
            entry = {
                'subject': spec['subject'],
                'match_tokens': spec['match_tokens'],
            }
            if _entry_matches_class(class_obj, int(grade), entry):
                return True
    return False


def resync_student_core_enrollments_for_grade_change(
    student: Student,
    *,
    old_grade: int | None,
    new_grade: int | None,
    school_year_id: int | None = None,
) -> dict:
    """
    When a student's grade changes mid-year, move them between grade-banded classes.

    - Drops active enrollments in old-grade classes (catalog cores + any other
      grade-banded class that does not include the new grade)
    - Leaves true electives (islamic/quran/arabic) alone
    - Enrolls into matching core classes for the new grade in the active school year
    - Does not create missing classes; reports catalog rows with no matching Class
    - Does NOT schedule Google sync (caller must do that AFTER commit via
      ``touched_class_ids``)

    Caller commits.
    """
    out = {
        'dropped': [],
        'enrolled': [],
        'missing_classes': [],
        'touched_class_ids': [],
        'skipped': False,
        'reason': None,
    }
    if student is None or student_is_archived(student):
        out['skipped'] = True
        out['reason'] = 'missing_or_deleted_student'
        return out
    if old_grade is None or new_grade is None:
        out['skipped'] = True
        out['reason'] = 'grade_missing'
        return out
    try:
        old_g = int(old_grade)
        new_g = int(new_grade)
    except (TypeError, ValueError):
        out['skipped'] = True
        out['reason'] = 'grade_invalid'
        return out
    if old_g == new_g:
        out['skipped'] = True
        out['reason'] = 'unchanged'
        return out

    if school_year_id is None:
        year = SchoolYear.query.filter_by(is_active=True).first()
        school_year_id = year.id if year else None
    if not school_year_id:
        out['skipped'] = True
        out['reason'] = 'no_active_school_year'
        return out

    old_core_ids = _core_class_ids_for_grade(school_year_id, old_g)
    new_core_ids = _core_class_ids_for_grade(school_year_id, new_g)

    from utils.core_class_catalog import class_name_for_grade, catalog_entries_for_grade

    # Report catalog rows that have no Class yet for the new grade.
    existing = Class.query.filter_by(school_year_id=school_year_id, is_active=True).all()
    for entry in catalog_entries_for_grade(new_g):
        matched = any(_entry_matches_class(c, new_g, entry) for c in existing)
        if not matched:
            out['missing_classes'].append(class_name_for_grade(new_g, entry))

    already_dropped: set[int] = set()

    # 1) Drop catalog-matched old-grade cores that are not also new-grade cores.
    to_drop = old_core_ids - new_core_ids
    if to_drop:
        enrollments = (
            Enrollment.query.filter(
                Enrollment.student_id == student.id,
                Enrollment.class_id.in_(list(to_drop)),
                Enrollment.is_active.is_(True),
            ).all()
        )
        for enr in enrollments:
            _deactivate_enrollment(enr, out['dropped'])
            already_dropped.add(int(enr.class_id))

    # 2) Sweep ALL active enrollments in this school year: drop any grade-banded
    # class that belongs to the old grade but not the new one (covers Art/PE/Music
    # when grade_levels or naming prevented catalog matching).
    active_enrollments = (
        Enrollment.query.filter_by(student_id=student.id, is_active=True).all()
    )
    for enr in active_enrollments:
        if int(enr.class_id) in already_dropped:
            continue
        cls = db.session.get(Class, enr.class_id)
        if cls is None:
            continue
        if getattr(cls, 'school_year_id', None) != school_year_id:
            continue
        if not _should_drop_enrollment_for_grade_change(cls, old_grade=old_g, new_grade=new_g):
            continue
        _deactivate_enrollment(enr, out['dropped'])
        already_dropped.add(int(enr.class_id))

    # Enroll into new-grade core classes.
    for class_id in sorted(new_core_ids):
        exists = Enrollment.query.filter_by(
            student_id=student.id,
            class_id=class_id,
            is_active=True,
        ).first()
        if exists:
            continue
        # Reactivate a prior inactive row if present.
        prior = Enrollment.query.filter_by(
            student_id=student.id,
            class_id=class_id,
        ).first()
        if prior:
            prior.is_active = True
            if hasattr(prior, 'dropped_at'):
                prior.dropped_at = None
        else:
            db.session.add(
                Enrollment(student_id=student.id, class_id=class_id, is_active=True)
            )
        cls = db.session.get(Class, class_id)
        out['enrolled'].append(
            {
                'class_id': class_id,
                'class_name': getattr(cls, 'name', None),
            }
        )

    # Keep StudentSchoolYear in sync when present.
    try:
        from utils.report_card_school_year import upsert_student_school_year

        upsert_student_school_year(student.id, school_year_id, new_g, enrolled=True)
    except Exception:
        pass

    # Caller schedules Google sync AFTER commit using these IDs.
    touched = {int(row['class_id']) for row in out['dropped'] + out['enrolled'] if row.get('class_id')}
    out['touched_class_ids'] = sorted(touched)

    return out


def _all_core_class_ids_for_year(school_year_id: int) -> set[int]:
    from utils.core_class_catalog import SETUP_GRADE_LEVELS

    ids: set[int] = set()
    for g in SETUP_GRADE_LEVELS:
        ids |= _core_class_ids_for_grade(school_year_id, g)
    return ids


def align_student_core_enrollments_to_current_grade(
    student: Student,
    *,
    school_year_id: int | None = None,
) -> dict:
    """
    Ensure the student is only in core classes for their *current* grade.

    - Enrolls missing current-grade core classes
    - Drops active enrollments in other-grade core classes
    - Leaves electives / non-catalog classes alone

    Caller commits.
    """
    out = {
        'dropped': [],
        'enrolled': [],
        'missing_classes': [],
        'skipped': False,
        'reason': None,
    }
    if student is None or student_is_archived(student):
        out['skipped'] = True
        out['reason'] = 'missing_or_deleted_student'
        return out
    if student.grade_level is None:
        out['skipped'] = True
        out['reason'] = 'grade_missing'
        return out

    if school_year_id is None:
        year = SchoolYear.query.filter_by(is_active=True).first()
        school_year_id = year.id if year else None
    if not school_year_id:
        out['skipped'] = True
        out['reason'] = 'no_active_school_year'
        return out

    grade = int(student.grade_level)
    desired = _core_class_ids_for_grade(school_year_id, grade)
    all_core = _all_core_class_ids_for_year(school_year_id)

    from utils.core_class_catalog import class_name_for_grade, catalog_entries_for_grade

    existing = Class.query.filter_by(school_year_id=school_year_id, is_active=True).all()
    for entry in catalog_entries_for_grade(grade):
        if not any(_entry_matches_class(c, grade, entry) for c in existing):
            out['missing_classes'].append(class_name_for_grade(grade, entry))

    wrong = all_core - desired
    if wrong:
        enrollments = (
            Enrollment.query.filter(
                Enrollment.student_id == student.id,
                Enrollment.class_id.in_(list(wrong)),
                Enrollment.is_active.is_(True),
            ).all()
        )
        for enr in enrollments:
            _deactivate_enrollment(enr, out['dropped'])

    # Also drop leftover grade-banded enrollments that failed catalog matching
    # (e.g. Art with empty grade_levels or odd naming).
    already_dropped = {int(row['class_id']) for row in out['dropped'] if row.get('class_id')}
    for enr in Enrollment.query.filter_by(student_id=student.id, is_active=True).all():
        if int(enr.class_id) in already_dropped or int(enr.class_id) in desired:
            continue
        cls = db.session.get(Class, enr.class_id)
        if cls is None or getattr(cls, 'school_year_id', None) != school_year_id:
            continue
        if is_elective_subject(getattr(cls, 'subject', None)):
            continue
        levels = _class_grade_levels(cls)
        if not levels:
            continue
        if grade in levels:
            continue
        # Class is grade-banded to some other grade(s) only → drop.
        _deactivate_enrollment(enr, out['dropped'])
        already_dropped.add(int(enr.class_id))

    for class_id in sorted(desired):
        exists = Enrollment.query.filter_by(
            student_id=student.id,
            class_id=class_id,
            is_active=True,
        ).first()
        if exists:
            continue
        prior = Enrollment.query.filter_by(
            student_id=student.id,
            class_id=class_id,
        ).first()
        if prior:
            prior.is_active = True
            if hasattr(prior, 'dropped_at'):
                prior.dropped_at = None
        else:
            db.session.add(
                Enrollment(student_id=student.id, class_id=class_id, is_active=True)
            )
        cls = db.session.get(Class, class_id)
        out['enrolled'].append(
            {'class_id': class_id, 'class_name': getattr(cls, 'name', None)}
        )

    return out


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

    preview['created'] = created
    preview['created_count'] = len(created)

    class_ids = _class_ids_for_setup(preview)
    enrollment = auto_enroll_students_by_grade(class_ids, school_year_id)
    preview['enrollment'] = enrollment

    from services.class_google_group import (
        class_ids_needing_google_classroom,
        schedule_try_provision_class_google_groups,
    )

    # Prefer classes still missing Classroom (e.g. after a prior timeout), then the
    # rest of this setup run. try_provision no-ops K–2 via class_needs_google_integration.
    missing_ids = class_ids_needing_google_classroom(school_year_id)
    queued: list[int] = []
    seen: set[int] = set()
    for cid in missing_ids + class_ids:
        if cid in seen:
            continue
        seen.add(cid)
        queued.append(cid)
    schedule_try_provision_class_google_groups(queued)
    preview["google_provision_queued"] = len(queued)
    preview["google_provision_missing"] = len(missing_ids)

    if not created and not enrollment.get('enrolled_count'):
        db.session.rollback()

    return preview
