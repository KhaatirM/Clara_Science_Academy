"""Warnings for report card grades whose templates or calculations are not finalized."""

from __future__ import annotations

# Grade integers (0 = Kindergarten).
REPORT_CARD_UNFINALIZED_GRADE_LEVELS = frozenset({0, 2})

_GRADE_LABELS = {
    0: 'Kindergarten',
    2: '2nd grade',
}


def _normalize_grade(grade_level) -> int | None:
    try:
        return int(grade_level)
    except (TypeError, ValueError):
        return None


def is_report_card_grade_unfinalized(grade_level) -> bool:
    g = _normalize_grade(grade_level)
    return g is not None and g in REPORT_CARD_UNFINALIZED_GRADE_LEVELS


def report_card_unfinalized_banner_message(grade_level) -> str | None:
    """Short message for inline banners on the generate form."""
    g = _normalize_grade(grade_level)
    if g is None or g not in REPORT_CARD_UNFINALIZED_GRADE_LEVELS:
        return None
    label = _GRADE_LABELS.get(g, f'Grade {g}')
    return (
        f'{label} report cards are not finalized yet and may not display or calculate correctly. '
        'Use other grade bands until this template is complete.'
    )


def report_card_unfinalized_confirm_message(grade_level) -> str | None:
    """Message for a confirm() dialog before generating."""
    g = _normalize_grade(grade_level)
    if g is None or g not in REPORT_CARD_UNFINALIZED_GRADE_LEVELS:
        return None
    label = _GRADE_LABELS.get(g, f'Grade {g}')
    return (
        f'Warning: {label} report cards are not finalized and may not work properly.\n\n'
        'Do you still want to generate this report card?'
    )


def report_card_warnings_template_context() -> dict:
    """Template variables for report card generate UI."""
    grades = sorted(REPORT_CARD_UNFINALIZED_GRADE_LEVELS)
    return {
        'report_card_unfinalized_grades': grades,
        'report_card_unfinalized_confirm_messages': {
            str(g): report_card_unfinalized_confirm_message(g)
            for g in grades
        },
        'report_card_unfinalized_banner_messages': {
            str(g): report_card_unfinalized_banner_message(g)
            for g in grades
        },
    }
