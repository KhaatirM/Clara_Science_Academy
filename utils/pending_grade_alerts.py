"""Pending-grade alerts for teachers and school administrators.

Counts submissions (online / in-person) that still need a usable teacher score.
Modeled on academic-concerns caching and scope rules.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from flask_login import current_user

_CACHE_TTL_SECONDS = 300
_CACHE_VERSION = 1
_cache_lock = threading.Lock()
_cache: dict[tuple, tuple[float, dict[str, Any]]] = {}


def invalidate_pending_grade_alerts_cache(user_id: int | None = None) -> None:
    """Drop cached pending-grade payloads for one user, or everyone."""
    with _cache_lock:
        if user_id is None:
            _cache.clear()
            return
        stale = [k for k in _cache if k[0] == user_id]
        for key in stale:
            _cache.pop(key, None)


def _parse_grade_data(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        data = raw if isinstance(raw, dict) else json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _has_usable_score(grade_data: dict[str, Any] | None) -> bool:
    """True when the teacher has recorded a real score (including intentional 0 / auto-zero)."""
    if not grade_data or grade_data.get("is_voided"):
        return False
    from utils.grade_helpers import get_points_earned

    pe = get_points_earned(grade_data)
    if pe is None or str(pe).strip() == "":
        return False
    try:
        float(pe)
    except (TypeError, ValueError):
        return False
    # Quiz open-ended auto-score can sit at 0 while still pending manual grading.
    if (grade_data.get("grading_status") or "").lower() == "pending":
        return False
    return True


def _iso(dt: Any) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _grade_url(*, scope: str, class_id: int, assignment_id: int, is_group: bool) -> str:
    kind = "group" if is_group else "individual"
    if scope == "teacher":
        return f"/teacher/assignments-and-grades/{class_id}/{kind}/{assignment_id}/grade"
    return f"/management/assignments/{class_id}/{kind}/{assignment_id}/grade"


def _empty_payload(scope: str) -> dict[str, Any]:
    return {
        "scope": scope,
        "schoolwide": scope == "management",
        "has_active_school_year": False,
        "school_year": None,
        "total_pending": 0,
        "assignment_count": 0,
        "assignments": [],
    }


def _resolve_class_ids(scope: str) -> list[int]:
    from utils.school_year_filters import (
        classes_for_active_school_year,
        teacher_class_ids_active_school_year,
    )
    from utils.user_roles import user_has_management_entry_access

    if scope == "management":
        return [c.id for c in classes_for_active_school_year()]

    from teacher_routes.utils import get_teacher_or_admin

    teacher = get_teacher_or_admin()
    if teacher:
        return teacher_class_ids_active_school_year(teacher.id)
    # Dual-role admin on teacher shell with no teaching load → empty.
    if user_has_management_entry_access(current_user):
        return []
    return []


def _count_individual_pending(assignment, enrolled_ids: set[int]) -> int:
    from models import Grade, Submission

    if not enrolled_ids:
        return 0
    grades = Grade.query.filter(
        Grade.assignment_id == assignment.id,
        Grade.student_id.in_(enrolled_ids),
    ).all()
    grade_by_student = {g.student_id: g for g in grades}
    voided_ids = {g.student_id for g in grades if getattr(g, "is_voided", False)}

    submissions = (
        Submission.query.filter(
            Submission.assignment_id == assignment.id,
            Submission.student_id.in_(enrolled_ids),
            Submission.submission_type.in_(("online", "in_person")),
        ).all()
    )
    pending = 0
    for sub in submissions:
        sid = sub.student_id
        if sid in voided_ids:
            continue
        grade = grade_by_student.get(sid)
        if grade and getattr(grade, "is_voided", False):
            continue
        gdata = _parse_grade_data(grade.grade_data) if grade else None
        if _has_usable_score(gdata):
            continue
        pending += 1
    return pending


def _group_applicable_student_ids(group_assignment) -> set[int]:
    from models import StudentGroup, StudentGroupMember

    try:
        sel = group_assignment.selected_group_ids
        if sel:
            ids = json.loads(sel) if isinstance(sel, str) else sel
            ids = [int(x) for x in ids]
            members = (
                StudentGroupMember.query.join(StudentGroup)
                .filter(
                    StudentGroup.id.in_(ids),
                    StudentGroup.class_id == group_assignment.class_id,
                    StudentGroup.is_active.is_(True),
                )
                .all()
            )
        else:
            members = (
                StudentGroupMember.query.join(StudentGroup)
                .filter(
                    StudentGroup.class_id == group_assignment.class_id,
                    StudentGroup.is_active.is_(True),
                )
                .all()
            )
        return {m.student_id for m in members if m.student_id}
    except Exception:
        return set()


def _count_group_pending(group_assignment, enrolled_ids: set[int]) -> int:
    from models import GroupGrade, GroupSubmission, StudentGroupMember

    applicable = _group_applicable_student_ids(group_assignment) & enrolled_ids
    if not applicable:
        return 0

    grades = GroupGrade.query.filter(
        GroupGrade.group_assignment_id == group_assignment.id,
        GroupGrade.student_id.in_(applicable),
    ).all()
    grade_by_student = {g.student_id: g for g in grades}
    voided_ids = {g.student_id for g in grades if getattr(g, "is_voided", False)}

    submitted: set[int] = set()
    for gg in grades:
        if gg.student_id not in applicable or gg.student_id in voided_ids:
            continue
        gd = _parse_grade_data(gg.grade_data)
        if not gd:
            continue
        if gd.get("submission_type") in ("online", "in_person"):
            submitted.add(gg.student_id)

    for gs in GroupSubmission.query.filter_by(group_assignment_id=group_assignment.id).all():
        if not (gs.attachment_file_path or gs.attachment_filename) or not gs.group_id:
            continue
        for m in StudentGroupMember.query.filter_by(group_id=gs.group_id).all():
            if m.student_id and m.student_id in applicable and m.student_id not in voided_ids:
                submitted.add(m.student_id)

    pending = 0
    for sid in submitted:
        grade = grade_by_student.get(sid)
        if grade and getattr(grade, "is_voided", False):
            continue
        gdata = _parse_grade_data(grade.grade_data) if grade else None
        if _has_usable_score(gdata):
            continue
        pending += 1
    return pending


def get_pending_grade_alerts_for_user(*, force_scope: str | None = None) -> dict[str, Any]:
    """Build pending-grade alert payload for the current user."""
    from decorators import is_teacher_role
    from models import Assignment, Class, GroupAssignment
    from utils.school_year_filters import get_active_school_year
    from utils.student_roster import active_class_roster_students_query
    from utils.user_roles import all_role_strings, user_has_management_entry_access

    is_admin = user_has_management_entry_access(current_user)
    is_teacher = any(is_teacher_role(r) for r in all_role_strings(current_user))

    scope = force_scope or ("management" if is_admin else "teacher")
    if scope == "management" and not is_admin:
        return _empty_payload(scope)
    if scope == "teacher" and not (is_teacher or is_admin):
        return _empty_payload(scope)

    active = get_active_school_year()
    if not active:
        return _empty_payload(scope)

    cache_key = (
        getattr(current_user, "id", None),
        _CACHE_VERSION,
        active.id,
        scope,
    )
    if cache_key[0] is not None:
        now_ts = time.time()
        with _cache_lock:
            entry = _cache.get(cache_key)
            if entry and entry[0] > now_ts:
                return entry[1]

    class_ids = _resolve_class_ids(scope)
    if not class_ids:
        payload = {
            "scope": scope,
            "schoolwide": scope == "management",
            "has_active_school_year": True,
            "school_year": {"id": active.id, "name": active.name},
            "total_pending": 0,
            "assignment_count": 0,
            "assignments": [],
        }
        if cache_key[0] is not None:
            with _cache_lock:
                _cache[cache_key] = (time.time() + _CACHE_TTL_SECONDS, payload)
        return payload

    classes = {c.id: c for c in Class.query.filter(Class.id.in_(class_ids)).all()}
    enrolled_by_class: dict[int, set[int]] = {}
    for cid in class_ids:
        enrolled_by_class[cid] = {s.id for s in active_class_roster_students_query(cid).all()}

    rows: list[dict[str, Any]] = []

    from sqlalchemy import nullslast

    assignments = (
        Assignment.query.filter(
            Assignment.class_id.in_(class_ids),
            Assignment.status != "Voided",
        )
        .order_by(nullslast(Assignment.due_date.asc()))
        .all()
    )
    for assignment in assignments:
        enrolled = enrolled_by_class.get(assignment.class_id) or set()
        pending = _count_individual_pending(assignment, enrolled)
        if pending <= 0:
            continue
        class_obj = classes.get(assignment.class_id)
        rows.append(
            {
                "id": assignment.id,
                "title": assignment.title or "Untitled",
                "class_id": assignment.class_id,
                "class_name": class_obj.name if class_obj else "Unknown",
                "is_group": False,
                "assignment_type": assignment.assignment_type,
                "pending_count": pending,
                "due_date": _iso(assignment.due_date),
                "grade_url": _grade_url(
                    scope=scope,
                    class_id=assignment.class_id,
                    assignment_id=assignment.id,
                    is_group=False,
                ),
            }
        )

    group_assignments = (
        GroupAssignment.query.filter(
            GroupAssignment.class_id.in_(class_ids),
            GroupAssignment.status != "Voided",
        )
        .order_by(nullslast(GroupAssignment.due_date.asc()))
        .all()
    )
    for ga in group_assignments:
        enrolled = enrolled_by_class.get(ga.class_id) or set()
        pending = _count_group_pending(ga, enrolled)
        if pending <= 0:
            continue
        class_obj = classes.get(ga.class_id)
        rows.append(
            {
                "id": ga.id,
                "title": ga.title or "Untitled",
                "class_id": ga.class_id,
                "class_name": class_obj.name if class_obj else "Unknown",
                "is_group": True,
                "assignment_type": ga.assignment_type,
                "pending_count": pending,
                "due_date": _iso(ga.due_date),
                "grade_url": _grade_url(
                    scope=scope,
                    class_id=ga.class_id,
                    assignment_id=ga.id,
                    is_group=True,
                ),
            }
        )

    rows.sort(
        key=lambda r: (
            -int(r.get("pending_count") or 0),
            r.get("due_date") or "9999",
            (r.get("title") or "").lower(),
        )
    )
    total_pending = sum(int(r["pending_count"]) for r in rows)
    payload = {
        "scope": scope,
        "schoolwide": scope == "management",
        "has_active_school_year": True,
        "school_year": {"id": active.id, "name": active.name},
        "total_pending": total_pending,
        "assignment_count": len(rows),
        "assignments": rows,
    }
    if cache_key[0] is not None:
        with _cache_lock:
            _cache[cache_key] = (time.time() + _CACHE_TTL_SECONDS, payload)
    return payload
