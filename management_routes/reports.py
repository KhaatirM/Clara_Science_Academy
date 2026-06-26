"""
Reports routes for management users.
"""

import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import admin_required, management_required, permissions_required
from models import db, ReportCard, SchoolYear, Class, Student, Enrollment
from utils.report_card_portal import (
    approve_report_card_for_parents,
    count_pending_parent_approval,
    is_official_report_card,
    report_card_report_type,
    revoke_report_card_parent_access,
)
from utils.report_card_school_year import (
    enrollment_must_be_active_for_report_card,
    grade_display as report_card_grade_display,
    grade_level_for_school_year,
    record_student_school_year_grade,
)
from utils.user_roles import canonical_role_label
from utils.report_card_warnings import (
    report_card_unfinalized_banner_message,
    report_card_warnings_template_context,
)


bp = Blueprint('reports', __name__)

# Grade-band categories for report card navigation (0 = Kindergarten)
REPORT_CARD_CATEGORIES = {
    'elementary': {
        'name': 'Elementary School (K–5th)',
        'grades': [0, 1, 2, 3, 4, 5],
        'icon': 'pencil-square',
        'color': 'primary',
    },
    '6-8': {
        'name': 'Middle School (6th–8th)',
        'grades': [6, 7, 8],
        'icon': 'mortarboard',
        'color': 'warning',
    },
    '9-12': {
        'name': 'High School (9th–12th)',
        'grades': [9, 10, 11, 12],
        'icon': 'building',
        'color': 'info',
    },
}

# Legacy category slugs → current slug
REPORT_CARD_CATEGORY_ALIASES = {
    'k-2': 'elementary',
    '3-5': 'elementary',
}


def _resolve_report_card_category(category):
    """Map URL slug to a defined report card category key."""
    return REPORT_CARD_CATEGORY_ALIASES.get(category, category)


def _as_date(value):
    """Convert datetime/date/str to date, best-effort."""
    if value is None:
        return None
    from datetime import datetime as _dt, date as _date
    if isinstance(value, _date) and not isinstance(value, _dt):
        return value
    if isinstance(value, _dt):
        return value.date()
    if isinstance(value, str):
        # Try common formats
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d'):
            try:
                return _dt.strptime(value.strip(), fmt).date()
            except Exception:
                continue
    return None


def _grade3_pdf_extras(student, school_year_id, selected_quarters, class_objects, grades, include_attendance,
                       report_card_data=None):
    """Context variables for 3rd grade progress report (director page-1 layout)."""
    if not student or getattr(student, 'grade_level', None) != 3:
        return {}
    from utils.report_card_grade3 import grade3_full_template_context
    sid = student.id if hasattr(student, 'id') else student
    return grade3_full_template_context(
        sid,
        school_year_id,
        selected_quarters,
        class_objects,
        grades,
        include_attendance=include_attendance,
        report_card_data=report_card_data,
    )


def _grade1_pdf_extras(student, school_year_id, selected_quarters, class_objects, grades, include_attendance,
                       report_card_data=None):
    """Context variables for 1st grade progress report (director page-1 layout)."""
    if not student or getattr(student, 'grade_level', None) != 1:
        return {}
    from utils.report_card_grade1 import grade1_full_template_context
    sid = student.id if hasattr(student, 'id') else student
    return grade1_full_template_context(
        sid,
        school_year_id,
        selected_quarters,
        class_objects,
        grades,
        include_attendance=include_attendance,
        report_card_data=report_card_data,
    )


def _elementary_pdf_extras(student, school_year_id, selected_quarters, class_objects, grades, include_attendance,
                           report_card_data=None):
    """Merge grade-specific PDF context (1st and 3rd grade)."""
    ctx = {}
    ctx.update(_grade1_pdf_extras(
        student, school_year_id, selected_quarters, class_objects, grades,
        include_attendance, report_card_data,
    ))
    ctx.update(_grade3_pdf_extras(
        student, school_year_id, selected_quarters, class_objects, grades,
        include_attendance, report_card_data,
    ))
    return ctx


def _report_card_template_name(grade_level, template_prefix):
    """Pick the PDF template for a student's grade level."""
    if grade_level == 1:
        return f'management/{template_prefix}_report_card_pdf_template_1.html'
    if grade_level == 2:
        return f'management/{template_prefix}_report_card_pdf_template_1_2.html'
    if grade_level == 0:
        return f'management/{template_prefix}_report_card_pdf_template_1_2.html'
    if grade_level == 3:
        return f'management/{template_prefix}_report_card_pdf_template_3.html'
    return f'management/{template_prefix}_report_card_pdf_template_4_8.html'


def _selected_quarters_date_window(school_year_id, quarters_clean):
    """
    Return (start_date, end_date) for the union window of selected quarters.
    Uses AcademicPeriod quarter records; falls back to SchoolYear bounds if missing.
    """
    from models import AcademicPeriod, SchoolYear

    periods = AcademicPeriod.query.filter_by(
        school_year_id=school_year_id,
        period_type='quarter',
    ).filter(AcademicPeriod.name.in_(quarters_clean)).all()
    if periods:
        start = min(p.start_date for p in periods if p and p.start_date)
        end = max(p.end_date for p in periods if p and p.end_date)
        return start, end

    sy = SchoolYear.query.get(school_year_id)
    if sy:
        return sy.start_date, sy.end_date
    return None, None


def _enrollment_overlaps_window(enrollment, window_start, window_end):
    """
    True if enrollment overlaps [window_start, window_end] (dates).

    For currently-active enrollments, a null ``dropped_at`` means "still enrolled",
    so we treat it as open-ended through ``window_end``.

    For inactive enrollments, a null ``dropped_at`` historically meant the
    enrollment was marked inactive without recording when. We must NOT pretend
    those span the whole window — that would let stale enrollments leak into
    forms and report cards. We treat the drop date as equal to ``enrolled_at``
    (or far in the past if neither is set), which excludes them from any future
    window they were never actually active in.
    """
    if not window_start or not window_end:
        return False
    enrolled_at = _as_date(getattr(enrollment, 'enrolled_at', None))
    raw_dropped = _as_date(getattr(enrollment, 'dropped_at', None))
    is_active = getattr(enrollment, 'is_active', True)

    if raw_dropped is None:
        if is_active:
            dropped_at = window_end
        else:
            # Inactive + no recorded drop date -> collapse the enrollment to a
            # point in time so overlap only matches if enrolled_at falls inside
            # the window. Avoids leaking dropped enrollments through.
            dropped_at = enrolled_at if enrolled_at is not None else (window_start - timedelta(days=1))
    else:
        dropped_at = raw_dropped

    if enrolled_at is None:
        enrolled_at = window_start  # unknown start: assume on/before window
    return enrolled_at <= window_end and dropped_at >= window_start


