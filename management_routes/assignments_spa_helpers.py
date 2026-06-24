"""Assignments & grades hub payloads for the React management SPA."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from flask import url_for
from utils.spa_management_urls import user_should_use_spa_management_shell
from sqlalchemy import func

from extensions import db
from management_routes.classes import query_classes_list, serialize_class_list_item
from management_routes.student_assistant_utils import count_pending_assistant_proposals_for_class
from models import (
    Assignment,
    Class,
    Enrollment,
    Grade,
    GroupAssignment,
    GroupGrade,
    GroupSubmission,
    StudentGroup,
    StudentGroupMember,
    Submission,
)
from utils.grade_helpers import get_points_earned
from utils.school_year_filters import count_pending_extension_requests, count_pending_redo_requests


def _due_ts(d: Any) -> float:
    if d is None:
        return 0.0
    if hasattr(d, "timestamp"):
        return float(d.timestamp() if getattr(d, "tzinfo", None) is None else d.replace(tzinfo=None).timestamp())
    if isinstance(d, date) and not isinstance(d, datetime):
        return datetime.combine(d, datetime.min.time()).timestamp()
    return 0.0


def _grade_dict_from_row(grade_data: Any) -> dict[str, Any] | None:
    if grade_data is None:
        return None
    try:
        return grade_data if isinstance(grade_data, dict) else json.loads(grade_data)
    except (json.JSONDecodeError, TypeError):
        return None


def _individual_assignment_stats(assignment: Assignment, enrolled_ids: set[int]) -> dict[str, Any]:
    grades = Grade.query.filter_by(assignment_id=assignment.id).all()
    total_submissions = (
        Submission.query.filter_by(assignment_id=assignment.id)
        .filter(Submission.submission_type != "not_submitted")
        .count()
    )
    graded_grades: list[dict[str, Any]] = []
    total_score = 0.0
    for g in grades:
        if g.is_voided:
            continue
        grade_dict = _grade_dict_from_row(g.grade_data)
        if not grade_dict or grade_dict.get("is_voided"):
            continue
        score_val = get_points_earned(grade_dict)
        if score_val is not None and str(score_val).strip() != "":
            graded_grades.append(grade_dict)
            try:
                total_score += float(score_val)
            except (ValueError, TypeError):
                pass
    total_points = float(assignment.total_points or 100.0)
    avg_pct = (
        round((total_score / len(graded_grades) / total_points * 100), 1)
        if graded_grades and total_points > 0
        else 0
    )
    all_voided = assignment.status == "Voided"
    voided_student_ids = {g.student_id for g in grades if g.is_voided}
    if not all_voided and enrolled_ids:
        all_voided = enrolled_ids <= voided_student_ids
    partially_voided = not all_voided and bool(voided_student_ids & enrolled_ids)
    return {
        "total_submissions": total_submissions,
        "graded_count": len(graded_grades),
        "average_score": avg_pct,
        "all_voided": all_voided,
        "partially_voided": partially_voided,
        "voided_count": len(voided_student_ids & enrolled_ids),
        "needs_grading": len(graded_grades) == 0,
    }


def _group_assignment_stats(group_assignment: GroupAssignment) -> dict[str, Any]:
    group_grades = GroupGrade.query.filter_by(group_assignment_id=group_assignment.id).all()
    submission_student_ids: set[int] = set()
    for gg in group_grades:
        if gg.grade_data and not gg.is_voided:
            gd = _grade_dict_from_row(gg.grade_data)
            if gd:
                if gd.get("submission_type") in ("in_person", "online"):
                    submission_student_ids.add(gg.student_id)
                else:
                    pe = get_points_earned(gd)
                    if pe is not None and str(pe).strip() != "":
                        submission_student_ids.add(gg.student_id)
    for gs in GroupSubmission.query.filter_by(group_assignment_id=group_assignment.id).all():
        if (gs.attachment_file_path or gs.attachment_filename) and gs.group_id:
            for m in StudentGroupMember.query.filter_by(group_id=gs.group_id).all():
                if m.student_id:
                    submission_student_ids.add(m.student_id)
    graded_group_grades: list[dict[str, Any]] = []
    total_score = 0.0
    for gg in group_grades:
        if gg.is_voided:
            continue
        gd = _grade_dict_from_row(gg.grade_data)
        if not gd or gd.get("is_voided"):
            continue
        score_val = get_points_earned(gd)
        if score_val is not None and str(score_val).strip() != "":
            graded_group_grades.append(gd)
            try:
                total_score += float(score_val)
            except (ValueError, TypeError):
                pass
    total_points = float(group_assignment.total_points or 100.0)
    avg_pct = (
        round((total_score / len(graded_group_grades) / total_points * 100), 1)
        if graded_group_grades and total_points > 0
        else 0
    )
    applicable_student_ids: set[int] = set()
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
        applicable_student_ids = {m.student_id for m in members if m.student_id}
    except Exception:
        applicable_student_ids = {g.student_id for g in group_grades if g.student_id}
    ga_voided_student_ids = {g.student_id for g in group_grades if g.is_voided}
    all_voided = group_assignment.status == "Voided"
    if not all_voided and applicable_student_ids:
        all_voided = applicable_student_ids <= ga_voided_student_ids
    partially_voided = not all_voided and bool(ga_voided_student_ids & applicable_student_ids)
    return {
        "total_submissions": len(submission_student_ids),
        "graded_count": len(graded_group_grades),
        "average_score": avg_pct,
        "all_voided": all_voided,
        "partially_voided": partially_voided,
        "voided_count": len(ga_voided_student_ids & applicable_student_ids),
        "needs_grading": len(graded_group_grades) == 0,
    }


def _serialize_assignment_item(
    item_type: str,
    assignment: Assignment | GroupAssignment,
    stats: dict[str, Any],
    class_id: int,
) -> dict[str, Any]:
    is_group = item_type == "group"
    aid = assignment.id
    links = {
        "class": f"/app/management/classes/{class_id}",
        "class_spa_grades": f"/app/management/classes/{class_id}/grades",
    }
    if is_group:
        links["view"] = f"/management/assignments/{class_id}/group/{aid}/view"
        links["grade"] = f"/management/assignments/{class_id}/group/{aid}/grade"
    else:
        links["view"] = f"/management/assignments/{class_id}/individual/{aid}/view"
        links["grade"] = f"/management/assignments/{class_id}/individual/{aid}/grade"
    return {
        "id": aid,
        "key": f"group_{aid}" if is_group else str(aid),
        "title": assignment.title,
        "type": item_type,
        "assignment_type": getattr(assignment, "assignment_type", None) if not is_group else "group",
        "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        "quarter": getattr(assignment, "quarter", None),
        "status": assignment.status,
        "total_points": getattr(assignment, "total_points", None),
        "stats": stats,
        "links": links,
    }


def query_assignments_hub(args: Any = None) -> dict[str, Any]:
    """Class picker hub for assignments & grades."""
    from flask import request

    list_args = request.args if args is None else args
    payload = query_classes_list(list_args)
    group_counts = dict(
        db.session.query(GroupAssignment.class_id, func.count(GroupAssignment.id))
        .group_by(GroupAssignment.class_id)
        .all()
    )
    pending_assistant_by_class: dict[int, int] = {}
    for item in payload["items"]:
        cid = item["id"]
        item["assignment_count"] = item.get("assignment_count", 0) + group_counts.get(cid, 0)
        pending_assistant_by_class[cid] = count_pending_assistant_proposals_for_class(cid)
    visible = payload["items"]
    if payload["meta"].get("default_school_year_id"):
        sy = payload["meta"]["default_school_year_id"]
        visible = [i for i in payload["items"] if i["school_year_id"] == sy]
    payload["stats"]["total_assignments"] = sum(i["assignment_count"] for i in visible)
    payload["hub"] = {
        "extension_request_count": count_pending_extension_requests(),
        "redo_request_count": count_pending_redo_requests(),
        "pending_assistant_by_class": pending_assistant_by_class,
        "total_pending_assistant_proposals": sum(pending_assistant_by_class.values()),
    }
    return payload


def query_assignments_class(
    class_id: int,
    view_mode: str = "grades",
    sort_by: str = "due_date",
    sort_order: str = "desc",
) -> dict[str, Any]:
    """Per-class assignments & grades workspace."""
    class_obj = Class.query.get_or_404(class_id)
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_ids = {
        e.student_id for e in enrollments if e.student_id and not getattr(e.student, "is_deleted", False)
    }
    enrollment_count = len(enrolled_ids)

    assignments_q = Assignment.query.filter_by(class_id=class_id)
    if sort_by == "title":
        assignments_q = assignments_q.order_by(
            Assignment.title.asc() if sort_order == "asc" else Assignment.title.desc()
        )
    else:
        assignments_q = assignments_q.order_by(
            Assignment.due_date.asc() if sort_order == "asc" else Assignment.due_date.desc()
        )
    class_assignments = assignments_q.all()

    try:
        group_q = GroupAssignment.query.filter_by(class_id=class_id)
        if sort_by == "title":
            group_q = group_q.order_by(
                GroupAssignment.title.asc() if sort_order == "asc" else GroupAssignment.title.desc()
            )
        else:
            group_q = group_q.order_by(
                GroupAssignment.due_date.asc() if sort_order == "asc" else GroupAssignment.due_date.desc()
            )
        group_assignments = group_q.all()
    except Exception:
        group_assignments = []

    merged = [("individual", a) for a in class_assignments] + [("group", ga) for ga in group_assignments]
    merged.sort(key=lambda x: (x[1].due_date is None, -_due_ts(x[1].due_date)))

    items: list[dict[str, Any]] = []
    active_count = 0
    avg_scores: list[float] = []
    for item_type, assignment in merged:
        stats = (
            _group_assignment_stats(assignment)
            if item_type == "group"
            else _individual_assignment_stats(assignment, enrolled_ids)
        )
        if assignment.status == "Active" and not stats.get("all_voided"):
            active_count += 1
        if stats.get("average_score", 0) > 0 and not stats.get("all_voided"):
            avg_scores.append(float(stats["average_score"]))
        items.append(_serialize_assignment_item(item_type, assignment, stats, class_id))

    return {
        "class": {
            **serialize_class_list_item(
                class_obj,
                enrollment_count=enrollment_count,
                assignment_count=len(items),
            ),
            "schedule": class_obj.schedule,
        },
        "view_mode": view_mode,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "assignments": items,
        "stats": {
            "total_assignments": len(items),
            "active_assignments": active_count,
            "students": enrollment_count,
            "average_score": round(sum(avg_scores) / len(avg_scores), 1) if avg_scores else None,
        },
        "toolbar": {
            "extension_request_count": count_pending_extension_requests(),
            "redo_request_count": count_pending_redo_requests(),
            "pending_assistant_count": count_pending_assistant_proposals_for_class(class_id),
            "new_assignment_url": f"/app/management/assignments/create?class_id={class_id}",
            "redo_url": "/app/management/redo" if user_should_use_spa_management_shell() else url_for("management.redo_dashboard"),
            "extensions_url": "/app/management/extensions" if user_should_use_spa_management_shell() else url_for("management.view_extension_requests"),
            "assistant_proposals_url": url_for(
                "teacher.assignments.pending_assistant_assignments", class_id=class_id
            ),
        },
    }
