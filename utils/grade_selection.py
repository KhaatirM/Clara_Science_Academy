"""Collapse multiple Grade rows per assignment to one official score.

Quiz retakes intentionally store one Grade row per attempt. Averages, GPA,
quarter grades, and grade lists must use a single representative row
(best attempt for quizzes; newest for other types).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from utils.academic_concern_assignments import pick_representative_grade


def collapse_grades_to_official(grades: Iterable) -> list:
    """
    Return at most one Grade per assignment_id.

    Quizzes use the best attempt; other assignments use the newest non-voided row.
    Rows without an assignment are skipped.
    """
    by_assignment: dict[int, list] = defaultdict(list)
    for grade in grades or []:
        if not grade or getattr(grade, "is_voided", False):
            continue
        assignment = getattr(grade, "assignment", None)
        assignment_id = getattr(grade, "assignment_id", None)
        if assignment is None or assignment_id is None:
            continue
        if getattr(assignment, "status", None) == "Voided":
            continue
        by_assignment[int(assignment_id)].append(grade)

    official: list = []
    for rows in by_assignment.values():
        assignment = rows[0].assignment
        rep = pick_representative_grade(rows, assignment)
        if rep is not None:
            official.append(rep)
    return official
