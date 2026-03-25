"""
Align academic-concern / alert detail UI with student-facing submission rules:
a recorded grade (in-person/paper) counts as submitted even without a Submission row.
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


def academic_concern_effective_submitted(student_id, assignment_id, grade, submission=None):
    """
    For teacher/admin academic concern panels: submitted if online/in-person Submission,
    or a non-voided Grade with entered score/points (graded in person).
    """
    from models import Submission

    if submission is None:
        submission = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
    if submission_row_indicates_turned_in(submission):
        return True
    if grade and not getattr(grade, 'is_voided', False) and grade_row_indicates_entered_grade(grade):
        return True
    return False