def _enrollment_eligible_for_report_card(enrollment, window_start, window_end):
    """
    Whether a class enrollment should be offered on the report card form / PDF.

    Active enrollments are always included so newly created classes and late
    roster adds still appear even when ``enrolled_at`` falls after the selected
    quarter window (e.g. class created after Q4 end date). Inactive enrollments
    still require date overlap with the selected period.
    """
    if getattr(enrollment, 'is_active', True):
        return True
    if not window_start or not window_end:
        return True
    return _enrollment_overlaps_window(enrollment, window_start, window_end)


@bp.route('/api/report-card/comments')
@login_required
@permissions_required('report_cards:generate')
def api_report_card_comments():
    """
    Return existing saved comments for a student/classes (single comment per class) so management can prefill overrides.
    """
    from models import ReportCardComment

    try:
        student_id = request.args.get('student_id', type=int)
        school_year_id = request.args.get('school_year_id', type=int)
        class_ids = [int(x) for x in request.args.getlist('class_ids') if str(x).isdigit()]

        if not student_id or not school_year_id or not class_ids:
            return jsonify({'success': False, 'message': 'Missing required parameters'}), 400

        class_map = {}
        for c in Class.query.filter(Class.id.in_(class_ids)).all():
            class_map[str(c.id)] = c.name

        comments = ReportCardComment.query.filter(
            ReportCardComment.student_id == student_id,
            ReportCardComment.school_year_id == school_year_id,
            ReportCardComment.quarter == 'ALL',
            ReportCardComment.class_id.in_(class_ids),
        ).all()

        by_class = {}
        for row in comments:
            by_class[str(row.class_id)] = row.comment_text or ''

        return jsonify({
            'success': True,
            'class_map': class_map,
            'comments_by_class': by_class,
        })
    except Exception as e:
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise
        current_app.logger.exception('api_report_card_comments failed')
        return jsonify({'success': False, 'message': 'Error loading comments'}), 500


def _build_entrance_school_year_options(start_year=2020):
    """Return school-year labels from current year back to start_year."""
    today = datetime.utcnow()
    current_start_year = today.year if today.month >= 7 else today.year - 1
    return [f"{year}-{year + 1}" for year in range(current_start_year, start_year - 1, -1)]


def _is_valid_school_year_label(value):
    """Validate 'YYYY-YYYY' format where second year = first + 1."""
    if not value or not isinstance(value, str):
        return False
    raw = value.strip()
    if len(raw) != 9 or raw[4] != '-':
        return False
    left, right = raw.split('-', 1)
    if not (left.isdigit() and right.isdigit()):
        return False
    return int(right) == int(left) + 1


def _calculate_expected_grad_from_student(student):
    """Estimate expected graduation month/year from grade and entrance year."""
    entrance = getattr(student, 'entrance_date', None)
    grade_level = getattr(student, 'grade_level', None)
    if grade_level is None or not _is_valid_school_year_label(entrance):
        return getattr(student, 'expected_grad_date', None) or None
    try:
        start_year = int(str(entrance).split('-', 1)[0])
        years_to_graduation = 12 - int(grade_level)
        if years_to_graduation < 0:
            years_to_graduation = 0
        return f"06/{start_year + years_to_graduation}"
    except (TypeError, ValueError):
        return getattr(student, 'expected_grad_date', None) or None


def _try_class_id_key(key):
    """Parse a JSON/dict key as a class id when possible."""
    if key is None:
        return None
    if isinstance(key, int):
        return key
    if isinstance(key, str) and key.isdigit():
        return int(key)
    try:
        return int(key)
    except (TypeError, ValueError):
        return None


def _class_name_to_id_map(class_objects):
    """Map class display name -> id for legacy snapshots keyed by subject name."""
    out = {}
    for class_obj in class_objects or []:
        if class_obj and getattr(class_obj, 'name', None):
            out[class_obj.name] = class_obj.id
    return out


def _normalize_quarter_grades_map(quarter_map, class_objects):
    """
    Re-key one quarter's grades to integer class_id.
    JSON snapshots use string ids ('12') or legacy class names as keys.
    """
    if not isinstance(quarter_map, dict):
        return {}
    name_to_id = _class_name_to_id_map(class_objects)
    normalized = {}
    for key, value in quarter_map.items():
        if not isinstance(value, dict):
            continue
        class_id = _try_class_id_key(key)
        if class_id is None:
            class_id = name_to_id.get(key)
        if class_id is None:
            continue
        if class_id in normalized and isinstance(normalized[class_id], dict):
            normalized[class_id] = {**normalized[class_id], **value}
        else:
            normalized[class_id] = value
    return normalized


def _normalize_grades_by_quarter(grades_by_quarter, class_objects):
    """Normalize all quarters in grades_by_quarter to int class_id keys."""
    if not isinstance(grades_by_quarter, dict):
        return {}
    result = {}
    for quarter_key, quarter_map in grades_by_quarter.items():
        q = quarter_key
        if isinstance(q, str) and not q.startswith('Q'):
            q = f'Q{q}'
        result[q] = _normalize_quarter_grades_map(quarter_map, class_objects)
    return result


def _merge_grades_by_quarter(saved_gbq, fresh_gbq, class_objects):
    """
    Combine saved snapshot with live quarter grades.
    Saved values win when present; DB fills gaps (empty/partial snapshots).
    """
    saved_norm = _normalize_grades_by_quarter(saved_gbq or {}, class_objects)
    fresh_norm = _normalize_grades_by_quarter(fresh_gbq or {}, class_objects)
    merged = {}
    for quarter in ('Q1', 'Q2', 'Q3', 'Q4'):
        saved_q = saved_norm.get(quarter, {})
        fresh_q = fresh_norm.get(quarter, {})
        combined = dict(fresh_q) if isinstance(fresh_q, dict) else {}
        if isinstance(saved_q, dict):
            for class_id, grade in saved_q.items():
                if _quarter_has_any_grade(grade):
                    combined[class_id] = grade
        merged[quarter] = combined
    return merged


def _selected_quarters_from_report_card(report_card, report_card_data):
    """Resolve which quarters this report card covers."""
    saved_quarters = report_card_data.get('selected_quarters') if isinstance(report_card_data, dict) else None
    if saved_quarters and isinstance(saved_quarters, list):
        return [
            q if isinstance(q, str) and q.startswith('Q') else f'Q{q}'
            for q in saved_quarters
        ]

    quarter_str = (report_card.quarter or '').strip()
    if not quarter_str:
        return []
    if '-' in quarter_str:
        parts = [p.strip() for p in quarter_str.split('-') if p.strip()]
        if len(parts) == 2:
            try:
                lo = int(parts[0].replace('Q', '')) if parts[0].startswith('Q') else int(parts[0])
                hi = int(parts[1].replace('Q', '')) if parts[1].startswith('Q') else int(parts[1])
                return [f'Q{i}' for i in range(lo, hi + 1)]
            except (ValueError, TypeError):
                return [p if p.startswith('Q') else f'Q{p}' for p in parts]
        return [p if p.startswith('Q') else f'Q{p}' for p in parts]
    if quarter_str.startswith('Q'):
        return [quarter_str]
    try:
        return [f'Q{int(quarter_str)}']
    except (ValueError, TypeError):
        return [quarter_str]


