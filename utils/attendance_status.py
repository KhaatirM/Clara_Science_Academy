"""Canonical attendance status values for class-period attendance."""

VALID_ATTENDANCE_STATUSES = (
    'Present',
    'Late',
    'Unexcused Absence',
    'Excused Absence',
    'Suspended',
)

# Form radio values are lowercase (see take_attendance.html).
_STATUS_TO_CANONICAL = {
    'present': 'Present',
    'late': 'Late',
    'unexcused absence': 'Unexcused Absence',
    'excused absence': 'Excused Absence',
    'suspended': 'Suspended',
    'absent': 'Unexcused Absence',
}

# Map stored status (any casing) to form radio value for pre-selection.
_STATUS_TO_FORM_VALUE = {
    'present': 'present',
    'late': 'late',
    'unexcused absence': 'unexcused absence',
    'excused absence': 'excused absence',
    'suspended': 'suspended',
    'absent': 'unexcused absence',
}


def normalize_attendance_status(raw: str | None) -> str | None:
    """Return canonical Title Case status, or None if empty."""
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    return _STATUS_TO_CANONICAL.get(key, str(raw).strip())


def attendance_status_form_value(raw: str | None) -> str:
    """Return lowercase form value matching a status_* radio button."""
    if not raw or not str(raw).strip():
        return ''
    key = str(raw).strip().lower()
    return _STATUS_TO_FORM_VALUE.get(key, key)


def count_class_attendance_stats(records, total_students: int) -> dict:
    """Aggregate present/late/absent counts from Attendance rows (any stored casing)."""
    present = late = absent = 0
    for rec in records:
        key = (getattr(rec, 'status', None) or '').strip().lower()
        if key == 'present':
            present += 1
        elif key == 'late':
            late += 1
        elif key in ('absent', 'unexcused absence', 'excused absence'):
            absent += 1
    pct = round((present / total_students * 100) if total_students > 0 else 0, 1)
    return {
        'present': present,
        'late': late,
        'absent': absent,
        'present_percentage': pct,
    }
