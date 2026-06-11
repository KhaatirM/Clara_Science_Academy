"""Helpers for 1st grade progress report PDF layout (director format)."""

from utils.report_card_grade3 import (
    QUARTER_DISPLAY,
    QUARTER_KEYS,
    build_attendance_by_quarter,
    build_report_period_label,
    _attendance_cell,
)

def progress_comment_for_grade1(letter):
    """Map letter grade to year-to-date Comment(s) cell, e.g. 'Above Target'."""
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
    return tier


def build_grade1_course_progress_rows(class_objects, grades):
    """Course + Comment(s) rows from the classes selected for this report card."""
    rows = []
    for class_obj in class_objects or []:
        class_grade = {}
        if grades and isinstance(grades, dict):
            class_grade = grades.get(class_obj.id, grades.get(str(class_obj.id), {}))
        if not isinstance(class_grade, dict):
            class_grade = {}
        letter = class_grade.get('letter', '')
        rows.append({
            'course': class_obj.name,
            'comment': progress_comment_for_grade1(letter),
        })
    return rows


def grade1_template_context(student_id, school_year_id, selected_quarters, class_objects, grades, include_attendance=True):
    """Bundle template variables for 1st grade report card PDFs (page 1)."""
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
        'course_progress_rows': build_grade1_course_progress_rows(class_objects, grades),
        'quarter_display': QUARTER_DISPLAY,
    }


def grade1_full_template_context(student_id, school_year_id, selected_quarters, class_objects, grades,
                                 include_attendance=True, report_card_data=None):
    """Page 1 + standards pages context for 1st grade PDFs."""
    ctx = grade1_template_context(
        student_id, school_year_id, selected_quarters, class_objects, grades, include_attendance
    )
    from utils.report_card_grade1_standards import grade1_standards_context
    ctx.update(grade1_standards_context(
        report_card_data,
        student_id=student_id,
        school_year_id=school_year_id,
    ))
    return ctx