def _sort_report_cards_newest_first(report_cards):
    """Stable newest-first ordering; null generated_at sorts last."""
    from datetime import datetime as _dt_min

    def _key(rc):
        ga = getattr(rc, 'generated_at', None)
        return (ga is None, ga or _dt_min.min)

    return sorted(report_cards or [], key=_key, reverse=True)


def _load_report_card_comments(student_id, school_year_id, class_ids_int):
    """Load teacher/management comments keyed by class id string."""
    from models import ReportCardComment

    comments_by_class = {}
    q = ReportCardComment.query.filter_by(
        student_id=student_id,
        school_year_id=school_year_id,
        quarter='ALL',
    )
    if class_ids_int:
        q = q.filter(ReportCardComment.class_id.in_(class_ids_int))
    for row in q.all():
        if row.comment_text and str(row.comment_text).strip():
            comments_by_class[str(row.class_id)] = row.comment_text.strip()
    return comments_by_class


def _sanitize_letter_grades_for_report(obj):
    """
    Recursively normalize legacy failing letter grades to 'E' in report data.
    Handles grades dict, grades_by_quarter, and nested structures.
    """
    if obj is None:
        return obj
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in ('letter', 'letter_grade', 'overall_letter', 'grade') and v in ('F', 'FL'):
                result[k] = 'E'
            else:
                result[k] = _sanitize_letter_grades_for_report(v)
        return result
    if isinstance(obj, list):
        return [_sanitize_letter_grades_for_report(item) for item in obj]
    return obj


def _quarter_has_any_grade(quarter_payload):
    """
    Return True when a quarter payload contains at least one usable grade value.
    Supports multiple payload shapes used in this codebase.
    """
    if not quarter_payload:
        return False

    # If payload is one class dict or a map of classes -> class dict.
    if isinstance(quarter_payload, dict):
        # Direct grade markers
        for key in ('overall_grade', 'overall_letter', 'letter_grade', 'letter', 'grade'):
            value = quarter_payload.get(key)
            if value not in (None, '', 'N/A'):
                return True
        for key in ('overall_percentage', 'percentage', 'avg_percentage', 'score'):
            value = quarter_payload.get(key)
            if value not in (None, '', 'N/A'):
                return True

        # Nested dict/list content (class maps and structures)
        for nested in quarter_payload.values():
            if _quarter_has_any_grade(nested):
                return True
        return False

    if isinstance(quarter_payload, list):
        return any(_quarter_has_any_grade(item) for item in quarter_payload)

    # Primitive fallback
    return quarter_payload not in (None, '', 'N/A')


def _detect_quarter_grade_inconsistency(all_quarter_grades):
    """
    Detect non-contiguous quarter-grade patterns.
    Allowed examples:
      - Q1,Q2 graded and Q3,Q4 not graded
      - Q1,Q2 not graded and Q3,Q4 graded
    Flag example:
      - Q1 graded, Q2 not graded, Q3/Q4 graded
    Rule: graded quarters must form one contiguous block (or no grades).
    """
    quarter_keys = ['Q1', 'Q2', 'Q3', 'Q4']
    graded_flags = []

    for q in quarter_keys:
        payload = all_quarter_grades.get(q)
        if payload is None:
            payload = all_quarter_grades.get(q.replace('Q', ''))
        graded_flags.append(1 if _quarter_has_any_grade(payload) else 0)

    first = next((i for i, flag in enumerate(graded_flags) if flag == 1), None)
    if first is None:
        return False, graded_flags  # No quarter has grades yet

    last = len(graded_flags) - 1 - next(
        (i for i, flag in enumerate(reversed(graded_flags)) if flag == 1), 0
    )
    is_contiguous = all(flag == 1 for flag in graded_flags[first:last + 1])
    return (not is_contiguous), graded_flags


def _quarter_str_from_selection(quarters_to_include):
    """Build stored ReportCard.quarter label (e.g. Q1, Q1-Q4) from selected quarters."""
    valid_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    quarters_to_include = [q for q in (quarters_to_include or []) if q in valid_quarters]
    if not quarters_to_include:
        return None
    if len(quarters_to_include) == 1:
        return quarters_to_include[0]
    quarter_nums = sorted([int(q.replace('Q', '')) for q in quarters_to_include])
    if len(quarter_nums) == len(quarters_to_include) and quarter_nums == list(
        range(min(quarter_nums), max(quarter_nums) + 1)
    ):
        return f"Q{quarter_nums[0]}-Q{quarter_nums[-1]}"
    return quarters_to_include[-1]


def _extract_comment_overrides_from_form(form, quarters_to_include, class_ids_int):
    """
    Read management report-card comment overrides from form fields:
      comment_<class_id>
    Returns: { '123': 'text', ... }
    """
    out = {}
    for cid in class_ids_int or []:
        key = f'comment_{cid}'
        if key in form:
            out[str(cid)] = (form.get(key) or '').strip()
    return out


