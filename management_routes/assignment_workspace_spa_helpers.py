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
    AssignmentAttachment,
    AssignmentExtension,
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
from utils.student_roster import active_class_roster_students_query


def _iso(dt: Any) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _student_brief(student: Student | None) -> dict[str, Any]:
    if not student:
        return {"id": None, "display_name": "Unknown", "grade_level": None, "email": None}
    return {
        "id": student.id,
        "display_name": f"{student.first_name or ''} {student.last_name or ''}".strip() or "Unknown",
        "grade_level": getattr(student, "grade_level", None),
        "email": getattr(student, "email", None) or None,
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
        return {
            "legacy_only": False,
            "legacy_view_url": legacy_view,
            "legacy_grade_url": legacy_grade,
            "legacy_reason": "discussion",
        }
    if atype == "quiz":
        questions = QuizQuestion.query.filter_by(assignment_id=assignment.id).all()
        has_open = any(q.question_type in ("short_answer", "essay") for q in questions)
        if has_open:
            return {
                "legacy_only": False,
                "legacy_view_url": legacy_view,
                "legacy_grade_url": legacy_grade,
                "legacy_reason": "quiz_open_ended_grade",
            }
        return {
            "legacy_only": False,
            "legacy_view_url": legacy_view,
            "legacy_grade_url": legacy_grade,
            "legacy_reason": "quiz_auto_graded",
        }
    return {
        "legacy_only": False,
        "legacy_view_url": legacy_view,
        "legacy_grade_url": legacy_grade,
        "legacy_reason": None,
    }


def _spa_edit_link(
    assignment_id: int,
    class_id: int,
    *,
    is_group: bool = False,
    scope: str = "management",
) -> str:
    if scope == "teacher":
        base = f"/app/teacher/assignments-and-grades/{class_id}"
        if is_group:
            return f"{base}/group/{assignment_id}/edit"
        return f"{base}/individual/{assignment_id}/edit"
    if is_group:
        return f"/app/management/assignments/{class_id}/group/{assignment_id}/edit"
    return f"/app/management/assignments/{class_id}/individual/{assignment_id}/edit"


def _discussion_view_payload(assignment: Assignment) -> dict[str, Any]:
    from collections import defaultdict
    from models import DiscussionPost, DiscussionThread

    threads = (
        DiscussionThread.query.filter_by(assignment_id=assignment.id)
        .order_by(DiscussionThread.is_pinned.desc(), DiscussionThread.created_at.desc())
        .all()
    )
    thread_ids = [t.id for t in threads]
    all_posts = (
        DiscussionPost.query.filter(DiscussionPost.thread_id.in_(thread_ids)).all()
        if thread_ids
        else []
    )
    participant_ids: set[int] = set()
    for thread in threads:
        participant_ids.add(thread.student_id)
    for post in all_posts:
        participant_ids.add(post.student_id)

    participants = []
    from utils.student_roster import student_is_archived

    for student_id in participant_ids:
        student = Student.query.get(student_id)
        if not student or student_is_archived(student):
            continue
        threads_count = sum(1 for t in threads if t.student_id == student_id)
        replies_count = sum(1 for p in all_posts if p.student_id == student_id)
        participants.append(
            {
                "student": _student_brief(student),
                "threads": threads_count,
                "replies": replies_count,
                "total_posts": threads_count + replies_count,
            }
        )
    participants.sort(key=lambda x: x["total_posts"], reverse=True)

    min_initial_posts = 1
    min_replies = 2
    if assignment.description:
        initial_posts_match = re.search(r"Minimum (\d+) initial post", assignment.description)
        if initial_posts_match:
            min_initial_posts = int(initial_posts_match.group(1))
        replies_match = re.search(r"Minimum (\d+) reply/replies", assignment.description)
        if replies_match:
            min_replies = int(replies_match.group(1))

    return {
        "threads": [
            {
                "id": t.id,
                "title": t.title,
                "is_pinned": bool(t.is_pinned),
                "created_at": _iso(t.created_at),
                "student": _student_brief(t.student),
                "reply_count": sum(1 for p in all_posts if p.thread_id == t.id),
            }
            for t in threads
        ],
        "participants": participants,
        "requirements": {"min_initial_posts": min_initial_posts, "min_replies": min_replies},
    }


def _quiz_grade_payload(assignment_id: int, students: list[Student]) -> dict[str, Any]:
    from models import QuizAnswer

    questions = (
        QuizQuestion.query.filter_by(assignment_id=assignment_id)
        .order_by(QuizQuestion.order)
        .all()
    )
    open_questions = [q for q in questions if q.question_type in ("short_answer", "essay")]
    if not open_questions:
        return {"grading_mode": "standard", "questions": [], "answers_by_student": {}}

    answers_by_student: dict[str, list[dict[str, Any]]] = {}
    for student in students:
        rows = []
        for question in open_questions:
            answer = QuizAnswer.query.filter_by(student_id=student.id, question_id=question.id).first()
            rows.append(
                {
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "max_points": float(question.points or 0),
                    "answer_text": (answer.answer_text or "") if answer else "",
                    "points_earned": float(answer.points_earned or 0) if answer else None,
                }
            )
        answers_by_student[str(student.id)] = rows

    return {
        "grading_mode": "per_question",
        "questions": [
            {
                "id": q.id,
                "text": q.question_text,
                "type": q.question_type,
                "max_points": float(q.points or 0),
            }
            for q in open_questions
        ],
        "answers_by_student": answers_by_student,
    }


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


def _assignment_action_links(
    assignment_id: int,
    class_id: int,
    *,
    is_group: bool = False,
    scope: str = "management",
) -> dict[str, str]:
    if scope == "teacher":
        base = f"/teacher/assignments-and-grades/{class_id}"
        if is_group:
            return {
                "grade_spa": f"{base}/group/{assignment_id}/grade",
                "class_spa": base,
                "edit": _spa_edit_link(assignment_id, class_id, is_group=True, scope=scope),
                "edit_spa": _spa_edit_link(assignment_id, class_id, is_group=True, scope=scope),
                "submissions": f"/app{base}/group/{assignment_id}/submissions",
                "extensions_spa": "/teacher/extensions",
                "redo_spa": "/teacher/redo",
            }
        return {
            "grade_spa": f"{base}/individual/{assignment_id}/grade",
            "class_spa": base,
            "edit": _spa_edit_link(assignment_id, class_id, scope=scope),
            "edit_spa": _spa_edit_link(assignment_id, class_id, scope=scope),
            "submissions": f"/app{base}/individual/{assignment_id}/submissions",
            "extensions_spa": "/teacher/extensions",
            "redo_spa": "/teacher/redo",
        }
    if is_group:
        return {
            "grade_spa": f"/management/assignments/{class_id}/group/{assignment_id}/grade",
            "class_spa": f"/management/assignments/{class_id}",
            "edit": _spa_edit_link(assignment_id, class_id, is_group=True),
            "edit_spa": _spa_edit_link(assignment_id, class_id, is_group=True),
            "submissions": f"/app/management/assignments/{class_id}/group/{assignment_id}/submissions",
            "extensions_spa": "/management/extensions",
            "redo_spa": "/management/redo",
        }
    return {
        "grade_spa": f"/management/assignments/{class_id}/individual/{assignment_id}/grade",
        "class_spa": f"/management/assignments/{class_id}",
        "edit": _spa_edit_link(assignment_id, class_id),
        "edit_spa": _spa_edit_link(assignment_id, class_id),
        "submissions": f"/app/management/assignments/{class_id}/individual/{assignment_id}/submissions",
        "extensions_spa": "/management/extensions",
        "redo_spa": "/management/redo",
    }


def _normalize_assignment_type(assignment_type: str | None) -> str:
    return (assignment_type or "").lower().replace("/", "_").replace(" ", "_")


def _is_pdf_paper_type(assignment_type: str | None) -> bool:
    atype = _normalize_assignment_type(assignment_type)
    return atype in ("pdf", "paper", "pdf_paper")


def _discussion_requirements(assignment: Assignment) -> dict[str, int]:
    min_initial_posts = 1
    min_replies = 2
    if assignment.description:
        initial_posts_match = re.search(r"Minimum (\d+) initial post", assignment.description)
        if initial_posts_match:
            min_initial_posts = int(initial_posts_match.group(1))
        replies_match = re.search(r"Minimum (\d+) reply/replies", assignment.description)
        if replies_match:
            min_replies = int(replies_match.group(1))
    return {"min_initial_posts": min_initial_posts, "min_replies": min_replies}


def _submission_download_url(assignment_id: int, submission_id: int) -> str:
    return url_for(
        "teacher.assignments.download_submission",
        assignment_id=assignment_id,
        submission_id=submission_id,
    )


def _grade_info_dict(grade: Grade | None) -> dict[str, Any] | None:
    if not grade or grade.is_voided or not grade.grade_data:
        return None
    try:
        gd = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
        if isinstance(gd, dict):
            return {
                "score": gd.get("score"),
                "points_earned": gd.get("points_earned") or gd.get("score"),
                "percentage": gd.get("percentage"),
                "comment": gd.get("comment") or gd.get("feedback") or "",
            }
    except Exception:
        pass
    return None


def _submission_status_for_student(
    student_id: int,
    submission: Submission | None,
    assignment: Assignment,
    extensions: dict[int, AssignmentExtension],
) -> str:
    if not submission:
        return "not_submitted"
    due = assignment.due_date
    if student_id in extensions and extensions[student_id].extended_due_date:
        due = extensions[student_id].extended_due_date
    if submission.submitted_at and due and submission.submitted_at > due:
        return "late"
    return "on_time"


def _quiz_attempt_details(subs: list) -> list[dict[str, Any]]:
    from teacher_routes.assignment_utils import parse_quiz_submission_auto_score

    details: list[dict[str, Any]] = []
    for idx, sub in enumerate(subs, start=1):
        details.append(
            {
                "attempt_num": idx,
                "submitted_at": _iso(sub.submitted_at) if sub.submitted_at else None,
                "parsed_score": parse_quiz_submission_auto_score(sub.comments),
            }
        )
    return details


def _quiz_questions_payload(assignment_id: int, student_id: int) -> tuple[list[dict[str, Any]], float]:
    from models import QuizAnswer, QuizOption

    questions = (
        QuizQuestion.query.filter_by(assignment_id=assignment_id)
        .order_by(QuizQuestion.order)
        .all()
    )
    if not questions:
        return [], 0.0

    question_ids = [q.id for q in questions]
    answers = (
        QuizAnswer.query.options(joinedload(QuizAnswer.selected_option))
        .filter(QuizAnswer.student_id == student_id, QuizAnswer.question_id.in_(question_ids))
        .all()
    )
    answers_by_q = {a.question_id: a for a in answers}

    auto_points = 0.0
    rows: list[dict[str, Any]] = []
    for idx, question in enumerate(questions, start=1):
        answer = answers_by_q.get(question.id)
        qtype = question.question_type or ""
        needs_manual = qtype in ("short_answer", "essay")
        answer_display = ""
        is_correct: bool | None = None
        points_earned: float | None = None

        if answer:
            points_earned = float(answer.points_earned or 0)
            is_correct = bool(answer.is_correct) if answer.is_correct is not None else None
            if qtype in ("multiple_choice", "true_false"):
                if answer.selected_option:
                    answer_display = answer.selected_option.option_text or ""
                elif answer.selected_option_id:
                    opt = QuizOption.query.get(answer.selected_option_id)
                    answer_display = opt.option_text if opt else ""
                if not needs_manual:
                    auto_points += points_earned
            else:
                answer_display = answer.answer_text or ""
        elif not needs_manual:
            points_earned = 0.0
            is_correct = False

        rows.append(
            {
                "order": idx,
                "question_id": question.id,
                "question_text": question.question_text or "",
                "type": qtype,
                "max_points": float(question.points or 0),
                "answer_display": answer_display,
                "is_correct": is_correct,
                "points_earned": points_earned,
                "needs_manual_grade": needs_manual,
            }
        )
    return rows, auto_points


def _actions_meta_individual(assignment: Assignment, flags: dict[str, Any], voided_ids: set[int]) -> dict[str, Any]:
    atype = _normalize_assignment_type(assignment.assignment_type)
    is_pdf = _is_pdf_paper_type(assignment.assignment_type)
    quiz_auto = flags.get("legacy_reason") == "quiz_auto_graded"
    grade_via_submissions = flags.get("legacy_reason") in ("discussion", "quiz_open_ended_grade")
    return {
        "show_reopen": not is_pdf and atype != "discussion",
        "show_redo": is_pdf,
        "show_unvoid": bool(voided_ids),
        "grade_disabled": bool(quiz_auto),
        "grade_disabled_label": "Auto-Graded" if quiz_auto else None,
        "grade_via_submissions": grade_via_submissions,
        "grade_label": "Grade in Submissions" if grade_via_submissions else "Grade",
        "is_quiz": atype == "quiz",
        "max_attempts": getattr(assignment, "max_attempts", None),
    }


def _class_students(class_id: int) -> list[Student]:
    """Active-roster students only (exclude graduated / withdrawn / transferred)."""
    return active_class_roster_students_query(class_id).all()


def _roster_students(class_id: int) -> list[dict[str, Any]]:
    return [_student_brief(s) for s in _class_students(class_id)]


def query_individual_assignment_view(assignment_id: int) -> dict[str, Any]:
    assignment = Assignment.query.get_or_404(assignment_id)
    class_info = assignment.class_info
    teacher = TeacherStaff.query.get(class_info.teacher_id) if class_info and class_info.teacher_id else None
    flags = _individual_legacy_flags(assignment)

    enrolled_ids = [s.id for s in _class_students(assignment.class_id)]
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
        **(
            {"discussion": _discussion_view_payload(assignment)}
            if (assignment.assignment_type or "") == "discussion"
            else {}
        ),
    }


