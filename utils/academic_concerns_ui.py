"""UI helpers for the academic concerns toast (visibility rules)."""

from flask import request


def summarize_concern_assignments(missing_assignments_by_class):
    """Count failing vs not-submitted items from a details API assignment map."""
    failing = 0
    missing = 0
    for assignments in (missing_assignments_by_class or {}).values():
        for item in assignments or []:
            if item.get('status') == 'failing':
                failing += 1
            if (item.get('submission_status') or 'not_submitted') != 'submitted':
                missing += 1
    return {'failing_count': failing, 'missing_count': missing}


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
