"""Helpers for 3rd grade progress report PDF layout (director format)."""

QUARTER_DISPLAY = {
    'Q1': 'First Quarter',
    'Q2': 'Second Quarter',
    'Q3': 'Third Quarter',
    'Q4': 'Fourth Quarter',
}

QUARTER_KEYS = ['Q1', 'Q2', 'Q3', 'Q4']


def _selected_quarters_date_window(school_year_id, quarters_clean):
    """Return (start_date, end_date) for the union of selected quarter periods."""
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


def progress_comment_for_grade(letter):
    """Map letter grade to year-to-date Comment(s) cell, e.g. 'Exceeds Target (A)'."""
    if not letter or str(letter).strip().upper() in ('N/A', 'NA', ''):
        return ''
    L = str(letter).strip().upper()
    if L in ('A+', 'A'):
        tier = 'Exceeds Target'
    elif L == 'B+':
        tier = 'Above Target'
    elif L in ('B', 'B-', 'P'):
        tier = 'On Target'
    elif L in ('C+', 'C', 'C-', 'D', 'D+'):
        tier = 'Below Target'
    else:
        tier = 'Not on Target'
    return f'{tier} ({L})'


def build_report_period_label(school_year_id, quarters_clean):
    """
    e.g. 'March 30, 2025 to May 30, 2025 – Fourth Quarter'
    """
    quarters = [q for q in (quarters_clean or []) if q in QUARTER_KEYS]
    if not quarters:
        return ''

    window_start, window_end = _selected_quarters_date_window(school_year_id, quarters)
    quarter_label = QUARTER_DISPLAY.get(quarters[-1], quarters[-1])

    if window_start and window_end:
        start_fmt = window_start.strftime('%B %d, %Y')
        end_fmt = window_end.strftime('%B %d, %Y')
        return f'{start_fmt} to {end_fmt} – {quarter_label}'

    return f'{quarters[-1]} – {quarter_label}'


def build_attendance_by_quarter(student_id, school_year_id):
    """
    School-day excused / unexcused absence counts per quarter (Q1–Q4).
    Returns {'Q1': {'excused': int, 'unexcused': int}, ...}
    """
    from models import AcademicPeriod, SchoolDayAttendance

    result = {q: {'excused': 0, 'unexcused': 0} for q in QUARTER_KEYS}

    periods = AcademicPeriod.query.filter_by(
        school_year_id=school_year_id,
        period_type='quarter',
    ).filter(AcademicPeriod.name.in_(QUARTER_KEYS)).all()

    for period in periods:
        q = period.name
        if q not in result or not period.start_date or not period.end_date:
            continue
        records = SchoolDayAttendance.query.filter(
            SchoolDayAttendance.student_id == student_id,
            SchoolDayAttendance.date >= period.start_date,
            SchoolDayAttendance.date <= period.end_date,
        ).all()
        for record in records:
            status = (record.status or '').strip()
            if status == 'Excused Absence':
                result[q]['excused'] += 1
            elif status in ('Unexcused Absence', 'Absent', 'Suspended'):
                result[q]['unexcused'] += 1

    return result


def _attendance_cell(count, *, force_show=False):
    """Render one attendance cell.

    - When ``force_show`` is True (attendance is being included) we always
      show a number — even zeros — so the box visibly reflects that
      attendance was pulled.
    - When ``force_show`` is False (the toggle is off) we render blank
      cells so the printed form stays empty.
    """
    if force_show:
        return str(count or 0)
    return str(count) if count else ''


def build_grade3_course_progress_rows(class_objects, grades):
    """Course + Comment(s) rows for the year-to-date progress table."""
    rows = []
    for class_obj in class_objects or []:
        class_grade = {}
        if grades and isinstance(grades, dict):
            class_grade = grades.get(class_obj.id, grades.get(str(class_obj.id), {}))
        if not isinstance(class_grade, dict):
            class_grade = {}
        letter = class_grade.get('letter', 'N/A')
        rows.append({
            'course': class_obj.name,
            'comment': progress_comment_for_grade(letter),
        })
    return rows


def grade3_template_context(student_id, school_year_id, selected_quarters, class_objects, grades, include_attendance=True):
    """Bundle template variables for 3rd grade report card PDFs."""
    quarters = [q for q in (selected_quarters or []) if q in QUARTER_KEYS] or ['Q4']
    attendance = build_attendance_by_quarter(student_id, school_year_id) if include_attendance else {}

    attendance_rows = [
        {
            'label': 'Excused Absences',
            'quarter_counts': [
                _attendance_cell(attendance.get(q, {}).get('excused', 0), force_show=include_attendance)
                for q in QUARTER_KEYS
            ],
        },
        {
            'label': 'Unexcused Absences',
            'quarter_counts': [
                _attendance_cell(attendance.get(q, {}).get('unexcused', 0), force_show=include_attendance)
                for q in QUARTER_KEYS
            ],
        },
    ]

    return {
        'report_period_label': build_report_period_label(school_year_id, quarters),
        'attendance_by_quarter': attendance,
        'attendance_rows': attendance_rows,
        'include_attendance': include_attendance,
        'course_progress_rows': build_grade3_course_progress_rows(class_objects, grades),
    }


def grade3_full_template_context(student_id, school_year_id, selected_quarters, class_objects, grades,
                                 include_attendance=True, report_card_data=None):
    """Page 1 + standards pages context for 3rd grade PDFs."""
    ctx = grade3_template_context(
        student_id, school_year_id, selected_quarters, class_objects, grades, include_attendance
    )
    from utils.report_card_grade3_standards import grade3_standards_context
    ctx.update(grade3_standards_context(
        report_card_data,
        student_id=student_id,
        school_year_id=school_year_id,
    ))
    return ctx
