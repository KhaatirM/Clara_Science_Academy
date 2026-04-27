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


def requires_explicit_submission_for_file_assignment(assignment):
    """
    File / paper-style assignments: a numeric grade should only be stored when
    the teacher has marked submission as online or in-person (not auto-inferred from points).
    """
    t = (getattr(assignment, 'assignment_type', None) or '').lower()
    return t in ('pdf', 'paper', 'pdf_paper')


def submission_record_confirmed_for_grading(submission):
    """True when submission exists and is explicitly online or in-person."""
    if submission is None:
        return False
    st = (getattr(submission, 'submission_type', None) or '').lower()
    return st in ('online', 'in_person')
