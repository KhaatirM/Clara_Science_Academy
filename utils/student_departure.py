"""Student year-end intent and departure (graduate / withdraw) helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from extensions import db
from models import Enrollment, Student

YEAR_END_INTENTS = frozenset({"promote", "graduate", "withdraw", "repeat"})
DEPARTURE_STATUSES = frozenset({"graduated", "withdrawn"})


def normalize_year_end_intent(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip().lower()
    if raw in YEAR_END_INTENTS:
        return raw
    return None


def effective_year_end_intent(student: Student | None) -> str:
    """Intent applied at year finalize. Missing → promote; repeating flag → repeat."""
    if student is None:
        return "promote"
    intent = normalize_year_end_intent(getattr(student, "year_end_intent", None))
    if intent:
        return intent
    if bool(getattr(student, "is_repeating", False)):
        return "repeat"
    return "promote"


def set_year_end_intent(student: Student, intent: str | None) -> str:
    """Stage year-end outcome. Returns the normalized intent (promote if cleared)."""
    normalized = normalize_year_end_intent(intent) or "promote"
    student.year_end_intent = normalized if normalized != "promote" else None
    if normalized == "repeat":
        student.is_repeating = True
    elif normalized == "promote":
        student.is_repeating = False
    student.status_updated_at = datetime.now(timezone.utc)
    return normalized


def _deactivate_enrollments(student_id: int) -> None:
    now = datetime.now(timezone.utc)
    for enr in Enrollment.query.filter_by(student_id=student_id).all():
        enr.is_active = False
        if hasattr(enr, "dropped_at") and enr.dropped_at is None:
            enr.dropped_at = now


def _strip_and_suspend(student: Student) -> None:
    """Best-effort portal login removal + Workspace suspend (lazy import)."""
    from management_routes.students import (
        _strip_student_user_account,
        _student_workspace_email,
        _suspend_student_google_workspace,
    )

    ws_email = _student_workspace_email(student)
    _strip_student_user_account(student)
    if ws_email:
        _suspend_student_google_workspace(student, workspace_email=ws_email)


def promote_student_one_grade(student: Student) -> bool:
    """
    Immediately promote live grade by one. Returns False if skipped.
    Clears year_end_intent / repeating for a clean active-year grade.
    """
    if student is None or getattr(student, "is_deleted", False):
        return False
    if getattr(student, "departure_status", None) in DEPARTURE_STATUSES:
        return False
    if not bool(getattr(student, "is_active", True)):
        return False
    gl = getattr(student, "grade_level", None)
    if gl is None:
        return False
    if int(gl) >= 12:
        return False
    student.grade_level = int(gl) + 1
    student.year_end_intent = None
    student.is_repeating = False
    student.status_updated_at = datetime.now(timezone.utc)
    try:
        from models import SchoolYear
        from utils.report_card_school_year import upsert_student_school_year

        active = SchoolYear.query.filter_by(is_active=True).first()
        if active:
            upsert_student_school_year(
                student.id, active.id, int(student.grade_level), enrolled=True
            )
    except Exception:
        pass
    return True


def apply_outcome_now(student: Student, action: str) -> str:
    """
    Apply promote / graduate / withdraw / repeat immediately.
    Returns a short result label: promoted|graduated|withdrawn|repeating|skipped.
    """
    action_n = normalize_year_end_intent(action) or ""
    if not action_n:
        return "skipped"
    if getattr(student, "is_deleted", False) and action_n != "withdraw":
        return "skipped"
    if getattr(student, "departure_status", None) in DEPARTURE_STATUSES:
        return "skipped"

    if action_n == "promote":
        return "promoted" if promote_student_one_grade(student) else "skipped"
    if action_n == "graduate":
        mark_student_graduated(student, strip_login=True)
        return "graduated"
    if action_n == "withdraw":
        mark_student_withdrawn(student, strip_login=True)
        return "withdrawn"
    if action_n == "repeat":
        set_year_end_intent(student, "repeat")
        student.is_repeating = True
        grad_year = getattr(student, "grad_year", None)
        if not grad_year and student.expected_grad_date and "/" in str(student.expected_grad_date):
            try:
                grad_year = int(str(student.expected_grad_date).split("/", 1)[1])
            except Exception:
                grad_year = None
        if grad_year:
            student.grad_year = int(grad_year) + 1
        return "repeating"
    return "skipped"


def mark_student_graduated(student: Student, *, strip_login: bool = True) -> None:
    """
    Off active roster as middle-school (or division) graduate. Keep profile (not deleted).
    Grade stays as completed (e.g. 8).
    """
    student.is_active = False
    student.is_deleted = False
    student.marked_for_removal = False
    student.departure_status = "graduated"
    student.year_end_intent = None
    student.is_repeating = False
    student.status_updated_at = datetime.now(timezone.utc)
    _deactivate_enrollments(student.id)
    if strip_login:
        _strip_and_suspend(student)


def mark_student_withdrawn(student: Student, *, strip_login: bool = True) -> None:
    """Same as soft-remove / former student; explicit withdrawn departure."""
    now = datetime.now(timezone.utc)
    student.is_deleted = True
    student.deleted_at = now
    student.marked_for_removal = False
    student.is_active = False
    student.departure_status = "withdrawn"
    student.year_end_intent = None
    student.is_repeating = False
    student.status_updated_at = now
    _deactivate_enrollments(student.id)
    if strip_login:
        _strip_and_suspend(student)


def apply_year_end_outcomes(student_ids: Iterable[int]) -> dict[str, int]:
    """
    Apply staged year-end intents for the given enrolled student IDs.

    Returns stats: promoted, graduated, withdrawn, repeating_cleared, skipped,
    provisioned_accounts.
    """
    from datetime import datetime as dt

    from management_routes.students import _provision_student_login_if_needed

    stats = {
        "promoted": 0,
        "graduated": 0,
        "withdrawn": 0,
        "repeating_cleared": 0,
        "skipped": 0,
        "provisioned_accounts": 0,
    }
    ids = list(student_ids)
    for sid in ids:
        student = Student.query.get(sid)
        if not student or getattr(student, "is_deleted", False):
            stats["skipped"] += 1
            continue
        if getattr(student, "departure_status", None) in DEPARTURE_STATUSES:
            stats["skipped"] += 1
            continue

        intent = effective_year_end_intent(student)
        if intent == "withdraw":
            mark_student_withdrawn(student)
            stats["withdrawn"] += 1
            continue
        if intent == "graduate":
            mark_student_graduated(student)
            stats["graduated"] += 1
            continue
        if intent == "repeat" or student.is_repeating:
            student.is_repeating = False
            student.year_end_intent = None
            student.status_updated_at = dt.utcnow()
            stats["repeating_cleared"] += 1
            continue

        gl = student.grade_level
        if gl is None:
            stats["skipped"] += 1
            continue
        if int(gl) >= 12:
            student.year_end_intent = None
            stats["skipped"] += 1
            continue
        student.grade_level = int(gl) + 1
        student.year_end_intent = None
        student.status_updated_at = dt.utcnow()
        stats["promoted"] += 1

    for sid in ids:
        student = Student.query.get(sid)
        if not student or getattr(student, "is_deleted", False):
            continue
        if not bool(getattr(student, "is_active", True)):
            continue
        if getattr(student, "departure_status", None) in DEPARTURE_STATUSES:
            continue
        if _provision_student_login_if_needed(student):
            stats["provisioned_accounts"] += 1

    return stats


def list_eighth_graders_for_school_year(school_year_id: int) -> list[Student]:
    """Active (non-deleted) students enrolled in the year whose current grade is 8."""
    from models import Class

    student_ids = {
        row[0]
        for row in (
            db.session.query(Enrollment.student_id)
            .join(Class, Class.id == Enrollment.class_id)
            .filter(Class.school_year_id == school_year_id)
            .distinct()
            .all()
        )
    }
    if not student_ids:
        return []
    return (
        Student.query.filter(
            Student.id.in_(student_ids),
            Student.is_deleted.is_(False),
            Student.grade_level == 8,
        )
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
