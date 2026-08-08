"""Helpers for Kindergarten progress report PDF layout."""

from utils.report_card_grade3 import (
    QUARTER_DISPLAY,
    QUARTER_KEYS,
    build_attendance_by_quarter,
    build_report_period_label,
    _attendance_cell,
)


def kindergarten_template_context(student_id, school_year_id, selected_quarters, include_attendance=True):
    quarters = [q for q in (selected_quarters or []) if q in QUARTER_KEYS] or ['Q1']
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
        'quarter_display': QUARTER_DISPLAY,
    }


def kindergarten_full_template_context(
    student_id,
    school_year_id,
    selected_quarters,
    include_attendance=True,
    report_card_data=None,
):
    ctx = kindergarten_template_context(
        student_id, school_year_id, selected_quarters, include_attendance=include_attendance
    )
    from utils.report_card_kindergarten_standards import kindergarten_standards_context
    ctx.update(kindergarten_standards_context(
        report_card_data,
        student_id=student_id,
        school_year_id=school_year_id,
    ))
    return ctx
