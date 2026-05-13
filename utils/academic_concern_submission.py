"""
Align academic-concern / alert detail UI with student-facing submission rules.

A submission row (online / in-person) counts as turned in unless a grade exists
with no positive earned credit (0 or missing numeric score), in which case the
UI treats the item as not submitted for concern badges.
"""
import json


def submission_row_indicates_turned_in(submission):
    return submission is not None and submission.submission_type in ('online', 'in_person')


def grade_row_indicates_entered_grade(grade):
    """True if instructor entered a grade (mirrors get_student_assignment_status)."""
    if not grade or not grade.grade_data:
        return bool(grade and grade.graded_at)
    try:
        grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
        has_score = (
            grade.graded_at
            or (isinstance(grade_data, dict) and (
                grade_data.get('score') is not None
                or grade_data.get('points_earned') is not None
            ))
        )
        return bool(has_score or grade.graded_at)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return bool(grade.graded_at)


def _total_points_for_grade(grade, fallback=100.0):
    a = getattr(grade, "assignment", None)
    if a is None and getattr(grade, "assignment_id", None):
        from models import Assignment

        a = Assignment.query.get(grade.assignment_id)
    v = getattr(a, "total_points", None) if a else None
    try:
        return float(v) if v is not None else float(fallback)
    except (TypeError, ValueError):
        return float(fallback)


def grade_shows_positive_earned_credit(grade) -> bool:
    """
    True only when parsed earned credit is strictly > 0 (percentage or points).
    Unknown / ungraded parses return False.
    """
    if not grade or not getattr(grade, "grade_data", None) or getattr(grade, "is_voided", False):
        return False
    try:
        grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
    except (json.JSONDecodeError, TypeError, AttributeError):
        return False
    if not isinstance(grade_data, dict):
        return False
    from utils.at_risk_alerts import _percentage_from_grade_data

    total_pts = _total_points_for_grade(grade)
    pct, _ = _percentage_from_grade_data(grade_data, total_pts)
    if pct is not None:
        return pct > 0
    return False


def academic_concern_effective_submitted(student_id, assignment_id, grade, submission=None):
    """
    For teacher/admin academic concern panels: submitted if there is positive earned
    credit on a non-voided grade, or a submission row that is not contradicted by
    a recorded zero / non-positive grade.
    """
    from models import Submission

    if submission is None:
        submission = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()

    g = grade if grade and not getattr(grade, "is_voided", False) else None
    has_positive = bool(g and grade_shows_positive_earned_credit(g))
    if has_positive:
        return True

    if submission_row_indicates_turned_in(submission):
        if g and g.grade_data and grade_row_indicates_entered_grade(g):
            if not grade_shows_positive_earned_credit(g):
                return False
        return True

    if g and grade_row_indicates_entered_grade(g):
        return grade_shows_positive_earned_credit(g)
    return False
