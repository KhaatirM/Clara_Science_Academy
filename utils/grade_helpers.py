"""
Shared helpers for grade/score extraction.
Use these to avoid treating 0 as falsy (which breaks 'x or y' patterns).
"""


def get_points_earned(grade_data):
    """
    Safely get points_earned or score from grade_data dict.
    Returns None if neither is present. Correctly handles 0 (zero is a valid grade).
    """
    if grade_data is None:
        return None
    val = grade_data.get('points_earned')
    if val is not None:
        return val
    return grade_data.get('score')


def get_score(grade_data):
    """Alias for get_points_earned for consistency."""
    return get_points_earned(grade_data)


def numeric_score_from_grade_dict(gdict, default=0.0):
    """
    Float score for stats/comparisons. grade_data JSON may store score/points_earned as strings;
    comparing str to int raises TypeError in Python 3.
    """
    if not isinstance(gdict, dict):
        return float(default)
    v = gdict.get('points_earned', gdict.get('score', default))
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)