def persist_report_card_record(
    student_id_int,
    school_year_id_int,
    class_ids_int,
    quarters_to_include,
    report_type='official',
    include_attendance=True,
    include_comments=True,
    additional_comments=None,
    comments_overrides=None,
    persist_comment_overrides=False,
    enrollment_must_be_active=True,
    notify_admins=True,
):
    """
    Persist report card JSON (and optional admin notifications). Does not build PDF.
    Returns a dict with ok, error, and render payload keys on success.
    """
    out = {
        'ok': False,
        'error': None,
        'warnings': [],
        'student': None,
        'report_card': None,
        'valid_class_ids': [],
        'quarters_to_include': [],
        'quarter_str': None,
        'calculated_grades': {},
        'calculated_grades_by_quarter': {},
        'report_card_data': {},
        'inconsistency_flag': False,
        'quarter_flags': [],
        'include_attendance': include_attendance,
        'include_comments': include_comments,
        'report_type': report_type,
    }
    valid_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    quarters_clean = [q for q in (quarters_to_include or []) if q in valid_quarters]
    if not quarters_clean:
        out['error'] = 'Invalid or empty quarter selection.'
        return out

    quarter_str = _quarter_str_from_selection(quarters_clean)
    if not quarter_str:
        out['error'] = 'Could not determine report period from quarters.'
        return out

    # Enrollment/class eligibility:
    # - Allow withdrawn students and closed school years to use inactive enrollments.
    # - Enforce that enrollment overlapped the selected quarter window.
    window_start, window_end = _selected_quarters_date_window(school_year_id_int, quarters_clean)

    student = Student.query.get(student_id_int)
    if not student:
        out['error'] = 'Student not found.'
        return out

    school_year = SchoolYear.query.get(school_year_id_int)
    if not school_year:
        out['error'] = 'School year not found.'
        return out

    if enrollment_must_be_active:
        enrollment_must_be_active = enrollment_must_be_active_for_report_card(student, school_year)

    valid_class_ids = []
    for class_id in class_ids_int:
        q = Enrollment.query.filter_by(student_id=student_id_int, class_id=class_id)
        if enrollment_must_be_active:
            q = q.filter_by(is_active=True)
        enrollments = q.all()
        if not enrollments:
            out['warnings'].append(
                f"Student is not enrolled ({'active' if enrollment_must_be_active else 'any'}) "
                f"in class ID {class_id}."
            )
            continue
        if window_start and window_end:
            if not any(_enrollment_eligible_for_report_card(e, window_start, window_end) for e in enrollments):
                out['warnings'].append(
                    f"Student enrollment does not overlap selected period for class ID {class_id}."
                )
                continue
        valid_class_ids.append(class_id)

    if not valid_class_ids:
        out['error'] = 'No valid classes for this student.'
        return out

    if not getattr(student, 'gender', None):
        out['error'] = (
            'Student profile is missing Gender. Update the student record before generating a report card.'
        )
        return out
    if not _is_valid_school_year_label(getattr(student, 'entrance_date', None)):
        out['error'] = (
            'Student profile is missing a valid Entrance School Year (YYYY-YYYY). '
            'Update the student record before generating a report card.'
        )
        return out

    try:
        from utils.quarter_grade_calculator import update_all_quarter_grades_for_student, get_quarter_grades_for_report

        force_recalc = bool(getattr(school_year, 'is_active', True))
        update_all_quarter_grades_for_student(
            student_id=student_id_int,
            school_year_id=school_year_id_int,
            force=force_recalc,
        )
        all_quarter_grades = get_quarter_grades_for_report(
            student_id=student_id_int,
            school_year_id=school_year_id_int,
            class_ids=valid_class_ids,
        )

        calculated_grades_by_quarter = {}
        for q in quarters_clean:
            q_key = q
            q_num_key = q.replace('Q', '')
            if q_key in all_quarter_grades:
                calculated_grades_by_quarter[q] = all_quarter_grades[q_key]
            elif q_num_key in all_quarter_grades:
                calculated_grades_by_quarter[q] = all_quarter_grades[q_num_key]
            else:
                calculated_grades_by_quarter[q] = {}

        inconsistency_flag, quarter_flags = _detect_quarter_grade_inconsistency(all_quarter_grades)

        if len(quarters_clean) == 1:
            calculated_grades = calculated_grades_by_quarter.get(quarters_clean[0], {})
        else:
            calculated_grades = calculated_grades_by_quarter.get(quarters_clean[0], {})

        # Each generation is a new snapshot so Recents/history show every run
        # (regenerating Q1–Q4 does not silently overwrite the prior list entry).
        report_card = ReportCard(
            student_id=student_id_int,
            school_year_id=school_year_id_int,
            quarter=quarter_str,
        )
        db.session.add(report_card)

        report_card_data = {
            'classes': valid_class_ids,
            'report_type': report_type,
            'include_attendance': include_attendance,
            'include_comments': include_comments,
            'grades': calculated_grades,
            'grades_by_quarter': calculated_grades_by_quarter,
            'selected_quarters': quarters_clean,
        }
        report_card_data['additional_comments'] = (additional_comments or '').strip()

        # Attach report card comments (teacher-entered) and optionally apply overrides.
        comments_by_class = {}
        if include_comments:
            from models import ReportCardComment
            existing_rows = ReportCardComment.query.filter(
                ReportCardComment.student_id == student_id_int,
                ReportCardComment.school_year_id == school_year_id_int,
                ReportCardComment.quarter == 'ALL',
                ReportCardComment.class_id.in_(valid_class_ids),
            ).all()
            for row in existing_rows:
                comments_by_class[str(row.class_id)] = row.comment_text or ''

            # Apply overrides from management generation form
            if comments_overrides and isinstance(comments_overrides, dict):
                for cid in valid_class_ids:
                    cid_str = str(cid)
                    if cid_str in comments_overrides:
                        comments_by_class[cid_str] = (comments_overrides.get(cid_str) or '').strip()

            # Optionally persist overrides back into ReportCardComment table
            if persist_comment_overrides and comments_overrides and isinstance(comments_overrides, dict):
                for cid in valid_class_ids:
                    cid_str = str(cid)
                    if cid_str not in comments_overrides:
                        continue
                    txt = (comments_overrides.get(cid_str) or '').strip()
                    existing = ReportCardComment.query.filter_by(
                        student_id=student_id_int,
                        class_id=cid,
                        school_year_id=school_year_id_int,
                        quarter='ALL',
                    ).first()
                    if existing:
                        existing.comment_text = txt
                        existing.author_user_id = getattr(current_user, 'id', None)
                        existing.author_teacher_staff_id = None
                        existing.source = 'management'
                    else:
                        db.session.add(ReportCardComment(
                            student_id=student_id_int,
                            class_id=cid,
                            school_year_id=school_year_id_int,
                            quarter='ALL',
                            comment_text=txt,
                            author_user_id=getattr(current_user, 'id', None),
                            author_teacher_staff_id=None,
                            source='management',
                        ))

        report_card_data['comments_by_class'] = comments_by_class

        if include_attendance:
            from models import Attendance
            attendance_data = {}
            for class_id in valid_class_ids:
                attendance_records = Attendance.query.filter_by(
                    student_id=student_id_int,
                    class_id=class_id,
                ).all()
                attendance_summary = {
                    'Present': 0,
                    'Unexcused Absence': 0,
                    'Excused Absence': 0,
                    'Tardy': 0,
                }
                for att in attendance_records:
                    status = att.status or 'Present'
                    if status in attendance_summary:
                        attendance_summary[status] += 1
                    else:
                        attendance_summary['Present'] += 1
                class_obj = Class.query.get(class_id)
                attendance_data[class_obj.name if class_obj else f"Class {class_id}"] = attendance_summary
            report_card_data['attendance'] = attendance_data

        def _format_date_for_save(value):
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            from datetime import date, datetime as _dt
            if isinstance(value, (date, _dt)):
                return value.strftime('%m/%d/%Y')
            if isinstance(value, str):
                for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d'):
                    try:
                        return _dt.strptime(value.strip(), fmt).strftime('%m/%d/%Y')
                    except Exception:
                        continue
            return None

        student_name = f"{student.first_name} {student.last_name}"
        expected_grad_date = _calculate_expected_grad_from_student(student)
        student_address = (
            f"{getattr(student, 'street', '')}, {getattr(student, 'city', '')}, "
            f"{getattr(student, 'state', '')} {getattr(student, 'zip_code', '')}"
        ).strip(', ')
        grade_at_year = grade_level_for_school_year(student, school_year)
        snapshot_grade = grade_at_year if grade_at_year is not None else student.grade_level
        report_card_data['student_display'] = {
            'name': student_name,
            'gender': getattr(student, 'gender', None),
            'address': student_address or None,
            'dob': _format_date_for_save(getattr(student, 'dob', None)),
            'entrance_date': getattr(student, 'entrance_date', None),
            'expected_grad_date': expected_grad_date,
            'phone': getattr(student, 'phone', None),
            'grade': snapshot_grade,
            'grade_display': report_card_grade_display(snapshot_grade),
        }
        record_student_school_year_grade(
            student_id_int,
            school_year_id_int,
            int(snapshot_grade),
            enrolled=True,
        )

        report_card.grades_details = json.dumps(report_card_data)
        report_card.generated_at = datetime.utcnow()
        if getattr(current_user, 'id', None):
            report_card.generated_by_user_id = current_user.id
        db.session.commit()

        if notify_admins:
            _notify_admins_report_card_generated(
                student=student,
                school_year=report_card.school_year,
                quarter_str=report_card.quarter,
                report_type=report_type,
                generated_at_utc=report_card.generated_at or datetime.utcnow(),
                report_card_id=report_card.id,
                inconsistency_flag=inconsistency_flag,
                quarter_flags=quarter_flags,
            )

        out.update({
            'ok': True,
            'student': student,
            'report_card': report_card,
            'valid_class_ids': valid_class_ids,
            'quarters_to_include': quarters_clean,
            'quarter_str': quarter_str,
            'calculated_grades': calculated_grades,
            'calculated_grades_by_quarter': calculated_grades_by_quarter,
            'report_card_data': report_card_data,
            'inconsistency_flag': inconsistency_flag,
            'quarter_flags': quarter_flags,
        })
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('persist_report_card_record failed')
        out['error'] = str(exc)
    return out


