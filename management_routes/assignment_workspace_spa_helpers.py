"""Assignment view & grade workspace payloads for the React management SPA."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from flask import url_for
from sqlalchemy.orm import joinedload

from extensions import db
from models import (
    Assignment,
    AssignmentExtension,
    Enrollment,
    Grade,
    GroupAssignment,
    GroupAssignmentExtension,
    GroupAssignmentMemberSnapshot,
    GroupGrade,
    GroupSubmission,
    QuizQuestion,
    Student,
    StudentGroup,
    Submission,
    TeacherStaff,
)
from teacher_routes.assignment_utils import compute_assignment_void_scope


def _iso(dt: Any) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _student_brief(student: Student | None) -> dict[str, Any]:
    if not student:
        return {"id": None, "display_name": "Unknown", "grade_level": None}
    return {
        "id": student.id,
        "display_name": f"{student.first_name or ''} {student.last_name or ''}".strip() or "Unknown",
        "grade_level": getattr(student, "grade_level", None),
    }


def _parse_grade_row(grade: Grade | None, total_points: float) -> dict[str, Any]:
    if not grade:
        return {
            "score": None,
            "points_earned": None,
            "percentage": None,
            "comment": "",
            "grade_id": None,
            "is_voided": False,
        }
    if grade.is_voided:
        return {
            "score": 0,
            "points_earned": 0,
            "percentage": 0,
            "comment": "",
            "grade_id": grade.id,
            "is_voided": True,
        }
    try:
        if grade.grade_data:
            data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            if isinstance(data, dict):
                raw = data.get("points_earned")
                if raw in (None, "", False):
                    raw = data.get("score", 0)
                try:
                    points = float(raw)
                except (TypeError, ValueError):
                    points = 0.0
                pct = round((points / total_points * 100) if total_points > 0 else 0, 1)
                return {
                    "score": points,
                    "points_earned": points,
                    "percentage": pct,
                    "comment": data.get("comment") or data.get("feedback") or "",
                    "grade_id": grade.id,
                    "is_voided": False,
                }
    except (json.JSONDecodeError, TypeError):
        pass
    return {
        "score": 0,
        "points_earned": 0,
        "percentage": 0,
        "comment": "",
        "grade_id": grade.id,
        "is_voided": grade.is_voided,
    }


def _submission_brief(sub: Submission | None) -> dict[str, Any] | None:
    if not sub:
        return None
    return {
        "submission_type": sub.submission_type or "not_submitted",
        "submission_notes": sub.submission_notes or "",
        "submitted_at": _iso(sub.submitted_at),
    }


def _individual_legacy_flags(assignment: Assignment) -> dict[str, Any]:
    atype = assignment.assignment_type or ""
    legacy_view = url_for("management.view_assignment", assignment_id=assignment.id)
    legacy_grade = url_for("management.grade_assignment", assignment_id=assignment.id)
    if atype == "discussion":
        return {"legacy_only": True, "legacy_view_url": legacy_view, "legacy_grade_url": legacy_grade, "legacy_reason": "discussion"}
    if atype == "quiz":
        questions = QuizQuestion.query.filter_by(assignment_id=assignment.id).all()
        has_open = any(q.question_type in ("short_answer", "essay") for q in questions)
        if has_open:
            return {"legacy_only": False, "legacy_view_url": legacy_view, "legacy_grade_url": legacy_grade, "legacy_reason": "quiz_open_ended_grade"}
        return {"legacy_only": True, "legacy_view_url": legacy_view, "legacy_grade_url": legacy_grade, "legacy_reason": "quiz_auto_graded"}
    return {"legacy_only": False, "legacy_view_url": legacy_view, "legacy_grade_url": legacy_grade, "legacy_reason": None}


def _class_brief(class_info, teacher: TeacherStaff | None = None) -> dict[str, Any]:
    if not class_info:
        return {"id": None, "name": "Unknown", "subject": None, "grade_level": None, "teacher_name": "Unknown"}
    if teacher is None and class_info.teacher_id:
        teacher = TeacherStaff.query.get(class_info.teacher_id)
    grade_level = getattr(class_info, "grade_level", None)
    if grade_level is None and hasattr(class_info, "grade_levels_display"):
        grade_level = getattr(class_info, "grade_levels_display", None)
    return {
        "id": class_info.id,
        "name": class_info.name,
        "subject": getattr(class_info, "subject", None),
        "grade_level": grade_level,
        "teacher_name": f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() if teacher else "Unknown",
    }


def _assignment_action_links(assignment_id: int, class_id: int, *, is_group: bool = False) -> dict[str, str]:
    if is_group:
        return {
            "grade_spa": f"/management/assignments/{class_id}/group/{assignment_id}/grade",
            "class_spa": f"/management/assignments/{class_id}",
            "edit": url_for("management.admin_edit_group_assignment", assignment_id=assignment_id),
            "submissions": url_for("management.admin_grade_group_assignment", assignment_id=assignment_id),
            "extensions_spa": "/management/extensions",
            "redo_spa": "/management/redo",
        }
    return {
        "grade_spa": f"/management/assignments/{class_id}/individual/{assignment_id}/grade",
        "class_spa": f"/management/assignments/{class_id}",
        "edit": url_for("management.edit_assignment", assignment_id=assignment_id),
        "submissions": url_for("teacher.assignments.view_assignment_submissions", assignment_id=assignment_id),
        "extensions_spa": "/management/extensions",
        "redo_spa": "/management/redo",
    }


def _normalize_assignment_type(assignment_type: str | None) -> str:
    return (assignment_type or "").lower().replace("/", "_").replace(" ", "_")


def _is_pdf_paper_type(assignment_type: str | None) -> bool:
    atype = _normalize_assignment_type(assignment_type)
    return atype in ("pdf", "paper", "pdf_paper")


def _actions_meta_individual(assignment: Assignment, flags: dict[str, Any], voided_ids: set[int]) -> dict[str, Any]:
    atype = _normalize_assignment_type(assignment.assignment_type)
    is_pdf = _is_pdf_paper_type(assignment.assignment_type)
    quiz_auto = flags.get("legacy_reason") == "quiz_auto_graded"
    return {
        "show_reopen": not is_pdf and atype != "discussion",
        "show_redo": is_pdf,
        "show_unvoid": bool(voided_ids),
        "grade_disabled": bool(flags.get("legacy_only") and quiz_auto),
        "grade_disabled_label": "Auto-Graded" if quiz_auto else None,
        "is_quiz": atype == "quiz",
        "max_attempts": getattr(assignment, "max_attempts", None),
    }


def _class_students(class_id: int) -> list[Student]:
    return (
        db.session.query(Student)
        .join(Enrollment)
        .filter(Enrollment.class_id == class_id, Enrollment.is_active.is_(True))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )


def _roster_students(class_id: int) -> list[dict[str, Any]]:
    return [_student_brief(s) for s in _class_students(class_id)]


def query_individual_assignment_view(assignment_id: int) -> dict[str, Any]:
    assignment = Assignment.query.get_or_404(assignment_id)
    class_info = assignment.class_info
    teacher = TeacherStaff.query.get(class_info.teacher_id) if class_info and class_info.teacher_id else None
    flags = _individual_legacy_flags(assignment)

    enrolled_ids = [
        sid
        for (sid,) in db.session.query(Enrollment.student_id)
        .filter_by(class_id=assignment.class_id, is_active=True)
        .all()
    ]
    voided_ids = {
        sid
        for (sid,) in db.session.query(Grade.student_id)
        .filter(Grade.assignment_id == assignment_id, Grade.is_voided.is_(True))
        .distinct()
        .all()
    }
    voided_ids = set(enrolled_ids).intersection(voided_ids)
    eligible = [sid for sid in enrolled_ids if sid not in voided_ids]
    total_students = len(eligible)

    submissions_q = db.session.query(Submission.student_id).filter(Submission.assignment_id == assignment_id).distinct()
    if voided_ids:
        submissions_q = submissions_q.filter(~Submission.student_id.in_(voided_ids))
    submissions_count = submissions_q.count()

    non_voided = Grade.query.filter(Grade.assignment_id == assignment_id, Grade.is_voided.is_(False))
    if voided_ids:
        non_voided = non_voided.filter(~Grade.student_id.in_(voided_ids))
    grades = non_voided.order_by(Grade.graded_at.desc(), Grade.id.desc()).all()
    graded_ids: set[int] = set()
    latest: dict[int, Grade] = {}
    for g in grades:
        if g.student_id not in graded_ids:
            graded_ids.add(g.student_id)
            latest[g.student_id] = g
    graded_count = len(graded_ids)

    total_points = float(assignment.total_points or assignment.points or 100)
    average_score = None
    if graded_count:
        pcts: list[float] = []
        for g in latest.values():
            row = _parse_grade_row(g, total_points)
            if row["percentage"] is not None:
                pcts.append(float(row["percentage"]))
        if pcts:
            average_score = round(sum(pcts) / len(pcts), 1)

    void_scope = compute_assignment_void_scope(assignment, enrolled_ids, voided_ids)
    attachments = []
    if hasattr(assignment, "attachment_list") and assignment.attachment_list:
        for i, att in enumerate(assignment.attachment_list):
            mime = getattr(att, "attachment_mime_type", "") or ""
            attachments.append(
                {
                    "index": i,
                    "name": getattr(att, "attachment_original_filename", None) or getattr(att, "attachment_filename", f"Document {i + 1}"),
                    "is_pdf": "pdf" in mime.lower(),
                    "view_url": f"/assignment/file/{assignment.id}?view=true&index={i}",
                    "download_url": f"/assignment/file/{assignment.id}?index={i}",
                }
            )
    elif assignment.attachment_filename:
        mime = getattr(assignment, "attachment_mime_type", "") or ""
        attachments.append(
            {
                "index": 0,
                "name": getattr(assignment, "attachment_original_filename", None) or assignment.attachment_filename,
                "is_pdf": "pdf" in mime.lower(),
                "view_url": f"/assignment/file/{assignment.id}?view=true",
                "download_url": f"/assignment/file/{assignment.id}",
            }
        )

    return {
        "type": "individual",
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description or "",
            "assignment_type": assignment.assignment_type,
            "due_date": _iso(assignment.due_date),
            "quarter": assignment.quarter,
            "status": assignment.status,
            "total_points": total_points,
        },
        "class": _class_brief(class_info, teacher),
        "stats": {
            "total_students": total_students,
            "submissions_count": submissions_count,
            "graded_count": graded_count,
            "pending_count": max(total_students - graded_count, 0),
            "submission_rate": round(min((submissions_count / total_students * 100) if total_students else 0, 100), 1),
            "grading_rate": round((graded_count / total_students * 100) if total_students else 0, 1),
            "average_score": average_score,
        },
        "void_scope": void_scope,
        "attachments": attachments,
        "students": _roster_students(assignment.class_id),
        "voided_student_ids": sorted(voided_ids),
        "actions": _actions_meta_individual(assignment, flags, voided_ids),
        "links": _assignment_action_links(assignment.id, assignment.class_id),
        **flags,
    }


def query_individual_assignment_grade(assignment_id: int) -> dict[str, Any]:
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    flags = _individual_legacy_flags(assignment)
    if flags.get("legacy_only") or flags.get("legacy_reason") == "quiz_open_ended_grade":
        return {
            "type": "individual",
            "assignment": {"id": assignment.id, "title": assignment.title, "class_id": assignment.class_id},
            **flags,
        }

    students = _class_students(class_obj.id) if class_obj else []
    total_points = float(assignment.total_points or 100)
    grade_rows = {g.student_id: g for g in Grade.query.filter_by(assignment_id=assignment_id).all()}
    subs = {s.student_id: s for s in Submission.query.filter_by(assignment_id=assignment_id).all()}
    exts = {
        e.student_id: {"extended_due_date": _iso(e.extended_due_date), "reason": e.reason or ""}
        for e in AssignmentExtension.query.filter_by(assignment_id=assignment_id, is_active=True).all()
    }

    roster = []
    graded = 0
    for student in students:
        g = grade_rows.get(student.id)
        row = _parse_grade_row(g, total_points)
        if row["points_earned"] not in (None, 0) and not row["is_voided"]:
            graded += 1
        sub = _submission_brief(subs.get(student.id))
        roster.append(
            {
                "student": _student_brief(student),
                "grade": row,
                "submission": sub,
                "extension": exts.get(student.id),
            }
        )

    return {
        "type": "individual",
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "assignment_type": assignment.assignment_type,
            "due_date": _iso(assignment.due_date),
            "quarter": assignment.quarter,
            "total_points": total_points,
            "class_id": assignment.class_id,
        },
        "class": {"id": class_obj.id if class_obj else None, "name": class_obj.name if class_obj else "Unknown"},
        "students": roster,
        "stats": {
            "total_students": len(roster),
            "graded_count": graded,
            "pending_count": max(len(roster) - graded, 0),
        },
        "links": {
            "view_spa": f"/management/assignments/{assignment.class_id}/individual/{assignment.id}/view",
            "class_spa": f"/management/assignments/{assignment.class_id}",
        },
        **flags,
    }


def _group_roster(group_assignment: GroupAssignment) -> tuple[list[dict[str, Any]], int]:
    from types import SimpleNamespace

    snap_rows = GroupAssignmentMemberSnapshot.query.filter_by(group_assignment_id=group_assignment.id).all()
    snapshot: dict[int | None, list[int]] = {}
    for r in snap_rows:
        snapshot.setdefault(r.group_id, []).append(r.student_id)

    groups: list[dict[str, Any]] = []
    if snapshot:
        group_ids = sorted({gid for gid in snapshot.keys() if gid is not None})
        group_objs = StudentGroup.query.filter(StudentGroup.id.in_(group_ids)).all() if group_ids else []
        by_id = {g.id: g for g in group_objs}
        student_ids = sorted({sid for sids in snapshot.values() for sid in sids})
        students_by_id = {s.id: s for s in Student.query.filter(Student.id.in_(student_ids)).all()} if student_ids else {}
        for gid in group_ids:
            members = [_student_brief(students_by_id.get(sid)) for sid in snapshot.get(gid, []) if sid in students_by_id]
            groups.append({"id": gid, "name": by_id[gid].name if gid in by_id else f"Group #{gid}", "members": members})
        if snapshot.get(None):
            members = [_student_brief(students_by_id.get(sid)) for sid in snapshot[None] if sid in students_by_id]
            groups.append({"id": 0, "name": "Students from deleted group", "members": members})
    else:
        if group_assignment.selected_group_ids:
            try:
                selected = json.loads(group_assignment.selected_group_ids) if isinstance(group_assignment.selected_group_ids, str) else group_assignment.selected_group_ids
                q = StudentGroup.query.filter(
                    StudentGroup.class_id == group_assignment.class_id,
                    StudentGroup.is_active.is_(True),
                    StudentGroup.id.in_([int(x) for x in selected]),
                )
            except Exception:
                q = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True)
        else:
            q = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True)
        for g in q.all():
            members = [_student_brief(m.student) for m in getattr(g, "members", []) if getattr(m, "student", None)]
            groups.append({"id": g.id, "name": g.name, "members": members})

    total_students = sum(len(g["members"]) for g in groups)
    return groups, total_students


def query_group_assignment_view(assignment_id: int) -> dict[str, Any]:
    ga = GroupAssignment.query.get_or_404(assignment_id)
    class_info = ga.class_info
    teacher = TeacherStaff.query.get(class_info.teacher_id) if class_info and class_info.teacher_id else None
    groups, total_students = _group_roster(ga)
    submissions = GroupSubmission.query.filter_by(group_assignment_id=assignment_id).all()
    submitted_groups = {s.group_id for s in submissions if getattr(s, "group_id", None)}
    group_grades = [g for g in GroupGrade.query.filter_by(group_assignment_id=assignment_id).all() if not g.is_voided]
    graded_student_ids = {g.student_id for g in group_grades if g.student_id}
    graded_count = len(graded_student_ids)
    total_points = float(ga.total_points or 100)

    average_score = None
    if graded_student_ids:
        pcts: list[float] = []
        for gg in group_grades:
            if gg.student_id not in graded_student_ids:
                continue
            row = _parse_grade_row(gg, total_points) if hasattr(gg, "grade_data") else None
            if row and row.get("percentage") is not None:
                pcts.append(float(row["percentage"]))
        if pcts:
            average_score = round(sum(pcts) / len(pcts), 1)

    attachment = None
    if ga.attachment_filename:
        mime = getattr(ga, "attachment_mime_type", "") or ""
        attachment = {
            "name": getattr(ga, "attachment_original_filename", None) or ga.attachment_filename,
            "is_pdf": "pdf" in mime.lower(),
            "view_url": f"/group-assignment/file/{ga.id}?view=true",
            "download_url": f"/group-assignment/file/{ga.id}",
        }

    roster_students: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for group in groups:
        for member in group.get("members", []):
            mid = member.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                roster_students.append(member)
    has_voided = GroupGrade.query.filter_by(group_assignment_id=assignment_id, is_voided=True).count() > 0
    voided_student_ids = sorted({
        gg.student_id
        for gg in GroupGrade.query.filter_by(group_assignment_id=assignment_id, is_voided=True).all()
        if gg.student_id
    })

    return {
        "type": "group",
        "legacy_only": False,
        "assignment": {
            "id": ga.id,
            "title": ga.title,
            "description": ga.description or "",
            "due_date": _iso(ga.due_date),
            "quarter": ga.quarter,
            "status": ga.status,
            "total_points": total_points,
            "group_size_min": ga.group_size_min,
            "group_size_max": ga.group_size_max,
        },
        "class": _class_brief(class_info, teacher),
        "groups": groups,
        "stats": {
            "total_students": total_students,
            "submissions_count": len(submitted_groups),
            "groups_submitted": len(submitted_groups),
            "graded_count": graded_count,
            "pending_count": max(total_students - graded_count, 0),
            "submission_rate": round((len(submitted_groups) / len(groups) * 100) if groups else 0, 1),
            "grading_rate": round((graded_count / total_students * 100) if total_students else 0, 1),
            "average_score": average_score,
        },
        "attachment": attachment,
        "students": roster_students,
        "voided_student_ids": voided_student_ids,
        "actions": {
            "show_reopen": True,
            "show_redo": False,
            "show_unvoid": has_voided,
            "grade_disabled": False,
            "grade_disabled_label": None,
            "is_quiz": False,
            "max_attempts": None,
        },
        "links": _assignment_action_links(ga.id, ga.class_id, is_group=True),
    }


def query_group_assignment_grade(assignment_id: int) -> dict[str, Any]:
    from utils.grade_helpers import numeric_score_from_grade_dict

    ga = GroupAssignment.query.get_or_404(assignment_id)
    groups, total_students = _group_roster(ga)
    total_points = float(ga.total_points or 100)

    grades_by_student: dict[int, dict[str, Any]] = {}
    for gg in GroupGrade.query.filter_by(group_assignment_id=assignment_id).all():
        if not gg.grade_data:
            continue
        try:
            data = json.loads(gg.grade_data) if isinstance(gg.grade_data, str) else gg.grade_data
            if isinstance(data, dict):
                data = dict(data)
                data["comment"] = gg.comments or data.get("comment") or ""
                sn = numeric_score_from_grade_dict(data)
                data["score"] = sn
                data["points_earned"] = sn
                grades_by_student[gg.student_id] = data
        except Exception:
            grades_by_student[gg.student_id] = {"score": 0, "comment": gg.comments or ""}

    group_sub_status: dict[int, str] = {}
    for sub in GroupSubmission.query.filter_by(group_assignment_id=assignment_id).all():
        if sub.group_id and (sub.attachment_file_path or sub.attachment_filename):
            group_sub_status[sub.group_id] = "online"

    roster_groups = []
    graded = 0
    for group in groups:
        members = []
        for m in group["members"]:
            sid = m["id"]
            if not sid:
                continue
            gdata = grades_by_student.get(sid, {})
            score = gdata.get("score")
            try:
                score_f = float(score) if score not in (None, "") else None
            except (TypeError, ValueError):
                score_f = None
            if score_f and score_f > 0:
                graded += 1
            members.append(
                {
                    "student": m,
                    "group_id": group["id"],
                    "grade": {
                        "score": score_f,
                        "comment": gdata.get("comment") or gdata.get("comments") or "",
                        "is_voided": False,
                    },
                    "submission_type": gdata.get("submission_type") or "not_submitted",
                    "submission_notes": gdata.get("submission_notes") or "",
                }
            )
        roster_groups.append({"id": group["id"], "name": group["name"], "members": members})

    return {
        "type": "group",
        "legacy_only": False,
        "assignment": {
            "id": ga.id,
            "title": ga.title,
            "due_date": _iso(ga.due_date),
            "quarter": ga.quarter,
            "total_points": total_points,
            "class_id": ga.class_id,
        },
        "class": {"id": ga.class_id, "name": ga.class_info.name if ga.class_info else "Unknown"},
        "groups": roster_groups,
        "stats": {
            "total_students": total_students,
            "graded_count": graded,
            "pending_count": max(total_students - graded, 0),
        },
        "links": {
            "view_spa": f"/management/assignments/{ga.class_id}/group/{ga.id}/view",
            "class_spa": f"/management/assignments/{ga.class_id}",
        },
    }
