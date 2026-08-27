"""Management SPA helpers for bell schedule edit and grade master PDFs."""

from __future__ import annotations

from typing import Any

from utils.bell_schedule import (
    available_grade_levels,
    build_bell_grid_for_classes,
    classes_for_grade_level,
    ensure_active_bell_schedule,
    grade_label,
    replace_bell_schedule_periods,
    serialize_bell_schedule,
)
from utils.bell_schedule_pdf import render_bell_schedule_pdf
from utils.school_year_filters import get_active_school_year


def build_management_bell_schedule_payload() -> dict[str, Any]:
    schedule = ensure_active_bell_schedule()
    year = get_active_school_year()
    grades = available_grade_levels(school_year=year)
    return {
        'bell_schedule': serialize_bell_schedule(schedule),
        'school_year': {'id': year.id, 'name': year.name} if year else None,
        'grades': [{'grade': g, 'label': grade_label(g)} for g in grades],
        'kind_options': [
            {'value': 'class', 'label': 'Class period'},
            {'value': 'break', 'label': 'Break'},
            {'value': 'lunch', 'label': 'Lunch'},
            {'value': 'tutorial', 'label': 'Tutorial'},
            {'value': 'other', 'label': 'Other'},
        ],
        'weekday_options': [
            {'value': 0, 'label': 'Mon'},
            {'value': 1, 'label': 'Tue'},
            {'value': 2, 'label': 'Wed'},
            {'value': 3, 'label': 'Thu'},
            {'value': 4, 'label': 'Fri'},
        ],
        'links': {
            'pdf_grade_template': '/api/spa/management/schedule/grade/{grade}.pdf',
        },
    }


def save_management_bell_schedule(body: dict[str, Any]) -> dict[str, Any]:
    schedule = ensure_active_bell_schedule()
    if not schedule:
        raise ValueError('No active school year — create a school year first.')
    periods = body.get('periods')
    if not isinstance(periods, list):
        raise ValueError('periods must be a list')
    replace_bell_schedule_periods(
        schedule,
        title=body.get('title'),
        periods_payload=periods,
    )
    return {
        'success': True,
        'bell_schedule': serialize_bell_schedule(schedule),
        'message': 'Bell schedule saved.',
    }


def build_grade_master_grid(grade: int) -> dict[str, Any]:
    year = get_active_school_year()
    classes = classes_for_grade_level(grade, school_year=year)
    grid = build_bell_grid_for_classes(classes, role='student')
    return {
        **grid,
        'grade': grade,
        'grade_label': grade_label(grade),
        'class_count': len(classes),
        'classes': [
            {
                'id': c.id,
                'name': c.name or '',
                'subject': c.subject or '',
                'grade_levels': c.get_grade_levels() or [],
            }
            for c in classes
        ],
    }


def render_grade_master_pdf(grade: int):
    data = build_grade_master_grid(grade)
    bell = data.get('bell_schedule') or {}
    title = bell.get('title') or 'Bell Schedule'
    subtitle = f'{data["grade_label"]} master schedule'
    year = get_active_school_year()
    if year:
        subtitle = f'{year.name} · {subtitle}'
    safe_name = f'grade_{grade}_schedule.pdf'
    return render_bell_schedule_pdf(
        title=title,
        subtitle=subtitle,
        day_columns=data.get('day_columns') or [],
        unmapped=data.get('unmapped') or [],
        filename=safe_name,
    )