def _notify_admins_report_card_generated(student, school_year, quarter_str, report_type, generated_at_utc,
                                         report_card_id=None, inconsistency_flag=False, quarter_flags=None):
    """
    Send in-app + email alerts to Director / School Administrator when a report card is generated.
    Uses existing notification service; email is sent automatically from create_notification().
    """
    try:
        from models import User
        from services.notifications import create_notifications_for_users

        admin_users = User.query.filter(User.role.in_(['Director', 'School Administrator'])).all()
        admin_user_ids = [u.id for u in admin_users if u and getattr(u, 'id', None)]
        if not admin_user_ids:
            return

        generated_label = generated_at_utc.strftime('%Y-%m-%d %H:%M UTC')
        student_name = f"{student.first_name} {student.last_name}".strip()
        report_kind = (report_type or 'official').title()
        title = f"Report card generated: {student_name}"

        message = (
            f"{report_kind} report card generated for {student_name} "
            f"(Grade {student.grade_level}) - {school_year.name}, {quarter_str}. "
            f"Generated at {generated_label} by {getattr(current_user, 'username', 'system')}."
        )
        if inconsistency_flag:
            pattern = ','.join(str(x) for x in (quarter_flags or []))
            message += (
                " Flag: quarter grading pattern appears inconsistent "
                f"(Q1-Q4 graded flags: {pattern}). Please review quarter records."
            )

        link = None
        if report_card_id:
            link = f'/app/management/report-cards/{report_card_id}'

        create_notifications_for_users(
            admin_user_ids,
            'report_card_generation',
            title,
            message,
            link
        )
    except Exception as notify_exc:
        current_app.logger.warning('Report card admin alert failed: %s', notify_exc)


# ============================================================
# Route: /report/card/generate', methods=['GET', 'POST']
# Function: generate_report_card_form
# ============================================================

@bp.route('/report/card/generate', methods=['GET', 'POST'])
@login_required
@permissions_required('report_cards:generate')
def generate_report_card_form():
    if request.method == 'GET':
        path = '/app/management/report-cards/generate'
        query = request.query_string.decode('utf-8') if request.query_string else ''
        if query:
            path = f'{path}?{query}'
        return redirect(path)

    if request.method == 'POST':
        # Get form data
        student_id = request.form.get('student_id')
        school_year_id = request.form.get('school_year_id')
        class_ids = request.form.getlist('class_ids')  # Get multiple class IDs
        selected_quarters = request.form.getlist('quarters')  # Get selected quarters
        report_type = request.form.get('report_type', 'official')  # Default to official
        include_attendance = request.form.get('include_attendance') == 'on'
        include_comments = request.form.get('include_comments') == 'on'
        persist_comment_overrides = request.form.get('persist_comment_overrides') == 'on'
        additional_comments = (request.form.get('additional_comments') or '').strip()
        
        if not all([student_id, school_year_id]):
            flash("Please select a student and school year.", 'danger')
            return redirect('/app/management/report-cards/generate')
        
        if not class_ids:
            flash("Please select at least one class.", 'danger')
            return redirect('/app/management/report-cards/generate')
        
        if not selected_quarters:
            flash("Please select at least one quarter.", 'danger')
            return redirect('/app/management/report-cards/generate')

        # Validate that the values can be converted to integers
        try:
            student_id_int = int(student_id)
            school_year_id_int = int(school_year_id)
            class_ids_int = [int(cid) for cid in class_ids]
        except ValueError:
            flash("Invalid student, school year, or class selection.", 'danger')
            return redirect('/app/management/report-cards/generate')
        
        # Use selected quarters instead of auto-determining
        # Validate selected quarters
        valid_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
        quarters_to_include = [q for q in selected_quarters if q in valid_quarters]
        
        if not quarters_to_include:
            flash("Invalid quarter selection. Please select valid quarters.", 'danger')
            return redirect('/app/management/report-cards/generate')

        rc_result = persist_report_card_record(
            student_id_int=student_id_int,
            school_year_id_int=school_year_id_int,
            class_ids_int=class_ids_int,
            quarters_to_include=quarters_to_include,
            report_type=report_type,
            include_attendance=include_attendance,
            include_comments=include_comments,
            additional_comments=additional_comments,
            comments_overrides=_extract_comment_overrides_from_form(request.form, quarters_to_include, class_ids_int),
            persist_comment_overrides=persist_comment_overrides,
            enrollment_must_be_active=True,
            notify_admins=True,
        )
        if not rc_result['ok']:
            flash(rc_result['error'], 'danger')
            return redirect('/app/management/report-cards/generate')
        for w in rc_result.get('warnings') or []:
            flash(w, 'warning')
        if rc_result.get('inconsistency_flag'):
            flash(
                "Heads up: quarter grades look inconsistent (example: Q1 has grades, Q2 missing, Q3/Q4 have grades). "
                "An administrator alert was generated for review.",
                'warning',
            )

        student = rc_result['student']
        unfinalized_msg = report_card_unfinalized_banner_message(student.grade_level)
        if unfinalized_msg:
            flash(unfinalized_msg, 'warning')
        report_card = rc_result['report_card']
        valid_class_ids = rc_result['valid_class_ids']
        calculated_grades = rc_result['calculated_grades']
        calculated_grades_by_quarter = rc_result['calculated_grades_by_quarter']
        report_card_data = rc_result['report_card_data']
        quarters_to_include = rc_result['quarters_to_include']

        current_app.logger.info(
            "Report card persisted: quarters=%s label=%s",
            quarters_to_include,
            rc_result.get('quarter_str'),
        )

        return_category = (request.form.get('return_category') or '').strip()
        if return_category in REPORT_CARD_CATEGORIES:
            return redirect(
                f'/app/management/report-cards/category/{return_category}'
                f'?highlight={student.id}&saved=1'
            )
        return redirect(f'/app/management/report-cards/{report_card.id}')

    return redirect('/app/management/report-cards/generate')