def query_individual_assignment_grade(assignment_id: int) -> dict[str, Any]:
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    flags = _individual_legacy_flags(assignment)

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
    submitted_count = 0
    pct_sum = 0.0
    pct_count = 0
    for student in students:
        g = grade_rows.get(student.id)
        row = _parse_grade_row(g, total_points)
        sub_obj = subs.get(student.id)
        if sub_obj:
            submitted_count += 1
        if row["points_earned"] not in (None, 0) and not row["is_voided"]:
            graded += 1
        if row["percentage"] is not None and not row["is_voided"] and row["points_earned"] not in (None, 0):
            pct_sum += float(row["percentage"])
            pct_count += 1
        notes = (sub_obj.submission_notes or "") if sub_obj else ""
        notes_type = "On-Time"
        notes_other = ""
        if notes in ("On-Time", "Late"):
            notes_type = notes
        elif notes:
            notes_type = "Other"
            notes_other = notes
        sub = _submission_brief(sub_obj)
        if sub:
            sub["submission_notes_type"] = notes_type
            sub["submission_notes_other"] = notes_other
        roster.append(
            {
                "student": _student_brief(student),
                "grade": row,
                "submission": sub,
                "extension": exts.get(student.id),
            }
        )

    class_id = assignment.class_id
    teacher = TeacherStaff.query.get(class_obj.teacher_id) if class_obj and class_obj.teacher_id else None
    class_brief = _class_brief(class_obj, teacher)

    atype = _normalize_assignment_type(assignment.assignment_type)
    grade_via_submissions = flags.get("legacy_reason") in ("discussion", "quiz_open_ended_grade")
    quiz_grade = (
        {"grading_mode": "standard", "questions": [], "answers_by_student": {}}
        if grade_via_submissions
        else _quiz_grade_payload(assignment_id, students)
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
            "total_points": total_points,
            "class_id": class_id,
            "allow_extra_credit": bool(getattr(assignment, "allow_extra_credit", False)),
            "max_extra_credit_points": float(getattr(assignment, "max_extra_credit_points", 0) or 0),
        },
        "class": class_brief,
        "students": roster,
        "stats": {
            "total_students": len(roster),
            "submitted_count": submitted_count,
            "graded_count": graded,
            "pending_count": max(len(roster) - graded, 0),
            "average_score": round(pct_sum / pct_count, 1) if pct_count else None,
        },
        "links": {
            "view_spa": f"/management/assignments/{class_id}/individual/{assignment.id}/view",
            "submissions_spa": f"/management/assignments/{class_id}/individual/{assignment.id}/submissions",
            "statistics": url_for("management.admin_grade_statistics", assignment_id=assignment.id),
            "class_spa": f"/management/assignments/{class_id}",
        },
        "quiz_grade": quiz_grade,
        "grade_via_submissions": grade_via_submissions,
        **flags,
    }


