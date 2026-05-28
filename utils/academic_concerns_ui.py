"""UI helpers for the academic concerns toast (visibility rules)."""

from flask import request


def academic_concerns_popup_disabled():
    """
    Return True when the academic concerns toast should not appear on this request.
    """
    try:
        ep = request.endpoint or ''
        if not ep:
            return False

        # Report card tab and related flows
        if 'report_card' in ep:
            return True

        # Assignments & Grades → class detail (class_id selected)
        if ep in (
            'management.assignments_and_grades',
            'teacher.dashboard.assignments_and_grades',
        ):
            if (request.args.get('class_id') or '').strip():
                return True

        # Management class assignments detail (alternate entry to class assignment view)
        if ep == 'management.classes.class_assignments':
            return True

        return False
    except Exception:
        return False