# ============================================================
# Route: /report/card/view/<int:report_card_id>
# Function: view_report_card
# ============================================================

@bp.route('/report/card/view/<int:report_card_id>')
@login_required
@permissions_required('report_cards:view', 'report_cards:generate')
def view_report_card(report_card_id):
    return redirect(f'/app/management/report-cards/{report_card_id}')



class _ReportCardStudentView:
    """Student row with a grade override for historical PDF rendering."""

    __slots__ = ('_student', 'grade_level')

    def __init__(self, student, grade_level):
        object.__setattr__(self, '_student', student)
        object.__setattr__(self, 'grade_level', grade_level)

    def __getattr__(self, name):
        return getattr(self._student, name)


def _report_card_pdf_grade_level(student, report_card_data):
    if isinstance(report_card_data, dict):
        saved = report_card_data.get('student_display') or {}
        grade = saved.get('grade')
        if grade is not None:
            try:
                return int(grade)
            except (TypeError, ValueError):
                pass
    return getattr(student, 'grade_level', None)


def build_report_card_pdf_response(report_card):
    """Render a stored report card snapshot as a PDF download response."""
    from weasyprint import HTML
    from io import BytesIO
    from flask import make_response

    student = report_card.student
    
    # Parse report card data
    report_card_data = json.loads(report_card.grades_details) if report_card.grades_details else {}
    
    # Extract data from new structure (backward compatible)
    if isinstance(report_card_data, dict) and 'grades' in report_card_data:
        grades = report_card_data.get('grades', {})
        # Use saved grades_by_quarter so PDF shows what was generated, not fresh DB
        grades_by_quarter = report_card_data.get('grades_by_quarter')
        attendance = report_card_data.get('attendance', {})
        selected_classes = report_card_data.get('classes', [])
        report_type = report_card_data.get('report_type', 'official')
        include_attendance = report_card_data.get('include_attendance', False)
        include_comments = report_card_data.get('include_comments', False)
        comments_by_class = report_card_data.get('comments_by_class', {}) if isinstance(report_card_data, dict) else {}
    else:
        grades = report_card_data if report_card_data else {}
        grades_by_quarter = None
        attendance = {}
        selected_classes = []
        report_type = 'official'  # Default for old report cards
        include_attendance = False
        include_comments = False
        comments_by_class = {}

    # Build class list early — needed to normalize JSON snapshot keys (string id / class name)
    class_objects = []
    class_ids_int = []
    if selected_classes:
        for class_id in selected_classes:
            try:
                cid = int(class_id)
            except (TypeError, ValueError):
                continue
            class_ids_int.append(cid)
            class_obj = Class.query.get(cid)
            if class_obj:
                class_objects.append(class_obj)

    from utils.quarter_grade_calculator import get_quarter_grades_for_report
    fresh_grades_by_quarter = get_quarter_grades_for_report(
        student_id=student.id,
        school_year_id=report_card.school_year_id,
        class_ids=class_ids_int if class_ids_int else None,
    )

    if isinstance(grades_by_quarter, dict) and grades_by_quarter:
        grades_by_quarter = _merge_grades_by_quarter(
            grades_by_quarter, fresh_grades_by_quarter, class_objects
        )
    else:
        grades_by_quarter = _normalize_grades_by_quarter(
            fresh_grades_by_quarter, class_objects
        )

    # Sanitize legacy failing letters to 'E' for report cards
    grades = _sanitize_letter_grades_for_report(grades)
    grades_by_quarter = _sanitize_letter_grades_for_report(grades_by_quarter)

    # Older snapshots stored include_comments=False even when comments exist
    if comments_by_class and any((v or '').strip() for v in comments_by_class.values()):
        include_comments = True
    elif not comments_by_class or not any((v or '').strip() for v in comments_by_class.values()):
        db_comments = _load_report_card_comments(
            student.id, report_card.school_year_id, class_ids_int
        )
        if db_comments:
            comments_by_class = {**db_comments, **(comments_by_class or {})}
            include_comments = True
    
    # Prepare student data for template (robust date handling)
    from datetime import datetime, date as date_type
    
    def _format_date_value(value):
        try:
            if value is None:
                return 'N/A'
            # If already a date/datetime object
            if isinstance(value, (date_type, datetime)):
                return value.strftime('%m/%d/%Y')
            # If it's a string, try common formats, otherwise return as-is
            if isinstance(value, str):
                for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d'):
                    try:
                        return datetime.strptime(value, fmt).strftime('%m/%d/%Y')
                    except Exception:
                        continue
                return value
            return 'N/A'
        except Exception:
            return 'N/A'
    
    pdf_grade = _report_card_pdf_grade_level(student, report_card_data)
    student_for_template = _ReportCardStudentView(student, pdf_grade)

    student_data = {
        'name': f"{student.first_name} {student.last_name}",
        'student_id_formatted': student.student_id_formatted if hasattr(student, 'student_id_formatted') else (student.student_id if student.student_id else 'N/A'),
        'ssn': getattr(student, 'ssn', None),
        'dob': _format_date_value(getattr(student, 'dob', None)),
        'grade': pdf_grade,
        'gender': getattr(student, 'gender', 'N/A'),
        'address': f"{getattr(student, 'street', '')}, {getattr(student, 'city', '')}, {getattr(student, 'state', '')} {getattr(student, 'zip_code', '')}".strip(', '),
        'phone': getattr(student, 'phone', ''),
        'entrance_date': getattr(student, 'entrance_date', None) or 'N/A',
        'expected_grad_date': _calculate_expected_grad_from_student(student) or 'N/A',
    }
    # Override with saved confirmation data from when report was generated
    saved_student = report_card_data.get('student_display') if isinstance(report_card_data, dict) else None
    if saved_student:
        if saved_student.get('name'):
            student_data['name'] = saved_student['name']
        if saved_student.get('gender') not in (None, ''):
            student_data['gender'] = saved_student['gender']
        if saved_student.get('address') not in (None, ''):
            student_data['address'] = saved_student['address']
        if saved_student.get('dob'):
            student_data['dob'] = saved_student['dob']
        if saved_student.get('phone') is not None:
            student_data['phone'] = saved_student['phone'] or ''
        if 'entrance_date' in saved_student:
            student_data['entrance_date'] = saved_student.get('entrance_date') or 'N/A'
        if 'expected_grad_date' in saved_student:
            student_data['expected_grad_date'] = saved_student.get('expected_grad_date') or 'N/A'
        if saved_student.get('grade') is not None:
            try:
                student_data['grade'] = int(saved_student['grade'])
                pdf_grade = int(saved_student['grade'])
                student_for_template = _ReportCardStudentView(student, pdf_grade)
            except (TypeError, ValueError):
                pass

    selected_quarters = _selected_quarters_from_report_card(report_card, report_card_data)

    # Choose template based on grade level and report type
    template_prefix = 'unofficial' if report_type == 'unofficial' else 'official'
    template_name = _report_card_template_name(pdf_grade, template_prefix)
    
    # Render the HTML template
    # Backward-compat: older snapshots used comments_by_quarter; collapse to comments_by_class if needed.
    if not comments_by_class and isinstance(report_card_data, dict):
        legacy = report_card_data.get('comments_by_quarter')
        if isinstance(legacy, dict):
            # pick first non-empty comment per class across any quarters present
            tmp = {}
            for qmap in legacy.values():
                if not isinstance(qmap, dict):
                    continue
                for cid, txt in qmap.items():
                    if cid not in tmp and txt:
                        tmp[str(cid)] = txt
            comments_by_class = tmp

    html_content = render_template(
        template_name,
        report_card=report_card,
        student=student_data,
        grades=grades,
        grades_by_quarter=grades_by_quarter,  # Cumulative quarter data
        selected_quarters=selected_quarters,  # So template shows grades for this report's quarter
        attendance=attendance,
        class_objects=class_objects,
        include_attendance=include_attendance,
        include_comments=include_comments,
        comments_by_class=comments_by_class,
        additional_comments=report_card_data.get('additional_comments', '') if isinstance(report_card_data, dict) else '',
        generated_date=report_card.generated_at or datetime.utcnow(),
        report_type=report_type,
        template_prefix=template_prefix,
        **_elementary_pdf_extras(
            student_for_template,
            report_card.school_year_id,
            selected_quarters,
            class_objects,
            grades,
            include_attendance,
            report_card_data,
        ),
    )
    
    # Read CSS file from filesystem and inject it into the HTML
    import os
    css_path = os.path.join(current_app.root_path, 'static', 'report_card_styles.css')
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        # Inject CSS into the HTML (replace the link tag with embedded style)
        html_content = html_content.replace(
            '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'report_card_styles.css\') }}">',
            f'<style>{css_content}</style>'
        )
        # Also handle already-rendered link tags
        import re
        html_content = re.sub(
            r'<link rel="stylesheet" href="[^"]*report_card_styles\.css[^"]*">',
            f'<style>{css_content}</style>',
            html_content
        )
    except Exception as e:
        current_app.logger.warning(f'Could not load CSS file: {str(e)}')
    
    # Read logo file and convert to base64 for embedding
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'clara_logo.png')
    try:
        import base64
        with open(logo_path, 'rb') as f:
            logo_data = base64.b64encode(f.read()).decode('utf-8')
        # Replace logo src with base64 data
        html_content = re.sub(
            r'<img src="[^"]*clara_logo\.png[^"]*"',
            f'<img src="data:image/png;base64,{logo_data}"',
            html_content
        )
    except Exception as e:
        current_app.logger.warning(f'Could not load logo file: {str(e)}')
    
    # Ensure any remaining /static asset URLs resolve without HTTP fetches.
    try:
        static_root = os.path.join(current_app.root_path, 'static').replace('\\', '/')
        html_content = re.sub(r'href=\"/static/', f'href=\"file:///{static_root}/', html_content)
        html_content = re.sub(r'src=\"/static/', f'src=\"file:///{static_root}/', html_content)
    except Exception:
        pass

    # Generate PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content, base_url=current_app.root_path).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    
    # Create response
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    filename = f"ReportCard_{student.first_name}_{student.last_name}_{report_card.school_year.name.replace('/', '_')}_{report_card.quarter}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@bp.route('/report/card/pdf/<int:report_card_id>')
@login_required
@permissions_required('report_cards:generate')
def generate_report_card_pdf(report_card_id):
    """PDF download — SPA API."""
    ReportCard.query.get_or_404(report_card_id)
    return redirect(f'/api/spa/report-cards/{report_card_id}/pdf')


