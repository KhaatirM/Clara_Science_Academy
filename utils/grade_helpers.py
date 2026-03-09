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
