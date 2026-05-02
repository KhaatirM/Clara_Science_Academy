"""Grade 3+ may have portal login and Google Workspace email; K–2 are records-only (no school email until 3rd)."""

# grade_level uses Kindergarten = 0, 1st = 1, …, 12th = 12
MIN_GRADE_LEVEL_FOR_ACTIVE_STUDENT_LOGIN = 3


def parse_grade_level_for_policy(value):
    """Normalize form/CSV grade values to int or None."""
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.strip()
        if v.isdigit() or (len(v) > 1 and v[0] == '-' and v[1:].isdigit()):
            try:
                return int(v)
            except ValueError:
                return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def grade_may_have_login(grade_level):
    """True when this grade should have (or be eligible for) a student User account."""
    gl = parse_grade_level_for_policy(grade_level)
    if gl is None:
        return False
    return gl >= MIN_GRADE_LEVEL_FOR_ACTIVE_STUDENT_LOGIN


def google_workspace_sync_should_skip_student(grade_level) -> bool:
    """
    K–2 (grades 0, 1, 2): skip all Google Directory API calls in bulk/real-time sync.
    If grade cannot be parsed, do not skip (legacy rows with missing grade still sync).
    """
    gl = parse_grade_level_for_policy(grade_level)
    if gl is None:
        return False
    return gl < MIN_GRADE_LEVEL_FOR_ACTIVE_STUDENT_LOGIN
