"""
3rd grade standards checklist editor.

Provides a teacher-facing grid for entering Language Arts / Math standards
marks (M / W / NA / UA) per student, per standard, per quarter.

The same routes are also accessible to Directors and School Administrators
so they can view or edit the grid for any 3rd grade LA / Math class.
"""

from __future__ import annotations

from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from decorators import teacher_required
from models import (
    db,
    Class,
    Student,
    Enrollment,
    SchoolYear,
    Grade3StandardMark,
    class_additional_teachers,
    class_substitute_teachers,
)
from utils.report_card_grade3_standards import (
    SUBJECT_CATALOGS,
    QUARTER_COLUMNS,
    VALID_MARKS,
    flat_standards,
    get_marks_for_students,
    upsert_mark,
    copy_marks_from_previous_quarter,
    subject_for_standard,
    class_completeness,
    section_completeness,
)
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class, get_current_quarter


bp = Blueprint('grade3_standards', __name__)


# Class.subject text -> standards subject_key
_LA_TOKENS = ('language arts', 'language', 'reading', 'english', 'ela', 'literacy')
_MATH_TOKENS = ('math',)


def _class_subject_key(class_obj: Class) -> str | None:
    """Return 'language_arts' or 'math' (or None) based on the class subject text."""
    if not class_obj or not class_obj.subject:
        return None
    subject = class_obj.subject.lower()
    if any(t in subject for t in _MATH_TOKENS):
        return 'math'
    if any(t in subject for t in _LA_TOKENS):
        return 'language_arts'
    return None


def _is_third_grade_class(class_obj: Class) -> bool:
    """True if Class.grade_levels includes grade 3."""
    if not class_obj:
        return False
    try:
        levels = class_obj.get_grade_levels() or []
    except Exception:
        levels = []
    return 3 in [int(l) for l in levels if str(l).isdigit() or isinstance(l, int)]


def _active_school_year() -> SchoolYear | None:
    return SchoolYear.query.filter_by(is_active=True).first()


def _normalize_quarter(raw: str | None) -> str:
    """Return a clean 'Q1'..'Q4' string, defaulting to the current quarter."""
    if raw:
        candidate = raw.strip().upper()
        if candidate in QUARTER_COLUMNS:
            return candidate
    # Fall back to the active quarter from AcademicPeriod (returns '1'..'4'),
    # then format it as 'Qn'.
    try:
        num = get_current_quarter()
        if num and str(num).strip().isdigit():
            cand = f'Q{int(num)}'
            if cand in QUARTER_COLUMNS:
                return cand
    except Exception:
        pass
    return 'Q1'


def _classes_for_user(school_year_id: int):
    """Return the list of 3rd grade LA/Math classes the current user can edit."""
    base_q = Class.query.filter(
        Class.school_year_id == school_year_id,
        Class.is_active.is_(True),
    )

    if is_admin():
        candidates = base_q.all()
    else:
        teacher = get_teacher_or_admin()
        if not teacher:
            return []
        addl_ids = [r.class_id for r in db.session.query(class_additional_teachers).filter(
            class_additional_teachers.c.teacher_id == teacher.id
        ).all()]
        sub_ids = [r.class_id for r in db.session.query(class_substitute_teachers).filter(
            class_substitute_teachers.c.teacher_id == teacher.id
        ).all()]
        related_ids = set(addl_ids) | set(sub_ids)
        clauses = [Class.teacher_id == teacher.id]
        if related_ids:
            clauses.append(Class.id.in_(list(related_ids)))
        candidates = base_q.filter(or_(*clauses)).all()

    classes = []
    for c in candidates:
        if not _is_third_grade_class(c):
            continue
        if not _class_subject_key(c):
            continue
        classes.append(c)
    classes.sort(key=lambda c: (c.subject or '', c.name or ''))
    return classes