def query_individual_assignment_grade_statistics(assignment_id: int) -> dict[str, Any]:
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    students = _class_students(class_obj.id) if class_obj else []
    total_points = float(assignment.total_points or assignment.points or 100)

    grades = Grade.query.filter_by(assignment_id=assignment_id, is_voided=False).all()
    voided_count = Grade.query.filter_by(assignment_id=assignment_id, is_voided=True).count()
    total_students = len(students)

    stats: dict[str, Any] = {
        "total_students": total_students,
        "voided_count": voided_count,
        "graded_count": 0,
        "ungraded_count": total_students,
        "average_score": 0,
        "average_percentage": 0,
        "median_score": 0,
        "highest_score": 0,
        "lowest_score": total_points if total_points > 0 else 100,
        "passing_count": 0,
        "failing_count": 0,
    }
    letter_grades = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    grade_distribution = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "0-59": 0}

    scores: list[float] = []
    graded_student_ids: set[int] = set()

    for grade in grades:
        try:
            grade_data = (
                json.loads(grade.grade_data)
                if isinstance(grade.grade_data, str)
                else grade.grade_data
            )
            if not isinstance(grade_data, dict):
                continue
            raw = grade_data.get("score")
            if raw in (None, "", False):
                raw = grade_data.get("points_earned")
            if raw is None:
                continue
            score_float = float(raw)
            graded_student_ids.add(grade.student_id)
            scores.append(score_float)

            percentage = (score_float / total_points * 100) if total_points > 0 else 0
            if score_float > stats["highest_score"]:
                stats["highest_score"] = score_float
            if score_float < stats["lowest_score"]:
                stats["lowest_score"] = score_float

            if percentage >= 70:
                stats["passing_count"] += 1
            else:
                stats["failing_count"] += 1

            if percentage >= 90:
                letter_grades["A"] += 1
                grade_distribution["90-100"] += 1
            elif percentage >= 80:
                letter_grades["B"] += 1
                grade_distribution["80-89"] += 1
            elif percentage >= 70:
                letter_grades["C"] += 1
                grade_distribution["70-79"] += 1
            elif percentage >= 60:
                letter_grades["D"] += 1
                grade_distribution["60-69"] += 1
            else:
                letter_grades["F"] += 1
                grade_distribution["0-59"] += 1
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    stats["graded_count"] = len(graded_student_ids)
    stats["ungraded_count"] = max(total_students - stats["graded_count"], 0)

    if scores:
        stats["average_score"] = round(sum(scores) / len(scores), 2)
        sorted_scores = sorted(scores)
        mid = len(sorted_scores) // 2
        if len(sorted_scores) == 1:
            stats["median_score"] = round(sorted_scores[0], 2)
        else:
            stats["median_score"] = round((sorted_scores[mid] + sorted_scores[~mid]) / 2, 2)
        stats["average_percentage"] = round(
            (stats["average_score"] / total_points * 100) if total_points > 0 else 0,
            1,
        )
    else:
        stats["lowest_score"] = 0

    return {
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "class_name": class_obj.name if class_obj else "Unknown",
        },
        "total_points": total_points,
        "stats": stats,
        "letter_grades": letter_grades,
        "grade_distribution": grade_distribution,
    }


