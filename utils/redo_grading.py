"""Close out a granted redo when a teacher saves the student's grade.

Without this, an ``AssignmentRedo`` row keeps ``final_grade = NULL`` forever and
the redo dashboard reports it as "Pending" even though the work was graded.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Penalty for a redo submitted after its deadline, as a share of total points.
REDO_LATE_PENALTY_RATE = 0.10


def _round(value: float) -> float:
    return round(float(value), 2)


def finalize_redo_for_grade(
    *,
    assignment_id: int,
    student_id: int,
    grade_data: dict[str, Any],
    late_penalty_already_applied: bool = False,
) -> dict[str, Any] | None:
    """Record a redo's score and final grade, updating ``grade_data`` in place.

    ``grade_data`` is the dict about to be stored on the ``Grade`` row. When the
    student has an outstanding redo, the school's policy is to keep the higher of
    the original and redo scores, so the stored score is rewritten to that value.

    Returns a summary dict when a redo was closed out, otherwise None.
    """
    from models import AssignmentRedo

    redo = (
        AssignmentRedo.query.filter_by(assignment_id=assignment_id, student_id=student_id)
        .order_by(AssignmentRedo.granted_at.desc())
        .first()
    )
    if not redo:
        return None

    try:
        awarded = float(grade_data.get('points_earned') or 0)
    except (TypeError, ValueError):
        return None
    try:
        total_points = float(grade_data.get('total_points') or 0)
    except (TypeError, ValueError):
        total_points = 0.0

    redo.redo_grade = _round(awarded)

    effective = awarded
    # Skip the redo penalty when the normal late-penalty rules already docked this
    # score, so a late redo is never penalized twice.
    if redo.was_redo_late and not late_penalty_already_applied:
        penalty = (total_points or 100.0) * REDO_LATE_PENALTY_RATE
        effective = max(0.0, awarded - penalty)

    original = redo.original_grade
    if original is not None:
        final = max(float(original), effective)
    else:
        final = effective
    redo.final_grade = _round(final)

    # A graded redo counts as completed even when the teacher marked a paper copy
    # rather than the student uploading one.
    if not redo.is_used:
        redo.is_used = True
        if not redo.redo_submitted_at:
            redo.redo_submitted_at = datetime.utcnow()

    percentage = (redo.final_grade / total_points * 100) if total_points > 0 else 0.0
    grade_data['score'] = redo.final_grade
    grade_data['points_earned'] = redo.final_grade
    grade_data['percentage'] = round(percentage, 2)
    grade_data['is_redo_final'] = True

    if original is not None:
        if redo.was_redo_late and not late_penalty_already_applied:
            note = (
                f'[REDO: Late redo, {int(REDO_LATE_PENALTY_RATE * 100)}% penalty applied. '
                f'Original: {_round(original)}, Redo: {_round(awarded)}, Final: {redo.final_grade}]'
            )
        else:
            note = (
                f'[REDO: Higher score kept. Original: {_round(original)}, '
                f'Redo: {_round(awarded)}, Final: {redo.final_grade}]'
            )
    else:
        note = f'[REDO: Final score {redo.final_grade}]'

    existing_comment = (grade_data.get('comment') or '').strip()
    # Re-grading should replace the old redo note rather than stack another copy.
    cleaned = '\n'.join(
        line for line in existing_comment.splitlines() if not line.strip().startswith('[REDO:')
    ).strip()
    combined = f'{cleaned}\n{note}'.strip() if cleaned else note
    grade_data['comment'] = combined
    grade_data['feedback'] = combined

    return {
        'redo_id': redo.id,
        'original_grade': original,
        'redo_grade': redo.redo_grade,
        'final_grade': redo.final_grade,
    }


def redo_final_grade_for(assignment_id: int, student_id: int) -> float | None:
    """Final grade recorded for a student's redo, if any."""
    from models import AssignmentRedo

    redo = (
        AssignmentRedo.query.filter_by(assignment_id=assignment_id, student_id=student_id)
        .order_by(AssignmentRedo.granted_at.desc())
        .first()
    )
    return redo.final_grade if redo else None


__all__ = ['finalize_redo_for_grade', 'redo_final_grade_for', 'REDO_LATE_PENALTY_RATE']
