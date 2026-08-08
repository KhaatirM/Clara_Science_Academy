"""Helpers for 2nd grade progress report PDF layout (director format)."""

from utils.report_card_grade3 import (
    QUARTER_DISPLAY,
    QUARTER_KEYS,
    build_attendance_by_quarter,
    build_report_period_label,
    _attendance_cell,
)
from utils.report_card_grade1 import progress_comment_for_grade1


def build_grade2_course_progress_rows(class_objects, grades):
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


def grade2_template_context(student_id, school_year_id, selected_quarters, class_objects, grades, include_attendance=True):
    """Bundle template variables for 2nd grade report card PDFs (page 1)."""
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
        'course_progress_rows': build_grade2_course_progress_rows(class_objects, grades),
        'quarter_display': QUARTER_DISPLAY,
    }


def grade2_full_template_context(student_id, school_year_id, selected_quarters, class_objects, grades,
                                 include_attendance=True, report_card_data=None):
    """Page 1 + standards pages context for 2nd grade PDFs."""
    ctx = grade2_template_context(
        student_id, school_year_id, selected_quarters, class_objects, grades, include_attendance
    )
    from utils.report_card_grade2_standards import grade2_standards_context
    ctx.update(grade2_standards_context(
        report_card_data,
        student_id=student_id,
        school_year_id=school_year_id,
    ))
    return ctx