@bp.route('/report-cards/approve/<int:report_card_id>', methods=['POST'])
@login_required
@admin_required
def approve_report_card_for_parents_route(report_card_id):
    """Director publishes an official report card to the Family Portal."""
    report_card = ReportCard.query.get_or_404(report_card_id)
    try:
        approve_report_card_for_parents(report_card, current_user.id)
        flash(
            f'Report card approved for Family Portal: '
            f'{report_card.student.first_name} {report_card.student.last_name} '
            f'({report_card.quarter}, {report_card.school_year.name}).',
            'success',
        )
    except ValueError as exc:
        flash(str(exc), 'warning')
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Report card approval failed: %s', exc)
        flash('Could not approve report card for parents.', 'danger')
    return redirect(f'/app/management/report-cards/{report_card_id}')


@bp.route('/report-cards/revoke/<int:report_card_id>', methods=['POST'])
@login_required
@admin_required
def revoke_report_card_for_parents_route(report_card_id):
    """Director removes a report card from the Family Portal."""
    report_card = ReportCard.query.get_or_404(report_card_id)
    try:
        revoke_report_card_parent_access(report_card)
        flash(
            f'Report card removed from Family Portal: '
            f'{report_card.student.first_name} {report_card.student.last_name} '
            f'({report_card.quarter}).',
            'success',
        )
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Report card revoke failed: %s', exc)
        flash('Could not revoke parent access to this report card.', 'danger')
    return redirect(f'/app/management/report-cards/{report_card_id}')


# ============================================================
# Route: /report-cards
# Function: report_cards
# ============================================================

@bp.route('/report-cards')
@login_required
@permissions_required('report_cards:view', 'report_cards:generate')
def report_cards():
    """Report cards hub — React SPA."""
    return redirect('/app/management/report-cards')



# ============================================================
# Route: /report-cards/category/<category>
# Function: report_cards_by_category
# ============================================================

@bp.route('/report-cards/category/<category>')
@login_required
@permissions_required('report_cards:view', 'report_cards:generate')
def report_cards_by_category(category):
    """Grade category roster — React SPA."""
    category_slug = _resolve_report_card_category(category)
    if category_slug not in REPORT_CARD_CATEGORIES:
        flash('Invalid grade category selected.', 'danger')
        return redirect('/app/management/report-cards')
    path = f'/app/management/report-cards/category/{category_slug}'
    query = request.query_string.decode('utf-8') if request.query_string else ''
    if query:
        path = f'{path}?{query}'
    return redirect(path)



# ============================================================
# Route: /report-cards/delete/<int:report_card_id>', methods=['POST']
# Function: delete_report_card
# ============================================================

@bp.route('/report-cards/delete/<int:report_card_id>', methods=['POST'])
@login_required
@permissions_required('report_cards:generate')
def delete_report_card(report_card_id):
    """Delete a report card."""
    try:
        report_card = ReportCard.query.get_or_404(report_card_id)
        student_name = f"{report_card.student.first_name} {report_card.student.last_name}" if report_card.student else "Unknown"
        quarter = report_card.quarter
        
        db.session.delete(report_card)
        db.session.commit()
        
        flash(f'Report card deleted successfully for {student_name} ({quarter}).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting report card: {str(e)}', 'danger')
    
    return redirect('/app/management/report-cards')