def _group_roster(group_assignment: GroupAssignment) -> tuple[list[dict[str, Any]], int]:
    from types import SimpleNamespace

    from utils.student_roster import student_is_archived

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
        students_by_id = {
            s.id: s
            for s in (
                Student.query.filter(Student.id.in_(student_ids)).all() if student_ids else []
            )
            if not student_is_archived(s)
        }
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
            members = [
                _student_brief(m.student)
                for m in getattr(g, "members", [])
                if getattr(m, "student", None) and not student_is_archived(m.student)
            ]
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


def query_assignment_edit_meta(assignment_id: int, *, is_group: bool = False) -> dict[str, Any]:
    if is_group:
        ga = GroupAssignment.query.get_or_404(assignment_id)
        return {
            "is_group": True,
            "assignment_id": ga.id,
            "class_id": ga.class_id,
            "assignment_type": "group",
            "edit_path": f"/app/management/assignments-and-grades/{ga.class_id}/group/{ga.id}/edit",
        }

    assignment = Assignment.query.get_or_404(assignment_id)
    atype = (assignment.assignment_type or "pdf").lower()
    class_id = assignment.class_id
    edit_path = f"/app/management/assignments-and-grades/{class_id}/individual/{assignment_id}/edit"
    return {
        "is_group": False,
        "assignment_id": assignment.id,
        "class_id": class_id,
        "assignment_type": atype,
        "edit_path": edit_path,
    }


