"""When student portal accounts are allowed (grade 4+; K–3 are record-only until 4th grade)."""

# grade_level uses Kindergarten = 0, 1st = 1, …, 12th = 12
MIN_GRADE_LEVEL_FOR_ACTIVE_STUDENT_LOGIN = 4


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