# ============================================================
# End of school year: report cards + archive classes
# (Registered on management blueprint in management_routes/__init__.py)
# ============================================================

def _apply_grade_promotion_after_year_close(enrolled_student_ids):
    """
    For each student ID that had an active enrollment in the closed year:
    - If is_repeating: clear the flag; do not change grade_level.
    - Else if grade_level is None: skip.
    - Else if grade_level >= 12: skip (no auto-promotion past 12th).
    - Else: increment grade_level by 1.

    Then provision new 3rd+ portal accounts where missing.

    Returns a stats dict.
    """
    from datetime import datetime
    from .students import _provision_student_login_if_needed

    stats = {
        "promoted": 0,
        "repeating_cleared": 0,
        "skipped": 0,
        "provisioned_accounts": 0,
    }
    for sid in enrolled_student_ids:
        student = Student.query.get(sid)
        if not student or getattr(student, "is_deleted", False):
            continue
        gl = student.grade_level
        if gl is None:
            stats["skipped"] += 1
            continue
        if student.is_repeating:
            student.is_repeating = False
            stats["repeating_cleared"] += 1
            continue
        if int(gl) >= 12:
            stats["skipped"] += 1
            continue
        student.grade_level = int(gl) + 1
        student.status_updated_at = datetime.utcnow()
        stats["promoted"] += 1

    for sid in enrolled_student_ids:
        student = Student.query.get(sid)
        if not student or getattr(student, "is_deleted", False):
            continue
        if _provision_student_login_if_needed(student):
            stats["provisioned_accounts"] += 1

    return stats


def close_school_year():
    """
    For a selected school year: generate official Q1–Q4 report cards for all current
    students with active enrollments in that year, then deactivate those enrollments,
    mark classes inactive, set individual and group assignments to Inactive (preserving
    Voided), promote enrolled students one grade (except those marked repeating; repeating
    students keep their grade and the flag is cleared), provision new 3rd-grade logins if
    needed, and mark the school year inactive. Historical grades and report card rows
    remain in the database.
    """
    from models import Assignment, GroupAssignment

    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()

    if request.method == 'GET':
        return render_template('management/school_year_close.html', school_years=school_years)

    school_year_id = request.form.get('school_year_id', type=int)
    confirm = (request.form.get('confirm') or '').strip()
    if confirm != 'CLOSE YEAR':
        flash('You must type CLOSE YEAR exactly to confirm.', 'danger')
        return render_template('management/school_year_close.html', school_years=school_years)

    if not school_year_id:
        flash('Select a school year.', 'danger')
        return render_template('management/school_year_close.html', school_years=school_years)

    sy = SchoolYear.query.get_or_404(school_year_id)

    classes_in_year = Class.query.filter_by(school_year_id=sy.id).all()
    class_ids = [c.id for c in classes_in_year]

    students = (
        Student.query.filter(Student.is_deleted == False)
        .order_by(Student.last_name, Student.first_name)
        .all()
    )

    ok_n = 0
    skip_n = 0
    err_n = 0
    errors_sample = []
    enrolled_student_ids = set()

    quarters_full = ['Q1', 'Q2', 'Q3', 'Q4']
    for student in students:
        enrs = (
            Enrollment.query.join(Class, Enrollment.class_id == Class.id)
            .filter(
                Class.school_year_id == sy.id,
                Enrollment.student_id == student.id,
                Enrollment.is_active == True,
            )
            .all()
        )
        if not enrs:
            skip_n += 1
            continue
        enrolled_student_ids.add(student.id)
        cid_list = list({e.class_id for e in enrs})
        res = persist_report_card_record(
            student_id_int=student.id,
            school_year_id_int=sy.id,
            class_ids_int=cid_list,
            quarters_to_include=quarters_full,
            report_type='official',
            include_attendance=True,
            include_comments=True,
            enrollment_must_be_active=True,
            notify_admins=False,
        )
        if res['ok']:
            ok_n += 1
        else:
            err_n += 1
            if len(errors_sample) < 15:
                errors_sample.append(f"{student.first_name} {student.last_name}: {res['error']}")

    if class_ids:
        Assignment.query.filter(
            Assignment.class_id.in_(class_ids),
            Assignment.status != 'Voided',
        ).update({Assignment.status: 'Inactive'}, synchronize_session=False)
        GroupAssignment.query.filter(
            GroupAssignment.class_id.in_(class_ids),
            GroupAssignment.status != 'Voided',
        ).update({GroupAssignment.status: 'Inactive'}, synchronize_session=False)

    # Defensive close: deactivate EVERYTHING tied to this school year, even if
    # an unexpected class slipped out of `class_ids` (bad data, late edits, etc).
    # (We keep historical rows; we only flip "active" flags.)
    class_ids_for_year = [c.id for c in classes_in_year]
    if class_ids_for_year:
        Enrollment.query.filter(
            Enrollment.class_id.in_(class_ids_for_year),
            Enrollment.is_active.is_(True),
        ).update(
            {Enrollment.is_active: False, Enrollment.dropped_at: datetime.utcnow()},
            synchronize_session=False,
        )

    Class.query.filter(
        Class.school_year_id == sy.id,
        Class.is_active.is_(True),
    ).update(
        {Class.is_active: False},
        synchronize_session=False,
    )

    promo_stats = None
    promo_failed = False
    if enrolled_student_ids:
        from utils.report_card_school_year import record_student_year_grades_before_close

        record_student_year_grades_before_close(sy.id, enrolled_student_ids)
        try:
            promo_stats = _apply_grade_promotion_after_year_close(enrolled_student_ids)
        except Exception:
            current_app.logger.exception("Grade promotion after school year close failed")
            promo_failed = True

    sy.is_active = False
    db.session.commit()

    msg = (
        f"School year {sy.name} closed. "
        f"Report cards saved: {ok_n}. Skipped (no active enrollment in this year): {skip_n}. Errors: {err_n}."
    )
    if promo_stats:
        msg += (
            f" Grade promotion: {promo_stats['promoted']} moved up; "
            f"{promo_stats['repeating_cleared']} repeating (grade unchanged, flag cleared); "
            f"{promo_stats['skipped']} unchanged (e.g. no grade or already 12th); "
            f"{promo_stats['provisioned_accounts']} new portal accounts for eligible grades."
        )
    if promo_failed:
        msg += " Grade promotion failed — review logs and update grades or accounts manually."
    flash_level = "success" if err_n == 0 and not promo_failed else "warning"
    if promo_failed:
        flash_level = "danger"
    flash(msg, flash_level)
    if errors_sample:
        flash('Examples: ' + '; '.join(errors_sample), 'warning')

    return redirect(url_for('management.report_cards'))

