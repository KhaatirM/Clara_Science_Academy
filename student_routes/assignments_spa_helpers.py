"""Student assignments list payload for the React SPA."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from flask_login import current_user
from sqlalchemy.orm import joinedload

from management_routes.student_assistant_utils import (
    assignment_student_visibility_filter,
    group_assignment_student_visibility_filter,
)
from models import (
    Assignment,
    AssignmentReopening,
    Class,
    Enrollment,
    ExtensionRequest,
    Grade,
    GroupAssignment,
    GroupAssignmentExtension,
    GroupGrade,
    GroupSubmission,
    RedoRequest,
    SchoolYear,
    Student,
    Submission,
    User,
)
from teacher_routes.assignment_utils import (
    get_effective_assignment_status,
    is_assignment_open_for_student,
)


def _iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _fmt_due(value) -> str | None:
    if not value:
        return None
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y")
    except Exception:
        pass
    return str(value)


def _fmt_open(value) -> str | None:
    if not value:
        return None
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%m/%d/%Y %I:%M %p")
    except Exception:
        pass
    return str(value)


def _creator_name(assignment) -> str:
    creator = getattr(assignment, "effective_creator", None)
    if not creator:
        return "Unknown"
    profile = getattr(creator, "teacher_staff_profile", None)
    if profile:
        name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        if name:
            return name
    student_profile = getattr(creator, "student_profile", None)
    if student_profile:
        name = f"{student_profile.first_name or ''} {student_profile.last_name or ''}".strip()
        if name:
            return name
    name = f"{getattr(creator, 'first_name', '') or ''} {getattr(creator, 'last_name', '') or ''}".strip()
    return name or getattr(creator, "username", None) or "Unknown"


def _type_label(assignment_type: str | None) -> str:
    t = (assignment_type or "pdf").lower()
    if t == "quiz":
        return "Quiz"
    if t == "discussion":
        return "Discussion"
    return "PDF/Paper"


def _grade_info(grade_obj, total_points) -> dict[str, Any]:
    from .routes import _get_points_earned, get_letter_grade

    empty = {
        "has_grade": False,
        "percentage": None,
        "letter": None,
        "feedback": None,
        "feedback_preview": None,
        "display": None,
    }
    if not grade_obj or not grade_obj.grade_data:
        return empty
    try:
        data = json.loads(grade_obj.grade_data) if isinstance(grade_obj.grade_data, str) else grade_obj.grade_data
    except (json.JSONDecodeError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    raw_score = _get_points_earned(data)
    score: float | None
    if raw_score is None:
        score = None
    elif isinstance(raw_score, str):
        cleaned = raw_score.strip()
        if not cleaned or cleaned.upper() in {"N/A", "NA", "NONE", "-", "NULL"}:
            score = None
        else:
            try:
                score = float(cleaned)
            except ValueError:
                score = None
    else:
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = None

    # Placeholder rows (score "N/A") are not graded — keep Submit/Extension available.
    if score is None:
        return empty

    total = total_points or 100.0
    percentage = None
    if total:
        try:
            percentage = round(float(score) / float(total) * 100, 1)
        except (TypeError, ValueError, ZeroDivisionError):
            percentage = None
    feedback = (data.get("feedback") or data.get("comment") or data.get("comments") or "").strip() or None
    letter = get_letter_grade(percentage) if percentage is not None else None
    display = f"{percentage}%" if percentage is not None else "Graded"
    return {
        "has_grade": True,
        "percentage": percentage,
        "letter": letter,
        "feedback": feedback,
        "feedback_preview": (feedback[:120] + "…") if feedback and len(feedback) > 120 else feedback,
        "display": display,
    }


def _primary_action(
    assignment,
    *,
    bucket: str,
    attempts_remaining,
    has_submission: bool = False,
    has_grade: bool = False,
) -> dict[str, Any] | None:
    if bucket == "upcoming":
        return {"label": "Not yet available", "url": None, "kind": "locked", "disabled": True}
    if bucket == "inactive":
        # View button opens SPA detail modal; no classic fallback.
        return None
    atype = (assignment.assignment_type or "pdf").lower()
    if atype == "quiz":
        label = (
            f"Retake quiz ({attempts_remaining} left)"
            if attempts_remaining and attempts_remaining > 0
            else "Take quiz"
        )
        return {"label": label, "url": f"/app/student/take-quiz/{assignment.id}", "kind": "quiz", "disabled": False}
    if atype == "discussion":
        return {
            "label": "Open discussion",
            "url": f"/app/student/discussion/{assignment.id}",
            "kind": "discussion",
            "disabled": False,
        }
    if has_grade:
        return None
    return {
        "label": "Resubmit" if has_submission else "Submit",
        "url": None,
        "kind": "submit",
        "disabled": False,
    }


def _serialize_card(
    assignment,
    *,
    submission,
    student_status: str,
    attempts_remaining,
    is_group: bool,
    student_group,
    grade_obj,
    bucket: str,
    extension_req=None,
    redo_req=None,
) -> dict[str, Any]:
    group_name = None
    group_leader = None
    if is_group and student_group:
        group_name = student_group.name
        leader = next((m for m in (student_group.members or []) if m.is_leader), None)
        if leader and leader.student:
            group_leader = f"{leader.student.first_name} {leader.student.last_name}".strip()

    grade = _grade_info(grade_obj, assignment.total_points)
    download_url = None
    if getattr(assignment, "attachment_filename", None):
        download_url = (
            f"/student/download-group-assignment-file/{assignment.id}"
            if is_group
            else f"/student/download-assignment-file/{assignment.id}"
        )

    has_submission = bool(submission)
    can_request_extension = (
        bucket == "active"
        and not is_group
        and not grade["has_grade"]
        and extension_req is None
    )
    can_request_redo = bucket == "inactive" and not is_group and redo_req is None

    return {
        "id": assignment.id,
        "is_group": is_group,
        "title": assignment.title,
        "description": assignment.description or "",
        "description_preview": (
            ((assignment.description or "")[:100] + "…")
            if assignment.description and len(assignment.description) > 100
            else (assignment.description or "")
        ),
        "assignment_type": (assignment.assignment_type or "pdf").lower(),
        "type_label": _type_label(assignment.assignment_type),
        "bucket": bucket,
        "class_id": assignment.class_id,
        "class_name": assignment.class_info.name if assignment.class_info else "Unknown Class",
        "teacher_name": _creator_name(assignment),
        "due_date": _iso(assignment.due_date),
        "due_display": _fmt_due(assignment.due_date) or "No due date",
        "open_date": _iso(getattr(assignment, "open_date", None)),
        "open_display": _fmt_open(getattr(assignment, "open_date", None)),
        "quarter": getattr(assignment, "quarter", None),
        "total_points": assignment.total_points,
        "student_status": student_status,
        "attempts_remaining": attempts_remaining,
        "has_submission": has_submission,
        "group_name": group_name,
        "group_leader": group_leader,
        "grade": grade,
        "attachment_name": getattr(assignment, "attachment_original_filename", None)
        or getattr(assignment, "attachment_filename", None),
        "download_url": download_url,
        "extension": (
            {"status": extension_req.status, "id": extension_req.id} if extension_req else None
        ),
        "redo": ({"status": redo_req.status, "id": redo_req.id} if redo_req else None),
        "can_request_extension": can_request_extension,
        "can_request_redo": can_request_redo,
        "primary_action": _primary_action(
            assignment,
            bucket=bucket,
            attempts_remaining=attempts_remaining,
            has_submission=has_submission,
            has_grade=bool(grade["has_grade"]),
        ),
        "legacy_url": f"/student/assignments?legacy=1&class_id={assignment.class_id}",
    }


def _serialize_low_grades(student: Student) -> dict[str, Any]:
    from .routes import _get_low_grade_data

    raw = _get_low_grade_data(student)
    items = []
    for item in raw.get("low_grade_assignments") or []:
        a = item["assignment"]
        items.append(
            {
                "assignment_id": a.id,
                "title": a.title,
                "class_name": item["class_name"],
                "class_id": item.get("class_id"),
                "percentage": item["percentage"],
                "letter": item["letter"],
                "points_earned": item.get("points_earned"),
                "total_points": item.get("total_points"),
                "feedback": item.get("feedback") or "",
                "assignment_type": item.get("assignment_type") or "pdf",
                "is_group": bool(item.get("is_group")),
                "graded_at": _iso(item.get("graded_at")),
                "graded_display": _fmt_due(item.get("graded_at")),
                "legacy_url": f"/student/assignments?legacy=1&class_id={item.get('class_id') or ''}",
            }
        )
    return {
        "threshold": raw.get("threshold", 70),
        "items": items,
        "classes": raw.get("low_grade_classes") or [],
        "summary": raw.get("low_grade_summary") or {},
    }


def build_student_assignments_payload(
    *,
    class_id: int | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    from .routes import (
        get_student_assignment_status,
        get_student_group_assignment_status,
        resolve_student_group_for_group_assignment,
    )

    try:
        sid = getattr(current_user, "student_id", None)
        if not sid:
            return None, "No student profile linked to this account"
        student = Student.query.get(sid)
        if not student:
            return None, "Student not found"
    except Exception as exc:
        return None, str(exc)

    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    empty_filters = {
        "class_id": class_id,
        "status": status or "",
        "start_date": start_date or "",
        "end_date": end_date or "",
    }
    if not current_school_year:
        return (
            {
                "has_active_school_year": False,
                "filters": empty_filters,
                "classes": [],
                "upcoming": [],
                "active": [],
                "inactive": [],
                "counts": {"upcoming": 0, "active": 0, "inactive": 0},
                "low_grades": _serialize_low_grades(student),
                "links": {"legacy": "/student/assignments?legacy=1"},
            },
            None,
        )

    enrollments = (
        Enrollment.query.filter_by(student_id=student.id, is_active=True)
        .join(Class)
        .filter(Class.school_year_id == current_school_year.id)
        .all()
    )
    classes = [e.class_info for e in enrollments if e.class_info]
    class_ids = [e.class_id for e in enrollments]
    filter_class_id = class_id
    filter_status = (status or "").strip()

    query = Assignment.query.options(
        joinedload(Assignment.creator).joinedload(User.teacher_staff_profile)
    ).filter(
        Assignment.class_id.in_(class_ids),
        Assignment.school_year_id == current_school_year.id,
        Assignment.status.in_(["Active", "Inactive", "Upcoming", "Voided"]),
        assignment_student_visibility_filter(),
    )
    if filter_class_id:
        query = query.filter(Assignment.class_id == filter_class_id)
    if filter_status in ("Active", "Inactive", "Upcoming", "Voided"):
        query = query.filter(Assignment.status == filter_status)
    if start_date:
        try:
            query = query.filter(Assignment.due_date >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Assignment.due_date <= end_dt)
        except ValueError:
            pass

    assignments = query.order_by(Assignment.due_date.asc()).all() if class_ids else []
    submissions_dict = {s.assignment_id: s for s in Submission.query.filter_by(student_id=student.id).all()}
    grades_dict: dict[int, Any] = {g.assignment_id: g for g in Grade.query.filter_by(student_id=student.id).all()}
    for g in GroupGrade.query.filter_by(student_id=student.id).all():
        grades_dict[g.group_assignment_id] = g

    extension_requests_by_assignment = {
        r.assignment_id: r
        for r in ExtensionRequest.query.filter_by(student_id=student.id)
        .filter(ExtensionRequest.status.in_(["Pending", "Approved"]))
        .all()
    }
    redo_requests_by_assignment = {
        r.assignment_id: r
        for r in RedoRequest.query.filter_by(student_id=student.id)
        .filter(RedoRequest.status.in_(["Pending", "Approved"]))
        .all()
    }

    inactive_raw: list = []
    active_raw: list = []
    upcoming_raw: list = []

    for assignment in assignments:
        submission = submissions_dict.get(assignment.id)
        grade = grades_dict.get(assignment.id)
        student_status = get_student_assignment_status(assignment, submission, grade, student.id)
        attempts_remaining = None
        quiz_lockout = False
        if assignment.assignment_type == "quiz" and assignment.max_attempts:
            submissions_count = Submission.query.filter_by(
                student_id=student.id, assignment_id=assignment.id
            ).count()
            active_reopening = AssignmentReopening.query.filter_by(
                assignment_id=assignment.id, student_id=student.id, is_active=True
            ).first()
            effective_max = assignment.max_attempts
            if active_reopening and active_reopening.additional_attempts > 0:
                effective_max = (assignment.max_attempts or 0) + active_reopening.additional_attempts
            attempts_remaining = max(0, (effective_max or 0) - submissions_count) if effective_max else None
            quiz_lockout = bool(submission) and attempts_remaining == 0

        if assignment.status == "Voided" or student_status == "Voided":
            continue
        lifecycle = get_effective_assignment_status(assignment)
        if lifecycle == "Voided":
            continue
        can_submit_now = is_assignment_open_for_student(assignment, student.id)
        if quiz_lockout:
            can_submit_now = False
        row = (
            assignment,
            submission,
            student_status,
            attempts_remaining,
            False,
            None,
            grade,
        )
        if lifecycle == "Upcoming":
            (active_raw if can_submit_now else upcoming_raw).append(row)
        elif lifecycle == "Inactive":
            (active_raw if can_submit_now else inactive_raw).append(row)
        else:
            (inactive_raw if quiz_lockout else active_raw).append(row)

    group_q = GroupAssignment.query.options(
        joinedload(GroupAssignment.creator).joinedload(User.teacher_staff_profile)
    ).filter(
        GroupAssignment.class_id.in_(class_ids),
        GroupAssignment.school_year_id == current_school_year.id,
        GroupAssignment.status.in_(["Active", "Inactive", "Upcoming", "Voided"]),
        group_assignment_student_visibility_filter(),
    )
    if filter_class_id:
        group_q = group_q.filter(GroupAssignment.class_id == filter_class_id)
    if filter_status in ("Active", "Inactive", "Upcoming", "Voided"):
        group_q = group_q.filter(GroupAssignment.status == filter_status)
    if start_date:
        try:
            group_q = group_q.filter(GroupAssignment.due_date >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            group_q = group_q.filter(GroupAssignment.due_date <= end_dt)
        except ValueError:
            pass

    group_assignments_list = group_q.order_by(GroupAssignment.due_date.asc()).all() if class_ids else []
    group_submissions_by_assignment: dict[int, list] = {}
    if group_assignments_list:
        for gs in GroupSubmission.query.filter(
            GroupSubmission.group_assignment_id.in_([ga.id for ga in group_assignments_list])
        ).all():
            group_submissions_by_assignment.setdefault(gs.group_assignment_id, []).append(gs)

    for group_assignment in group_assignments_list:
        if group_assignment.status == "Voided":
            continue
        student_group = resolve_student_group_for_group_assignment(student.id, group_assignment)
        group_submission = None
        if student_group:
            for gs in group_submissions_by_assignment.get(group_assignment.id) or []:
                if gs.group_id == student_group.id:
                    group_submission = gs
                    break
        group_grade = grades_dict.get(group_assignment.id)
        student_status = get_student_group_assignment_status(
            group_assignment, group_submission, group_grade, student.id
        )
        if student_status == "Voided":
            continue
        row = (
            group_assignment,
            group_submission,
            student_status,
            None,
            True,
            student_group,
            group_grade,
        )
        ga_lifecycle = get_effective_assignment_status(group_assignment)
        can_submit_group = False
        if ga_lifecycle == "Inactive":
            _ext = GroupAssignmentExtension.query.filter_by(
                group_assignment_id=group_assignment.id,
                student_id=student.id,
                is_active=True,
            ).first()
            if _ext and _ext.extended_due_date:
                _ed = _ext.extended_due_date
                if isinstance(_ed, datetime) and _ed.tzinfo is None:
                    _ed = _ed.replace(tzinfo=timezone.utc)
                elif not isinstance(_ed, datetime):
                    _ed = datetime.combine(_ed, datetime.min.time()).replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) <= _ed:
                    can_submit_group = True
        if ga_lifecycle == "Upcoming":
            upcoming_raw.append(row)
        elif ga_lifecycle == "Inactive":
            (active_raw if can_submit_group else inactive_raw).append(row)
        else:
            active_raw.append(row)

    def _due_sort_key(item):
        a = item[0]
        d = getattr(a, "due_date", None)
        if d is None:
            return (1, 0)
        ts = d.timestamp() if hasattr(d, "timestamp") else 0
        return (0, -ts)

    for lst in (inactive_raw, active_raw, upcoming_raw):
        lst.sort(key=_due_sort_key)

    def _map_bucket(rows, bucket: str):
        out = []
        for row in rows:
            assignment, submission, student_status, attempts_remaining, is_group, student_group, grade = row
            out.append(
                _serialize_card(
                    assignment,
                    submission=submission,
                    student_status=student_status,
                    attempts_remaining=attempts_remaining,
                    is_group=is_group,
                    student_group=student_group,
                    grade_obj=grade,
                    bucket=bucket,
                    extension_req=None if is_group else extension_requests_by_assignment.get(assignment.id),
                    redo_req=None if is_group else redo_requests_by_assignment.get(assignment.id),
                )
            )
        return out

    upcoming = _map_bucket(upcoming_raw, "upcoming")
    active = _map_bucket(active_raw, "active")
    inactive = _map_bucket(inactive_raw, "inactive")

    return (
        {
            "has_active_school_year": True,
            "school_year_name": current_school_year.name,
            "filters": empty_filters,
            "classes": [{"id": c.id, "name": c.name} for c in classes],
            "upcoming": upcoming,
            "active": active,
            "inactive": inactive,
            "counts": {
                "upcoming": len(upcoming),
                "active": len(active),
                "inactive": len(inactive),
            },
            "low_grades": _serialize_low_grades(student),
            "links": {"legacy": "/student/assignments?legacy=1"},
        },
        None,
    )