def save_quiz_open_ended_grades(assignment_id: int, entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Save per-question quiz grades (open-ended questions) from SPA JSON."""
    import json
    from datetime import datetime

    from management_routes.assignments import _apply_assignment_adjustments

    assignment = Assignment.query.get_or_404(assignment_id)
    if (assignment.assignment_type or "") != "quiz":
        return {"success": False, "message": "Not a quiz assignment."}

    students = _class_students(assignment.class_info.id) if assignment.class_info else []
    student_by_id = {s.id: s for s in students}
    questions = (
        QuizQuestion.query.filter_by(assignment_id=assignment_id)
        .order_by(QuizQuestion.order)
        .all()
    )
    open_questions = [q for q in questions if q.question_type in ("short_answer", "essay")]
    if not open_questions:
        return {"success": False, "message": "This quiz has no manually graded questions."}

    from models import QuizAnswer

    saved = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        student_id = entry.get("student_id")
        if not student_id or int(student_id) not in student_by_id:
            continue
        student = student_by_id[int(student_id)]
        existing_grade = Grade.query.filter_by(assignment_id=assignment_id, student_id=student.id).first()
        if existing_grade and existing_grade.is_voided:
            continue
        sub = Submission.query.filter_by(student_id=student.id, assignment_id=assignment_id).first()

        earned_points = 0.0
        question_scores = entry.get("questions") or {}
        if isinstance(question_scores, list):
            question_scores = {
                str(row.get("question_id")): row.get("points")
                for row in question_scores
                if isinstance(row, dict)
            }

        for question in questions:
            if question.question_type in ("short_answer", "essay"):
                raw_val = question_scores.get(str(question.id), question_scores.get(question.id, ""))
                try:
                    q_points = float(raw_val) if str(raw_val).strip() != "" else 0.0
                except (TypeError, ValueError):
                    q_points = 0.0
                earned_points += q_points
                answer = QuizAnswer.query.filter_by(student_id=student.id, question_id=question.id).first()
                if answer:
                    answer.points_earned = q_points
                    answer.is_correct = q_points == float(question.points or 0)
            else:
                answer = QuizAnswer.query.filter_by(student_id=student.id, question_id=question.id).first()
                if answer:
                    earned_points += float(answer.points_earned or 0.0)

        comments = (entry.get("comment") or "").strip()
        adjusted = _apply_assignment_adjustments(
            assignment=assignment,
            entered_points=earned_points,
            submission_record=sub,
            notes_type="On-Time",
        )
        grade_data_dict = {
            "score": adjusted["points_earned"],
            "points_earned": adjusted["points_earned"],
            "raw_points": adjusted["raw_points"],
            "extra_credit_points": adjusted["extra_credit_points"],
            "late_penalty_applied": adjusted["late_penalty_applied"],
            "days_late": adjusted["days_late"],
            "total_points": adjusted["total_points"],
            "max_score": adjusted["max_score"],
            "percentage": adjusted["percentage"],
            "comment": comments,
            "feedback": comments,
            "graded_at": datetime.utcnow().isoformat(),
            "grading_status": "final",
        }
        grade_json = json.dumps(grade_data_dict)
        if existing_grade:
            existing_grade.grade_data = grade_json
            existing_grade.graded_at = datetime.utcnow()
            existing_grade.extra_credit_points = adjusted["extra_credit_points"]
            existing_grade.late_penalty_applied = adjusted["late_penalty_applied"]
        else:
            db.session.add(
                Grade(
                    student_id=student.id,
                    assignment_id=assignment_id,
                    grade_data=grade_json,
                    graded_at=datetime.utcnow(),
                    extra_credit_points=adjusted["extra_credit_points"],
                    late_penalty_applied=adjusted["late_penalty_applied"],
                )
            )
        if sub is None and adjusted["points_earned"] > 0:
            sub = Submission(
                student_id=student.id,
                assignment_id=assignment_id,
                submission_type="in_person",
                submission_notes="Auto-marked: quiz grade entered",
                submitted_at=datetime.utcnow(),
                marked_at=datetime.utcnow(),
            )
            db.session.add(sub)
        saved += 1

    if not saved:
        return {"success": False, "message": "No quiz grades were saved."}
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "message": str(exc)}
    from utils.grade_mutation_hooks import notify_grades_changed

    notify_grades_changed()
    return {"success": True, "message": f"Saved {saved} quiz grade(s)."}


def _assignment_edit_common_fields(assignment: Assignment) -> dict[str, Any]:
    class_obj = assignment.class_info
    attachments = []
    for att in assignment.attachment_list or []:
        attachments.append(
            {
                "id": att.id,
                "name": att.attachment_original_filename or att.attachment_filename,
            }
        )
    if not attachments and assignment.attachment_original_filename:
        attachments.append(
            {
                "id": None,
                "name": assignment.attachment_original_filename,
            }
        )
    return {
        "assignment_id": assignment.id,
        "class_id": assignment.class_id,
        "class_name": class_obj.name if class_obj else "Unknown",
        "assignment_type": (assignment.assignment_type or "pdf").lower(),
        "title": assignment.title,
        "description": assignment.description or "",
        "due_date": _iso(assignment.due_date),
        "open_date": _iso(assignment.open_date),
        "close_date": _iso(assignment.close_date),
        "quarter": str(assignment.quarter or "1"),
        "status": assignment.status or "Active",
        "assignment_context": assignment.assignment_context or "homework",
        "assignment_category": assignment.assignment_category or "",
        "category_weight": float(assignment.category_weight or 0),
        "total_points": float(assignment.total_points or 100),
        "allow_extra_credit": bool(assignment.allow_extra_credit),
        "max_extra_credit_points": float(assignment.max_extra_credit_points or 0),
        "late_penalty_enabled": bool(assignment.late_penalty_enabled),
        "late_penalty_per_day": float(assignment.late_penalty_per_day or 0),
        "late_penalty_max_days": int(assignment.late_penalty_max_days or 0),
        "status_revert_enabled": bool(assignment.status_override and assignment.status_override_until),
        "status_override_until": _iso(assignment.status_override_until),
        "attachments": attachments,
    }


def query_individual_assignment_edit(assignment_id: int) -> dict[str, Any]:
    assignment = Assignment.query.get_or_404(assignment_id)
    payload = _assignment_edit_common_fields(assignment)
    atype = payload["assignment_type"]
    if atype == "quiz":
        payload["quiz"] = {
            "time_limit_minutes": assignment.time_limit_minutes,
            "max_attempts": assignment.max_attempts or 1,
            "shuffle_questions": bool(assignment.shuffle_questions),
            "show_correct_answers": bool(assignment.show_correct_answers),
            "allow_save_and_continue": bool(assignment.allow_save_and_continue),
            "max_save_attempts": assignment.max_save_attempts or 10,
            "save_timeout_minutes": assignment.save_timeout_minutes or 30,
            "google_form_linked": bool(assignment.google_form_linked),
            "google_form_url": assignment.google_form_url or "",
        }
    if atype == "discussion":
        payload["discussion"] = {
            "allow_student_edit_posts": bool(assignment.allow_student_edit_posts),
        }
    return payload


def query_group_assignment_edit(assignment_id: int) -> dict[str, Any]:
    ga = GroupAssignment.query.get_or_404(assignment_id)
    class_obj = ga.class_info
    return {
        "assignment_id": ga.id,
        "is_group": True,
        "class_id": ga.class_id,
        "class_name": class_obj.name if class_obj else "Unknown",
        "assignment_type": (ga.assignment_type or "pdf").lower(),
        "title": ga.title,
        "description": ga.description or "",
        "due_date": _iso(ga.due_date),
        "open_date": _iso(ga.open_date),
        "close_date": _iso(ga.close_date),
        "quarter": str(ga.quarter or "1"),
        "status": ga.status or "Active",
        "assignment_context": ga.assignment_context or "homework",
        "assignment_category": ga.assignment_category or "",
        "category_weight": float(ga.category_weight or 0),
        "total_points": float(ga.total_points or 100),
        "allow_extra_credit": bool(ga.allow_extra_credit),
        "max_extra_credit_points": float(ga.max_extra_credit_points or 0),
        "late_penalty_enabled": bool(ga.late_penalty_enabled),
        "late_penalty_per_day": float(ga.late_penalty_per_day or 0),
        "late_penalty_max_days": int(ga.late_penalty_max_days or 0),
        "allow_individual": bool(ga.allow_individual),
        "attachments": (
            [
                {
                    "id": None,
                    "name": ga.attachment_original_filename or ga.attachment_filename,
                }
            ]
            if ga.attachment_filename
            else []
        ),
    }


def _parse_edit_datetime(raw: str | None):
    if not raw or not str(raw).strip():
        return None
    from teacher_routes.assignment_utils import parse_form_datetime_as_school_tz
    from utils.school_timezone import get_school_timezone_name

    return parse_form_datetime_as_school_tz(str(raw).strip(), get_school_timezone_name())


def _truthy_form_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "on", "yes"}


def _coerce_remove_attachment_ids(raw) -> list[int]:
    ids: list[int] = []
    if raw is None:
        return ids
    if isinstance(raw, list):
        values = raw
    else:
        values = str(raw).split(",")
    for item in values:
        try:
            ids.append(int(str(item).strip()))
        except (TypeError, ValueError):
            continue
    return ids


def _delete_attachment_file(att: AssignmentAttachment) -> None:
    import os

    from flask import current_app

    upload = current_app.config["UPLOAD_FOLDER"]
    candidates = []
    if att.attachment_file_path:
        candidates.append(att.attachment_file_path)
        candidates.append(os.path.join(upload, att.attachment_file_path))
    if att.attachment_filename:
        candidates.append(os.path.join(upload, "assignments", att.attachment_filename))
        candidates.append(os.path.join(upload, att.attachment_filename))
    for path in candidates:
        try:
            if path and os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass


def _apply_individual_attachment_updates(assignment: Assignment, body: dict[str, Any]) -> str | None:
    """Remove selected attachments and/or append new uploads. Returns error message or None."""
    import os
    from datetime import datetime

    from flask import current_app, request
    from werkzeug.utils import secure_filename

    from management_routes.utils import ALLOWED_EXTENSIONS, allowed_file

    remove_ids = set(_coerce_remove_attachment_ids(body.get("remove_attachment_ids")))
    if remove_ids:
        for att in list(assignment.attachment_list or []):
            if att.id in remove_ids:
                _delete_attachment_file(att)
                db.session.delete(att)
        db.session.flush()
        remaining = (
            AssignmentAttachment.query.filter_by(assignment_id=assignment.id)
            .order_by(AssignmentAttachment.sort_order, AssignmentAttachment.id)
            .all()
        )
        if remaining:
            first = remaining[0]
            assignment.attachment_filename = first.attachment_filename
            assignment.attachment_original_filename = first.attachment_original_filename
            assignment.attachment_file_path = first.attachment_file_path
            assignment.attachment_file_size = first.attachment_file_size
            assignment.attachment_mime_type = first.attachment_mime_type
        else:
            assignment.attachment_filename = None
            assignment.attachment_original_filename = None
            assignment.attachment_file_path = None
            assignment.attachment_file_size = None
            assignment.attachment_mime_type = None

    files = request.files.getlist("assignment_files") if request.files else []
    if not files or not (files[0] and files[0].filename):
        single = request.files.get("assignment_file") if request.files else None
        files = [single] if single and single.filename else []
    named = [f for f in files if f and f.filename]
    if not named:
        return None

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "assignments")
    os.makedirs(upload_dir, exist_ok=True)
    existing_count = AssignmentAttachment.query.filter_by(assignment_id=assignment.id).count()
    for idx, file in enumerate(named):
        if not allowed_file(file.filename):
            return f'File type not allowed. Allowed types are: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
        filename = secure_filename(file.filename)
        unique_filename = (
            f"assignment_{assignment.class_id}_{assignment.id}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{existing_count + idx}_{filename}"
        )
        filepath = os.path.join(upload_dir, unique_filename)
        file.save(filepath)
        rel = os.path.join("assignments", unique_filename)
        att = AssignmentAttachment(
            assignment_id=assignment.id,
            attachment_filename=unique_filename,
            attachment_original_filename=filename,
            attachment_file_path=rel,
            attachment_file_size=os.path.getsize(filepath),
            attachment_mime_type=file.content_type or None,
            sort_order=existing_count + idx,
        )
        db.session.add(att)
        if existing_count + idx == 0 or not assignment.attachment_filename:
            assignment.attachment_filename = unique_filename
            assignment.attachment_original_filename = filename
            assignment.attachment_file_path = rel
            assignment.attachment_file_size = os.path.getsize(filepath)
            assignment.attachment_mime_type = file.content_type
    return None


def _apply_group_attachment_updates(ga: GroupAssignment, body: dict[str, Any]) -> str | None:
    import os
    from datetime import datetime

    from flask import current_app, request
    from werkzeug.utils import secure_filename

    from management_routes.utils import ALLOWED_EXTENSIONS, allowed_file

    clear_attachment = _truthy_form_bool(body.get("clear_attachment")) or (
        "remove_attachment_ids" in body and body.get("remove_attachment_ids") not in (None, "", [])
    )
    if clear_attachment and ga.attachment_filename:
        upload = current_app.config["UPLOAD_FOLDER"]
        for path in (
            ga.attachment_file_path,
            os.path.join(upload, ga.attachment_file_path) if ga.attachment_file_path else None,
            os.path.join(upload, "group_assignments", ga.attachment_filename),
            os.path.join(upload, ga.attachment_filename),
        ):
            try:
                if path and os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass
        ga.attachment_filename = None
        ga.attachment_original_filename = None
        ga.attachment_file_path = None
        ga.attachment_file_size = None
        ga.attachment_mime_type = None

    file = None
    if request.files:
        files = request.files.getlist("assignment_files") or []
        if files and files[0] and files[0].filename:
            file = files[0]
        else:
            file = request.files.get("assignment_file") or request.files.get("attachment")
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        return f'File type not allowed. Allowed types are: {", ".join(sorted(ALLOWED_EXTENSIONS))}'

    filename = secure_filename(file.filename)
    unique_filename = (
        f"group_assignment_{ga.class_id}_{ga.id}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    )
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "group_assignments")
    os.makedirs(upload_dir, exist_ok=True)
    abs_path = os.path.join(upload_dir, unique_filename)
    file.save(abs_path)
    ga.attachment_filename = unique_filename
    ga.attachment_original_filename = filename
    ga.attachment_file_path = os.path.join("group_assignments", unique_filename)
    ga.attachment_file_size = os.path.getsize(abs_path)
    ga.attachment_mime_type = file.content_type
    return None


def save_individual_assignment_edit(assignment_id: int, body: dict[str, Any]) -> dict[str, Any]:
    assignment = Assignment.query.get_or_404(assignment_id)
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    due_date = _parse_edit_datetime(body.get("due_date"))
    quarter = str(body.get("quarter") or "").strip()
    status = (body.get("status") or "Active").strip()

    if not title or not due_date or not quarter:
        return {"success": False, "message": "Title, due date, and quarter are required."}

    valid_statuses = {"Active", "Inactive", "Upcoming", "Voided"}
    if status not in valid_statuses:
        return {"success": False, "message": "Invalid assignment status."}

    total_points = body.get("total_points")
    try:
        total_points = float(total_points) if total_points is not None else float(assignment.total_points or 100)
    except (TypeError, ValueError):
        total_points = float(assignment.total_points or 100)
    if total_points <= 0:
        total_points = 100.0

    assignment.title = title
    assignment.description = description
    assignment.due_date = due_date
    assignment.quarter = quarter
    assignment.status = status
    assignment.assignment_context = body.get("assignment_context") or assignment.assignment_context or "homework"
    assignment.assignment_category = (body.get("assignment_category") or "").strip() or None
    try:
        assignment.category_weight = float(body.get("category_weight") or 0)
    except (TypeError, ValueError):
        pass
    assignment.total_points = total_points
    assignment.allow_extra_credit = _truthy_form_bool(body.get("allow_extra_credit"))
    try:
        assignment.max_extra_credit_points = float(body.get("max_extra_credit_points") or 0)
    except (TypeError, ValueError):
        assignment.max_extra_credit_points = 0.0
    if not assignment.allow_extra_credit:
        assignment.max_extra_credit_points = 0.0
    assignment.late_penalty_enabled = _truthy_form_bool(body.get("late_penalty_enabled"))
    try:
        assignment.late_penalty_per_day = float(body.get("late_penalty_per_day") or 0)
        assignment.late_penalty_max_days = int(body.get("late_penalty_max_days") or 0)
    except (TypeError, ValueError):
        pass
    if not assignment.late_penalty_enabled:
        assignment.late_penalty_per_day = 0.0
        assignment.late_penalty_max_days = 0

    open_date = _parse_edit_datetime(body.get("open_date"))
    close_date = _parse_edit_datetime(body.get("close_date"))
    assignment.open_date = open_date
    assignment.close_date = close_date

    if _truthy_form_bool(body.get("status_revert_enabled")) and body.get("status_override_until"):
        override_until = _parse_edit_datetime(body.get("status_override_until"))
        if override_until:
            assignment.status_override = status
            assignment.status_override_until = override_until
        else:
            assignment.status_override = None
            assignment.status_override_until = None
    else:
        assignment.status_override = None
        assignment.status_override_until = None

    quiz_raw = body.get("quiz")
    if isinstance(quiz_raw, str) and quiz_raw.strip():
        try:
            body["quiz"] = json.loads(quiz_raw)
        except json.JSONDecodeError:
            body["quiz"] = None
    discussion_raw = body.get("discussion")
    if isinstance(discussion_raw, str) and discussion_raw.strip():
        try:
            body["discussion"] = json.loads(discussion_raw)
        except json.JSONDecodeError:
            body["discussion"] = None

    atype = (assignment.assignment_type or "pdf").lower()
    if atype == "quiz" and isinstance(body.get("quiz"), dict):
        q = body["quiz"]
        try:
            assignment.time_limit_minutes = int(q["time_limit_minutes"]) if q.get("time_limit_minutes") not in (None, "") else None
        except (TypeError, ValueError):
            assignment.time_limit_minutes = None
        try:
            assignment.max_attempts = max(1, int(q.get("max_attempts") or 1))
        except (TypeError, ValueError):
            assignment.max_attempts = 1
        assignment.shuffle_questions = bool(q.get("shuffle_questions"))
        assignment.show_correct_answers = bool(q.get("show_correct_answers", True))
        assignment.allow_save_and_continue = bool(q.get("allow_save_and_continue"))
        try:
            assignment.max_save_attempts = int(q.get("max_save_attempts") or 10)
            assignment.save_timeout_minutes = int(q.get("save_timeout_minutes") or 30)
        except (TypeError, ValueError):
            pass
    if atype == "discussion" and isinstance(body.get("discussion"), dict):
        assignment.allow_student_edit_posts = bool(body["discussion"].get("allow_student_edit_posts"))

    attach_err = _apply_individual_attachment_updates(assignment, body)
    if attach_err:
        db.session.rollback()
        return {"success": False, "message": attach_err}

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "message": str(exc)}
    return {"success": True, "message": "Assignment updated."}


def save_group_assignment_edit(assignment_id: int, body: dict[str, Any]) -> dict[str, Any]:
    ga = GroupAssignment.query.get_or_404(assignment_id)
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    due_date = _parse_edit_datetime(body.get("due_date"))
    quarter = str(body.get("quarter") or "").strip()
    status = (body.get("status") or "Active").strip()

    if not title or not due_date or not quarter:
        return {"success": False, "message": "Title, due date, and quarter are required."}

    ga.title = title
    ga.description = description
    ga.due_date = due_date
    ga.quarter = quarter
    ga.status = status
    ga.assignment_context = body.get("assignment_context") or ga.assignment_context or "homework"
    ga.assignment_category = (body.get("assignment_category") or "").strip() or None
    try:
        ga.category_weight = float(body.get("category_weight") or 0)
        ga.total_points = float(body.get("total_points") or ga.total_points or 100)
    except (TypeError, ValueError):
        pass
    ga.allow_extra_credit = _truthy_form_bool(body.get("allow_extra_credit"))
    try:
        ga.max_extra_credit_points = float(body.get("max_extra_credit_points") or 0)
    except (TypeError, ValueError):
        ga.max_extra_credit_points = 0.0
    ga.late_penalty_enabled = _truthy_form_bool(body.get("late_penalty_enabled"))
    ga.allow_individual = _truthy_form_bool(body.get("allow_individual"))
    ga.open_date = _parse_edit_datetime(body.get("open_date"))
    ga.close_date = _parse_edit_datetime(body.get("close_date"))

    attach_err = _apply_group_attachment_updates(ga, body)
    if attach_err:
        db.session.rollback()
        return {"success": False, "message": attach_err}

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "message": str(exc)}
    return {"success": True, "message": "Group assignment updated."}


def query_individual_assignment_submissions(assignment_id: int) -> dict[str, Any]:
    from collections import defaultdict

    from models import DiscussionPost, DiscussionThread

    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    students = _class_students(class_obj.id) if class_obj else []
    atype = _normalize_assignment_type(assignment.assignment_type)
    total_points = float(assignment.total_points or assignment.points or 100)
    flags = _individual_legacy_flags(assignment)
    grading_on_submissions = flags.get("legacy_reason") in ("discussion", "quiz_open_ended_grade")
    has_open_ended = flags.get("legacy_reason") == "quiz_open_ended_grade"

    if _is_pdf_paper_type(assignment.assignment_type):
        ui_mode = "pdf"
    elif atype == "quiz":
        ui_mode = "quiz"
    elif atype == "discussion":
        ui_mode = "discussion"
    else:
        ui_mode = "default"

    submissions = Submission.query.filter_by(assignment_id=assignment_id).order_by(Submission.submitted_at.asc()).all()
    submissions_by_student: dict[int, list] = defaultdict(list)
    for sub in submissions:
        submissions_by_student[sub.student_id].append(sub)

    grades_ordered = Grade.query.filter_by(assignment_id=assignment_id).order_by(Grade.graded_at.desc()).all()
    grades_dict: dict[int, Grade] = {}
    for g in grades_ordered:
        if g.student_id not in grades_dict:
            grades_dict[g.student_id] = g

    extensions = {
        e.student_id: e
        for e in AssignmentExtension.query.filter_by(assignment_id=assignment_id, is_active=True).all()
    }

    requirements = _discussion_requirements(assignment) if atype == "discussion" else None
    discussion_threads_by_student: dict[int, list] = defaultdict(list)
    discussion_posts_by_student: dict[int, list] = defaultdict(list)
    threads_by_id: dict[int, DiscussionThread] = {}

    if atype == "discussion":
        all_threads = (
            DiscussionThread.query.filter_by(assignment_id=assignment_id)
            .order_by(DiscussionThread.is_pinned.desc(), DiscussionThread.created_at.desc())
            .all()
        )
        threads_by_id = {t.id: t for t in all_threads}
        thread_ids = list(threads_by_id.keys())
        all_posts = (
            DiscussionPost.query.filter(DiscussionPost.thread_id.in_(thread_ids)).all() if thread_ids else []
        )
        for thread in all_threads:
            discussion_threads_by_student[thread.student_id].append(thread)
        for post in all_posts:
            discussion_posts_by_student[post.student_id].append(post)

    rows: list[dict[str, Any]] = []
    submitted_count = 0
    late_count = 0
    on_time_count = 0
    graded_count = 0

    for student in students:
        subs_for_student = submissions_by_student.get(student.id, [])
        submission = subs_for_student[-1] if subs_for_student else None
        grade = grades_dict.get(student.id)
        status = _submission_status_for_student(student.id, submission, assignment, extensions)

        if submission:
            submitted_count += 1
            if status == "late":
                late_count += 1
            else:
                on_time_count += 1

        grade_info = _grade_info_dict(grade)
        is_voided = bool(grade and grade.is_voided)
        if grade_info and not is_voided:
            graded_count += 1

        base_row: dict[str, Any] = {
            "student": _student_brief(student),
            "status": status,
            "grade": grade_info,
            "is_voided": is_voided,
        }

        if ui_mode == "pdf" or ui_mode == "default":
            import os

            download_url = None
            if submission and submission.id and submission.file_path:
                download_url = _submission_download_url(assignment_id, submission.id)
            rows.append(
                {
                    **base_row,
                    "submission_id": submission.id if submission else None,
                    "submission_type": submission.submission_type if submission else None,
                    "submitted_at": _iso(submission.submitted_at) if submission else None,
                    "submission_notes": (submission.submission_notes or "") if submission else None,
                    "file_name": (
                        os.path.basename(submission.file_path)
                        if submission and submission.file_path
                        else None
                    ),
                    "download_url": download_url,
                }
            )
        elif ui_mode == "quiz":
            questions, auto_points = _quiz_questions_payload(assignment_id, student.id)
            rows.append(
                {
                    **base_row,
                    "submitted_at": _iso(submission.submitted_at) if submission else None,
                    "quiz_attempts": len(subs_for_student),
                    "quiz_attempt_details": _quiz_attempt_details(subs_for_student),
                    "auto_points": round(auto_points, 2),
                    "questions": questions,
                    "has_submission": submission is not None,
                }
            )
        elif ui_mode == "discussion":
            student_threads = discussion_threads_by_student.get(student.id, [])
            student_posts = discussion_posts_by_student.get(student.id, [])
            threads_count = len(student_threads)
            replies_count = len(student_posts)
            min_initial = requirements["min_initial_posts"] if requirements else 1
            min_replies = requirements["min_replies"] if requirements else 2
            initial_met = threads_count >= min_initial
            replies_met = replies_count >= min_replies
            peer_thread_ids = {
                p.thread_id
                for p in student_posts
                if p.thread_id in threads_by_id and threads_by_id[p.thread_id].student_id != student.id
            }
            rows.append(
                {
                    **base_row,
                    "participation": {
                        "threads_count": threads_count,
                        "replies_count": replies_count,
                        "total_posts": threads_count + replies_count,
                        "min_initial_posts": min_initial,
                        "min_replies": min_replies,
                        "initial_posts_met": initial_met,
                        "replies_met": replies_met,
                        "peer_threads_replied": len(peer_thread_ids),
                        "requirements_met": initial_met and replies_met,
                    },
                    "threads": [
                        {
                            "id": t.id,
                            "title": t.title or "",
                            "content": t.content or "",
                            "created_at": _iso(t.created_at),
                            "is_pinned": bool(t.is_pinned),
                        }
                        for t in student_threads
                    ],
                    "replies": [
                        {
                            "id": p.id,
                            "content": p.content or "",
                            "created_at": _iso(p.created_at),
                            "thread_title": (
                                threads_by_id[p.thread_id].title
                                if p.thread_id in threads_by_id
                                else "Thread"
                            ),
                            "is_peer_thread": (
                                p.thread_id in threads_by_id
                                and threads_by_id[p.thread_id].student_id != student.id
                            ),
                        }
                        for p in sorted(student_posts, key=lambda x: x.created_at or datetime.min)
                    ],
                }
            )

    rows.sort(key=lambda r: (0 if r["status"] != "not_submitted" else 1, r["student"]["display_name"]))

    class_id = assignment.class_id
    return {
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "assignment_type": assignment.assignment_type,
            "due_date": _iso(assignment.due_date),
            "class_id": class_id,
            "total_points": total_points,
        },
        "ui_mode": ui_mode,
        "grading_on_submissions": grading_on_submissions,
        "show_grade_link": not grading_on_submissions and flags.get("legacy_reason") != "quiz_auto_graded",
        "has_open_ended": has_open_ended,
        "requirements": requirements,
        "class": _class_brief(class_obj) if class_obj else {"id": None, "name": "Unknown"},
        "stats": {
            "total_students": len(students),
            "submitted_count": submitted_count,
            "graded_count": graded_count,
            "late_count": late_count,
            "on_time_count": on_time_count,
            "submission_rate": round((submitted_count / len(students) * 100) if students else 0, 1),
        },
        "rows": rows,
        "links": {
            "view_spa": f"/management/assignments/{class_id}/individual/{assignment.id}/view",
            "grade_spa": f"/management/assignments/{class_id}/individual/{assignment.id}/grade",
            "submissions_spa": f"/management/assignments/{class_id}/individual/{assignment.id}/submissions",
        },
    }


def query_group_assignment_submissions(assignment_id: int) -> dict[str, Any]:
    ga = GroupAssignment.query.get_or_404(assignment_id)
    groups, total_students = _group_roster(ga)
    submissions = GroupSubmission.query.filter_by(group_assignment_id=assignment_id).all()
    submitted_group_ids = {s.group_id for s in submissions if getattr(s, "group_id", None)}

    rows = []
    for group in groups:
        has_sub = group["id"] in submitted_group_ids
        rows.append(
            {
                "group": {"id": group["id"], "name": group["name"]},
                "member_count": len(group["members"]),
                "submitted": has_sub,
                "members": group["members"],
            }
        )

    return {
        "assignment": {
            "id": ga.id,
            "title": ga.title,
            "assignment_type": ga.assignment_type,
            "due_date": _iso(ga.due_date),
            "class_id": ga.class_id,
        },
        "class": {"id": ga.class_id, "name": ga.class_info.name if ga.class_info else "Unknown"},
        "stats": {
            "total_groups": len(groups),
            "submitted_count": len(submitted_group_ids),
            "total_students": total_students,
        },
        "rows": rows,
        "links": {
            "view_spa": f"/management/assignments/{ga.class_id}/group/{ga.id}/view",
            "grade_spa": f"/management/assignments/{ga.class_id}/group/{ga.id}/grade",
        },
    }
