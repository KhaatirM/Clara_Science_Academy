"""
Build per-assignment academic concern rows (one row per assignment).

Quizzes may have multiple Grade rows (retakes). Concerns, printouts, and badge
counts use the **best** attempt only; passing best scores are omitted entirely.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

FAILING_MAX_PERCENT = 69
PASSING_MIN_PERCENT = 70


def get_points_earned(grade_data):
    if not grade_data or not isinstance(grade_data, dict):
        return None
    val = grade_data.get('points_earned')
    if val is not None:
        return val
    return grade_data.get('score')


def pick_best_quiz_grade_row(grade_rows, assignment_total_points):
    """Highest-percentage quiz attempt; tie-break newest graded_at / id."""
    total_points = assignment_total_points if (assignment_total_points and assignment_total_points > 0) else 100.0
    best = None
    best_pct = None
    best_key = None

    for g in grade_rows or []:
        if not g or getattr(g, 'is_voided', False) or not getattr(g, 'grade_data', None):
            continue
        try:
            gdata = json.loads(g.grade_data) if isinstance(g.grade_data, str) else g.grade_data
        except (json.JSONDecodeError, TypeError):
            continue
        pts = get_points_earned(gdata)
        if pts is None:
            continue
        try:
            pct = (float(pts) / float(total_points) * 100.0) if float(total_points) > 0 else 0.0
        except (ValueError, TypeError):
            continue
        key = (g.graded_at or datetime.min, g.id or 0)
        if best is None or best_pct is None or pct > best_pct or (pct == best_pct and key > best_key):
            best = g
            best_pct = pct
            best_key = key
    return best


def pick_representative_grade(grade_rows, assignment):
    """One grade row per assignment; quizzes use the best attempt."""
    rows = [g for g in (grade_rows or []) if g and not getattr(g, 'is_voided', False)]
    if not rows:
        return None
    atype = (getattr(assignment, 'assignment_type', None) or 'pdf').lower()
    if atype == 'quiz':
        return pick_best_quiz_grade_row(rows, getattr(assignment, 'total_points', None))
    rows.sort(key=lambda g: (g.graded_at or datetime.min, g.id or 0), reverse=True)
    for g in rows:
        if g.grade_data:
            return g
    return rows[0]


def _percentage_for_grade(grade, assignment):
    from utils.at_risk_alerts import _percentage_from_grade_data

    if not grade or not getattr(grade, 'grade_data', None):
        return None
    total_pts = getattr(assignment, 'total_points', None) or 100.0
    try:
        grade_data = (
            json.loads(grade.grade_data)
            if isinstance(grade.grade_data, str)
            else (grade.grade_data or {})
        )
    except (json.JSONDecodeError, TypeError):
        return None
    percentage, _ = _percentage_from_grade_data(grade_data, total_pts)
    return percentage


def _is_quiz_type(assignment_type: str | None) -> bool:
    return (assignment_type or '').lower() in ('quiz', 'group_quiz')


def build_concern_item_for_assignment(student, assignment, grade_rows, now=None):
    """
    Return a concern dict for this assignment, or None if it should not appear.

    Also returns (status, representative_grade) when at-risk for GPA hypotheticals.
    """
    from models import Submission
    from utils.academic_concern_submission import academic_concern_effective_submitted

    now = now or datetime.utcnow()
    rep = pick_representative_grade(grade_rows, assignment)
    percentage = _percentage_for_grade(rep, assignment) if rep else None
    is_quiz = _is_quiz_type(getattr(assignment, 'assignment_type', None))
    is_past_due = bool(assignment.due_date and assignment.due_date < now)

    # Quiz with a passing best attempt is not a concern.
    if is_quiz and percentage is not None and percentage >= PASSING_MIN_PERCENT:
        return None

    status = None
    is_at_risk = False
    if percentage is None:
        if is_past_due:
            is_at_risk = True
            status = 'missing'
    elif percentage <= FAILING_MAX_PERCENT:
        is_at_risk = True
        status = 'failing'

    if not is_at_risk:
        return None

    awaiting_grade = False
    if status == 'failing' and percentage is not None and percentage == 0:
        sub = Submission.query.filter_by(
            student_id=student.id, assignment_id=assignment.id
        ).first()
        if sub and sub.submission_type in ('online', 'in_person'):
            awaiting_grade = True
    if awaiting_grade:
        return None

    sub = Submission.query.filter_by(
        student_id=student.id, assignment_id=assignment.id
    ).first()
    if is_quiz and rep is not None:
        submitted = True
    else:
        submitted = academic_concern_effective_submitted(
            student.id, assignment.id, rep, sub
        )

    score_display: Any
    if percentage is not None:
        score_display = round(float(percentage), 1)
    else:
        score_display = 'N/A'

    item = {
        'assignment_id': assignment.id,
        'title': assignment.title,
        'due_date': (
            assignment.due_date.strftime('%Y-%m-%d')
            if assignment.due_date
            else 'No due date'
        ),
        'quarter': assignment.quarter or '',
        'status': status,
        'score': score_display,
        'assignment_type': assignment.assignment_type or 'pdf',
        'submission_status': 'submitted' if submitted else 'not_submitted',
        'is_quiz': is_quiz,
        'score_label': 'Best score' if is_quiz and percentage is not None else 'Score',
    }
    if is_quiz and status == 'missing':
        item['submission_status'] = 'not_submitted'

    return {
        'item': item,
        'status': status,
        'representative_grade': rep,
    }


def build_missing_assignments_from_grades(student, all_grades, now=None):
    """
    One concern row per assignment (quiz retakes collapsed to best attempt).

    Returns (missing_assignments_by_class, at_risk_grades_list, grades_by_class).
    """
    now = now or datetime.utcnow()
    by_assignment: dict[int, list] = {}
    grades_by_class: dict[int, list] = {}

    for g in all_grades or []:
        if not g.assignment or not g.assignment.class_info:
            continue
        class_id = g.assignment.class_id
        grades_by_class.setdefault(class_id, []).append(g)
        by_assignment.setdefault(g.assignment_id, []).append(g)

    missing_assignments_by_class: dict[str, list] = {}
    at_risk_grades_list = []

    for _assignment_id, glist in by_assignment.items():
        assignment = glist[0].assignment
        try:
            result = build_concern_item_for_assignment(student, assignment, glist, now)
            if not result:
                continue
            item = result['item']
            class_name = assignment.class_info.name
            missing_assignments_by_class.setdefault(class_name, []).append(item)
            if result['status'] == 'failing' and result['representative_grade'] is not None:
                at_risk_grades_list.append(result['representative_grade'])
        except Exception:
            continue

    return missing_assignments_by_class, at_risk_grades_list, grades_by_class


def append_group_concern_item(
    missing_assignments_by_class,
    at_risk_grades_list,
    *,
    student,
    class_name,
    title,
    due_date,
    quarter,
    assignment_type,
    status,
    score,
    submission_status,
    group_grade=None,
):
    """Append a group-assignment concern row (already evaluated)."""
    is_quiz = _is_quiz_type(assignment_type)
    item = {
        'title': title,
        'due_date': due_date,
        'quarter': quarter or '',
        'status': status,
        'score': score,
        'assignment_type': assignment_type,
        'submission_status': submission_status,
        'is_quiz': is_quiz,
        'score_label': 'Best score' if is_quiz and score not in (None, 'N/A') else 'Score',
    }
    missing_assignments_by_class.setdefault(class_name, []).append(item)
    if status == 'failing' and group_grade is not None:
        at_risk_grades_list.append(group_grade)