def _class_roster(class_obj: Class):
    """Return students enrolled in the class, sorted by name."""
    q = (
        db.session.query(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(
            Enrollment.class_id == class_obj.id,
            Enrollment.is_active.is_(True),
        )
        .distinct()
    )
    students = q.all()
    students.sort(key=lambda s: ((s.last_name or '').lower(), (s.first_name or '').lower()))
    return students


def _decorate_class(class_obj, subject_key, school_year_id):
    """Attach completeness stats + roster size to a class object for templates."""
    students = _class_roster(class_obj)
    stats = class_completeness([s.id for s in students], school_year_id, subject_key)
    class_obj.g3_stats = stats
    class_obj.g3_subject_key = subject_key
    class_obj.g3_student_count = len(students)
    return class_obj


@bp.route('/grade3-standards', methods=['GET'])
@login_required
@teacher_required
def grade3_standards_index():
    """Landing page: pick a class to edit."""
    from utils.spa_management_urls import user_should_use_spa_management_shell

    if user_should_use_spa_management_shell() and request.args.get('legacy') != '1':
        return redirect('/app/management/report-cards/standards/grade3')

    school_year = _active_school_year()
    if not school_year:
        flash('No active school year is configured.', 'warning')
        return redirect(url_for('teacher.dashboard.my_classes'))

    classes = _classes_for_user(school_year.id)
    grouped = {'language_arts': [], 'math': []}
    for c in classes:
        key = _class_subject_key(c)
        if key in grouped:
            grouped[key].append(_decorate_class(c, key, school_year.id))

    # Aggregate stats for the hero insight strip.
    total_classes = len(classes)
    total_students = sum(c.g3_student_count for c in classes)
    overall_filled = sum(c.g3_stats['overall']['filled'] for c in classes)
    overall_total = sum(c.g3_stats['overall']['total'] for c in classes)
    overall_percent = int(round(100 * overall_filled / overall_total)) if overall_total else 0
    current_quarter = _normalize_quarter(None)

    return render_template(
        'teachers/grade3_standards_index.html',
        school_year=school_year,
        la_classes=grouped['language_arts'],
        math_classes=grouped['math'],
        current_quarter=current_quarter,
        quarter_columns=QUARTER_COLUMNS,
        total_classes=total_classes,
        total_students=total_students,
        overall_percent=overall_percent,
        overall_filled=overall_filled,
        overall_total=overall_total,
        is_admin=is_admin(),
    )


@bp.route('/grade3-standards/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade3_standards_editor(class_id: int):
    """Edit standards marks for a class + quarter."""
    from utils.spa_management_urls import user_should_use_spa_management_shell

    if (
        request.method == 'GET'
        and user_should_use_spa_management_shell()
        and request.args.get('legacy') != '1'
    ):
        quarter = request.args.get('quarter', '')
        view = request.args.get('view', 'grid')
        student_id = request.args.get('student_id', '')
        path = f'/app/management/report-cards/standards/grade3/{class_id}'
        params = []
        if quarter:
            params.append(f'quarter={quarter}')
        if view:
            params.append(f'view={view}')
        if student_id:
            params.append(f'student_id={student_id}')
        if params:
            path = f'{path}?{"&".join(params)}'
        return redirect(path)

    class_obj = Class.query.get_or_404(class_id)
    if not is_authorized_for_class(class_obj):
        abort(403)
    if not _is_third_grade_class(class_obj):
        flash('This is not a 3rd grade class.', 'warning')
        return redirect(url_for('teacher.grade3_standards.grade3_standards_index'))

    subject_key = _class_subject_key(class_obj)
    if not subject_key:
        flash(
            'This class subject is not Language Arts or Math, '
            'so it cannot use the 3rd grade standards checklist.',
            'warning',
        )
        return redirect(url_for('teacher.grade3_standards.grade3_standards_index'))

    school_year = class_obj.school_year or _active_school_year()
    if not school_year:
        flash('No active school year is configured.', 'warning')
        return redirect(url_for('teacher.grade3_standards.grade3_standards_index'))

    quarter = _normalize_quarter(request.values.get('quarter'))
    students = _class_roster(class_obj)
    standards = flat_standards(subject_key)

    if request.method == 'POST':
        bulk_action = (request.form.get('bulk_action') or '').strip()
        student_ids = [s.id for s in students]
        actor_user_id = getattr(current_user, 'id', None)

        if bulk_action == 'copy_previous':
            copied = copy_marks_from_previous_quarter(
                student_ids, school_year.id, subject_key, quarter,
                user_id=actor_user_id,
            )
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                flash('Could not copy marks from the previous quarter.', 'danger')
            else:
                if copied:
                    flash(f'Copied {copied} mark(s) from the previous quarter into {quarter}.', 'success')
                else:
                    flash('No new marks were copied (target cells were already filled or empty in previous quarter).', 'info')
            return redirect(url_for('teacher.grade3_standards.grade3_standards_editor', class_id=class_id, quarter=quarter))

        if bulk_action in ('mark_all_m', 'mark_all_w', 'mark_all_na', 'mark_all_ua'):
            mark_value = bulk_action.split('_')[-1].upper()
            changed = 0
            for sid in student_ids:
                for std in standards:
                    if upsert_mark(sid, std['id'], school_year.id, quarter, mark_value, user_id=actor_user_id):
                        changed += 1
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                flash('Could not apply the bulk mark.', 'danger')
            else:
                flash(f'Set {changed} cell(s) to {mark_value} for {quarter}.', 'success')
            return redirect(url_for('teacher.grade3_standards.grade3_standards_editor', class_id=class_id, quarter=quarter))

        if bulk_action == 'clear_all':
            removed = 0
            for sid in student_ids:
                for std in standards:
                    if upsert_mark(sid, std['id'], school_year.id, quarter, '', user_id=actor_user_id):
                        removed += 1
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                flash('Could not clear marks.', 'danger')
            else:
                flash(f'Cleared {removed} mark(s) for {quarter}.', 'success')
            return redirect(url_for('teacher.grade3_standards.grade3_standards_editor', class_id=class_id, quarter=quarter))

        # Default: save all per-cell selects from the form. We accept two
        # field-name formats:
        #   mark__<student_id>__<standard_id>           -> writes to ``quarter``
        #   markq__<student_id>__<standard_id>__<Qn>    -> writes to <Qn>
        # The "markq" form is used by the per-student view which edits all 4
        # quarters at once.
        student_id_set = set(student_ids)
        standard_id_set = {s['id'] for s in standards}
        changed = 0
        for key, value in request.form.items():
            if key.startswith('markq__'):
                parts = key.split('__')
                if len(parts) != 4:
                    continue
                try:
                    sid = int(parts[1])
                except (TypeError, ValueError):
                    continue
                std_id = parts[2]
                target_q = parts[3]
                if sid not in student_id_set or std_id not in standard_id_set:
                    continue
                if target_q not in QUARTER_COLUMNS:
                    continue
                mark_value = (value or '').strip().upper()
                if mark_value and mark_value not in VALID_MARKS:
                    continue
                if upsert_mark(sid, std_id, school_year.id, target_q, mark_value, user_id=actor_user_id):
                    changed += 1
            elif key.startswith('mark__'):
                parts = key.split('__')
                if len(parts) != 3:
                    continue
                try:
                    sid = int(parts[1])
                except (TypeError, ValueError):
                    continue
                std_id = parts[2]
                if sid not in student_id_set or std_id not in standard_id_set:
                    continue
                mark_value = (value or '').strip().upper()
                if mark_value and mark_value not in VALID_MARKS:
                    continue
                if upsert_mark(sid, std_id, school_year.id, quarter, mark_value, user_id=actor_user_id):
                    changed += 1

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Could not save standards marks. Please try again.', 'danger')
        else:
            if changed:
                flash(f'Saved {changed} change(s).', 'success')
            else:
                flash('No changes to save.', 'info')
        # Preserve view mode + student selection on redirect.
        view_for_redirect = (request.values.get('view') or 'grid').strip().lower()
        if view_for_redirect not in ('grid', 'student'):
            view_for_redirect = 'grid'
        student_id_for_redirect = request.values.get('student_id', type=int)
        return redirect(url_for(
            'teacher.grade3_standards.grade3_standards_editor',
            class_id=class_id,
            quarter=quarter,
            view=view_for_redirect,
            student_id=student_id_for_redirect if view_for_redirect == 'student' else None,
        ))

    # GET: build the grid.
    student_ids = [s.id for s in students]
    marks_by_student = get_marks_for_students(
        student_ids,
        school_year.id,
        subject_key=subject_key,
    )

    # Per-cell value for the chosen quarter (used by the grid view).
    marks_grid = {}
    for sid in student_ids:
        per_std = marks_by_student.get(sid, {})
        grid_row = {}
        for std in standards:
            grid_row[std['id']] = (per_std.get(std['id']) or {}).get(quarter, '')
        marks_grid[sid] = grid_row

    # Full per-student × quarter map (used by the per-student view).
    marks_student_view = {}
    for sid in student_ids:
        per_std = marks_by_student.get(sid, {})
        student_block = {}
        for std in standards:
            row = {}
            for q in QUARTER_COLUMNS:
                row[q] = (per_std.get(std['id']) or {}).get(q, '')
            student_block[std['id']] = row
        marks_student_view[sid] = student_block

    # View mode + selected student for per-student view.
    view_mode = (request.values.get('view') or 'grid').strip().lower()
    if view_mode not in ('grid', 'student'):
        view_mode = 'grid'
    selected_student_id = request.values.get('student_id', type=int)
    if view_mode == 'student' and selected_student_id not in student_ids:
        selected_student_id = student_ids[0] if student_ids else None

    # Stats for header insights + section progress.
    overall_stats = class_completeness(student_ids, school_year.id, subject_key)
    section_stats = section_completeness(student_ids, school_year.id, subject_key, quarter)

    other_classes = _classes_for_user(school_year.id)

    return render_template(
        'teachers/grade3_standards_editor.html',
        class_obj=class_obj,
        subject_key=subject_key,
        subject_catalog=SUBJECT_CATALOGS[subject_key],
        students=students,
        standards=standards,
        marks_grid=marks_grid,
        marks_student_view=marks_student_view,
        quarter=quarter,
        quarter_columns=QUARTER_COLUMNS,
        valid_marks=VALID_MARKS,
        school_year=school_year,
        other_classes=other_classes,
        can_copy_previous=quarter != 'Q1',
        view_mode=view_mode,
        selected_student_id=selected_student_id,
        overall_stats=overall_stats,
        section_stats=section_stats,
        is_admin=is_admin(),
    )
