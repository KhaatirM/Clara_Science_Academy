"""Student class detail payload for the React SPA."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask_login import current_user
from sqlalchemy.orm import joinedload

from management_routes.student_assistant_utils import (
    assignment_student_visibility_filter,
    student_is_active_assistant_for_class,
)
from management_routes.class_syllabus_spa_helpers import class_supports_syllabus
from models import (
    Announcement,
    Assignment,
    Class,
    Enrollment,
    Grade,
    Student,
    Submission,
    TeacherStaff,
)


def _fmt_due(value) -> str | None:
    if not value:
        return None
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y")
    except Exception:
        pass
    return str(value)


def _type_label(assignment_type: str | None) -> str:
    t = (assignment_type or "pdf").lower()
    if t == "quiz":
        return "Quiz"
    if t == "discussion":
        return "Discussion"
    return "PDF/Paper"


def _student_email(student: Student) -> str | None:
    if student.email:
        return student.email
    user = getattr(student, "user", None)
    if user and getattr(user, "google_workspace_email", None):
        return user.google_workspace_email
    if user and getattr(user, "email", None):
        return user.email
    return None


def _teacher_school_email(teacher: TeacherStaff) -> str | None:
    """School / Google Workspace address only — never personal email on file."""
    remembered = (getattr(teacher, "google_workspace_email", None) or "").strip()
    if remembered:
        return remembered
    user = getattr(teacher, "user", None)
    if user is None:
        from models import User

        user = User.query.filter_by(teacher_staff_id=teacher.id).first()
    ws = (getattr(user, "google_workspace_email", None) or "").strip() if user else ""
    return ws or None


def build_student_class_detail_payload(class_id: int) -> tuple[dict[str, Any] | None, str | None, int]:
    from .routes import (
        _get_points_earned,
        calculate_gpa,
        get_letter_grade,
        get_student_assignment_status,
        get_student_class_group,
    )

    sid = getattr(current_user, "student_id", None)
    if not sid:
        return None, "Student profile required", 403
    student = Student.query.get(sid)
    if not student:
        return None, "Student not found", 404

    class_obj = Class.query.options(joinedload(Class.teacher)).get(class_id)
    if not class_obj:
        return None, "Class not found", 404

    enrollment = Enrollment.query.filter_by(
        student_id=student.id, class_id=class_id, is_active=True
    ).first()
    if not enrollment:
        return None, "You are not enrolled in this class", 403

    teacher = None
    if class_obj.teacher_id:
        teacher = TeacherStaff.query.get(class_obj.teacher_id)

    enrollments = (
        Enrollment.query.filter_by(class_id=class_id, is_active=True)
        .options(joinedload(Enrollment.student).joinedload(Student.user))
        .all()
    )
    enrolled_students = [e.student for e in enrollments if e.student]
    enrolled_students.sort(
        key=lambda s: ((s.last_name or "").lower(), (s.first_name or "").lower())
    )

    assignments = (
        Assignment.query.filter(
            Assignment.class_id == class_id,
            assignment_student_visibility_filter(),
        )
        .order_by(Assignment.due_date.desc())
        .all()
    )

    all_grades = (
        Grade.query.filter_by(student_id=student.id)
        .order_by(Grade.graded_at.desc(), Grade.id.desc())
        .all()
    )
    grades_by_assignment: dict[int, list] = {}
    for g in all_grades:
        if not g.assignment:
            continue
        grades_by_assignment.setdefault(g.assignment_id, []).append(g)

    grades_dict = {aid: glist[0] for aid, glist in grades_by_assignment.items() if glist}

    student_submissions = {
        s.assignment_id: s for s in Submission.query.filter_by(student_id=student.id).all()
    }

    class_percentages_for_gpa: list[float] = []
    assignments_out: list[dict[str, Any]] = []

    for assignment in assignments:
        submission = student_submissions.get(assignment.id)
        grade = grades_dict.get(assignment.id)
        status = get_student_assignment_status(assignment, submission, grade, student.id)

        letter = None
        if status in ("completed", "submitted_in_person") and grade and grade.grade_data:
            try:
                gdata = (
                    json.loads(grade.grade_data)
                    if isinstance(grade.grade_data, str)
                    else grade.grade_data
                )
                points_earned = _get_points_earned(gdata)
                if points_earned is not None:
                    points_earned = float(points_earned)
                    total_points = (
                        assignment.total_points
                        if (assignment.total_points and assignment.total_points > 0)
                        else 100.0
                    )
                    pct = (points_earned / total_points * 100) if total_points > 0 else 0
                    letter = get_letter_grade(pct)
                    class_percentages_for_gpa.append(pct)
            except (ValueError, TypeError, json.JSONDecodeError):
                pass

        atype = (assignment.assignment_type or "pdf").lower()
        primary_url = None
        if atype == "quiz":
            primary_url = f"/app/student/take-quiz/{assignment.id}"
        elif atype == "discussion":
            primary_url = f"/app/student/discussion/{assignment.id}"

        assignments_out.append(
            {
                "id": assignment.id,
                "title": assignment.title,
                "description_preview": (assignment.description or "")[:120],
                "assignment_type": assignment.assignment_type or "pdf",
                "type_label": _type_label(assignment.assignment_type),
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "due_display": _fmt_due(assignment.due_date),
                "status": status,
                "letter_grade": letter,
                "primary_url": primary_url,
            }
        )

    class_gpa = calculate_gpa(class_percentages_for_gpa) if class_percentages_for_gpa else 0.0

    announcements = (
        Announcement.query.filter_by(class_id=class_id)
        .order_by(Announcement.timestamp.desc())
        .limit(8)
        .all()
    )
    announcements_out = [
        {
            "id": a.id,
            "title": a.title,
            "message": a.message,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "timestamp_display": a.timestamp.strftime("%b %d, %Y · %I:%M %p")
            if a.timestamp
            else None,
        }
        for a in announcements
    ]

    is_assistant = student_is_active_assistant_for_class(student.id, class_id)

    group = get_student_class_group(student.id, class_id)
    group_payload = None
    if group:
        members = []
        for m in getattr(group, "members", []) or []:
            st = getattr(m, "student", None)
            if not st:
                continue
            members.append(
                {
                    "id": st.id,
                    "name": f"{st.first_name or ''} {st.last_name or ''}".strip(),
                    "is_you": st.id == student.id,
                }
            )
        group_payload = {
            "id": group.id,
            "name": group.name,
            "members": members,
        }

    try:
        grade_display = class_obj.get_grade_levels_display() or "All Grades"
    except Exception:
        grade_display = getattr(class_obj, "grade_level", None) or "All Grades"

    teacher_payload = None
    if teacher:
        teacher_payload = {
            "id": teacher.id,
            "name": f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() or "Teacher",
            "position": teacher.position or "Teacher",
            "email": _teacher_school_email(teacher),
            "phone": teacher.phone,
        }

    roster = [
        {
            "id": s.id,
            "name": f"{s.first_name or ''} {s.last_name or ''}".strip(),
            "email": _student_email(s),
            "is_you": s.id == student.id,
        }
        for s in enrolled_students
    ]

    return {
        "class": {
            "id": class_obj.id,
            "name": class_obj.name,
            "subject": class_obj.subject or "General",
            "grade_levels_display": str(grade_display),
        },
        "teacher": teacher_payload,
        "stats": {
            "student_count": len(roster),
            "assignment_count": len(assignments_out),
            "class_gpa": round(float(class_gpa or 0), 2),
            "graded_count": len(class_percentages_for_gpa),
        },
        "group": group_payload,
        "roster": roster,
        "announcements": announcements_out,
        "assignments": assignments_out[:8],
        "is_assistant": is_assistant,
        "links": {
            "back": "/app/student/classes",
            "assignments": f"/app/student/assignments?class_id={class_id}",
            "class_notes": f"/app/student/classes/{class_id}/notes",
            "assistant": f"/assistant/class/{class_id}" if is_assistant else None,
            **(
                {"syllabus": "modal:syllabus"}
                if class_supports_syllabus(class_obj)
                else {}
            ),
        },
        "server_now": datetime.now().isoformat(),
    }, None, 200
