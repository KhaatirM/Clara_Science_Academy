"""Parent portal: provision logins, link children, build read-only child views."""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from typing import Any, Optional

from werkzeug.security import generate_password_hash

from extensions import db
from models import (
    Assignment,
    Attendance,
    Class,
    Enrollment,
    Grade,
    GroupAssignment,
    GroupGrade,
    ParentStudentLink,
    SchoolYear,
    Student,
    User,
)


def normalize_parent_email(email: Optional[str]) -> Optional[str]:
    e = (email or "").strip().lower()
    return e or None


def parent_slot_fields(student: Student, slot: int) -> dict[str, Optional[str]]:
    """Return first/last/email/phone/relationship for parent slot 1 or 2."""
    if slot == 1:
        return {
            "first_name": (student.parent1_first_name or "").strip(),
            "last_name": (student.parent1_last_name or "").strip(),
            "email": normalize_parent_email(student.parent1_email),
            "phone": (student.parent1_phone or "").strip(),
            "relationship": (student.parent1_relationship or "").strip() or "Parent",
        }
    if slot == 2:
        return {
            "first_name": (student.parent2_first_name or "").strip(),
            "last_name": (student.parent2_last_name or "").strip(),
            "email": normalize_parent_email(student.parent2_email),
            "phone": (student.parent2_phone or "").strip(),
            "relationship": (student.parent2_relationship or "").strip() or "Parent",
        }
    raise ValueError("slot must be 1 or 2")


def _allocate_parent_username(email: str, first_name: str, last_name: str) -> str:
    local = email.split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9]", "", local)
    if not base and first_name and last_name:
        base = re.sub(
            r"[^a-z0-9]",
            "",
            f"{first_name[0]}{last_name}".lower(),
        )
    if not base:
        base = "parent"
    username = base[:24]
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base[:20]}{counter}"
        counter += 1
    return username


def _temporary_parent_password(phone: str = "") -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) >= 4:
        return f"Parent{digits[-4:]}"
    return f"Parent{secrets.token_hex(3)}"


def find_parent_user_by_email(email: Optional[str]) -> Optional[User]:
    norm = normalize_parent_email(email)
    if not norm:
        return None
    return User.query.filter(
        db.func.lower(User.email) == norm,
        User.role == "Parent",
    ).first()


def get_linked_students(parent_user_id: int, *, active_only: bool = True) -> list[Student]:
    q = (
        Student.query.join(ParentStudentLink, ParentStudentLink.student_id == Student.id)
        .filter(ParentStudentLink.parent_user_id == parent_user_id)
        .order_by(Student.last_name, Student.first_name)
    )
    if active_only:
        q = q.filter(Student.is_deleted.is_(False), Student.is_active.is_(True))
    return q.all()


def parent_has_access(parent_user_id: int, student_id: int) -> bool:
    return (
        ParentStudentLink.query.filter_by(
            parent_user_id=parent_user_id,
            student_id=student_id,
        ).first()
        is not None
    )


def parent_portal_status_for_student(student: Student) -> dict[str, Any]:
    """JSON-friendly parent login status for admin UI."""
    out: dict[str, Any] = {"parent1": None, "parent2": None}
    for slot in (1, 2):
        info = parent_slot_fields(student, slot)
        email = info["email"]
        if not email:
            out[f"parent{slot}"] = {
                "has_email": False,
                "has_login": False,
                "username": None,
                "email": None,
            }
            continue
        user = find_parent_user_by_email(email)
        linked = False
        if user:
            linked = parent_has_access(user.id, student.id)
        out[f"parent{slot}"] = {
            "has_email": True,
            "has_login": bool(user),
            "is_linked": linked,
            "username": user.username if user else None,
            "email": email,
            "name": f"{info['first_name']} {info['last_name']}".strip(),
        }
    return out


def provision_parent_for_student_slot(student: Student, slot: int) -> Optional[dict[str, Any]]:
    """
    Create or reuse a Parent User and link them to ``student`` for slot 1 or 2.
    Caller must commit. Returns credential dict or None if slot has no email.
    """
    if getattr(student, "is_deleted", False):
        return None

    info = parent_slot_fields(student, slot)
    email = info["email"]
    if not email:
        return None

    first_name = info["first_name"] or "Parent"
    last_name = info["last_name"] or (student.last_name or "Guardian")
    created_new = False
    temp_password: Optional[str] = None

    user = find_parent_user_by_email(email)
    if not user:
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user and user.role != "Parent":
            raise ValueError(
                f"Email {email} is already used by a {user.role} account. "
                "Use a different parent email or contact Tech."
            )
        if not user:
            temp_password = _temporary_parent_password(info["phone"])
            user = User(
                username=_allocate_parent_username(email, first_name, last_name),
                password_hash=generate_password_hash(temp_password),
                role="Parent",
                email=email,
                is_temporary_password=True,
            )
            db.session.add(user)
            db.session.flush()
            created_new = True

    link = ParentStudentLink.query.filter_by(
        parent_user_id=user.id,
        student_id=student.id,
    ).first()
    if not link:
        link = ParentStudentLink(
            parent_user_id=user.id,
            student_id=student.id,
            relationship=info["relationship"],
            parent_slot=slot,
        )
        db.session.add(link)
    else:
        link.relationship = info["relationship"]
        link.parent_slot = slot

    result: dict[str, Any] = {
        "slot": slot,
        "student_id": student.id,
        "student_name": f"{student.first_name} {student.last_name}".strip(),
        "parent_name": f"{first_name} {last_name}".strip(),
        "email": email,
        "username": user.username,
        "created_new": created_new,
        "portal_password": temp_password,
    }
    return result


def provision_all_parents_for_student(student: Student) -> list[dict[str, Any]]:
    results = []
    for slot in (1, 2):
        try:
            row = provision_parent_for_student_slot(student, slot)
            if row:
                results.append(row)
        except ValueError:
            raise
    return results


def _unlink_parent_slot(student_id: int, slot: int) -> None:
    """Remove the portal link for one parent slot when email is cleared or changed."""
    link = ParentStudentLink.query.filter_by(student_id=student_id, parent_slot=slot).first()
    if link:
        db.session.delete(link)


def sync_student_parent_portal(student: Student) -> list[dict[str, Any]]:
    """
    Align ``ParentStudentLink`` rows with ``parent1_*`` / ``parent2_*`` on the student.

    - Cleared email → unlink that slot for this student
    - Changed email → replace link for that slot
    - Present email → ensure Parent user exists and is linked

    Caller must commit. Returns credential dicts only for newly created parent accounts.
    """
    if getattr(student, "is_deleted", False):
        return []

    created: list[dict[str, Any]] = []
    for slot in (1, 2):
        info = parent_slot_fields(student, slot)
        email = info["email"]

        existing = ParentStudentLink.query.filter_by(
            student_id=student.id,
            parent_slot=slot,
        ).first()

        if not email:
            if existing:
                db.session.delete(existing)
            continue

        if existing:
            linked_email = normalize_parent_email(getattr(existing.parent_user, "email", None))
            if linked_email != email:
                db.session.delete(existing)

        row = provision_parent_for_student_slot(student, slot)
        if row and row.get("created_new") and row.get("portal_password"):
            created.append(row)

    return created


def _grade_points(grade_data: Any) -> Optional[float]:
    if grade_data is None:
        return None
    if isinstance(grade_data, str):
        try:
            grade_data = json.loads(grade_data)
        except json.JSONDecodeError:
            return None
    if not isinstance(grade_data, dict):
        return None
    val = grade_data.get("points_earned")
    if val is None:
        val = grade_data.get("score")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _percentage_from_grade(grade_row, *, assignment) -> Optional[float]:
    if not grade_row or grade_row.is_voided:
        return None
    if assignment and getattr(assignment, "status", None) == "Voided":
        return None
    pts = _grade_points(grade_row.grade_data)
    if pts is None:
        return None
    total = getattr(assignment, "total_points", None) or 100.0
    try:
        total_f = float(total)
        if total_f <= 0:
            return None
        return round(float(pts) / total_f * 100.0, 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def calculate_gpa_from_percentages(percentages: list[float]) -> float:
    if not percentages:
        return 0.0

    def pct_to_gpa(pct: float) -> float:
        if pct >= 93:
            return 4.0
        if pct >= 90:
            return 3.67
        if pct >= 87:
            return 3.33
        if pct >= 83:
            return 3.0
        if pct >= 80:
            return 2.67
        if pct >= 77:
            return 2.33
        if pct >= 73:
            return 2.0
        if pct >= 70:
            return 1.67
        if pct >= 67:
            return 1.33
        if pct >= 63:
            return 1.0
        if pct >= 60:
            return 0.67
        return 0.0

    pts = [pct_to_gpa(float(p)) for p in percentages]
    return round(sum(pts) / len(pts), 2)


def get_active_school_year() -> Optional[SchoolYear]:
    return SchoolYear.query.filter_by(is_active=True).first()


def enrolled_classes_for_student(student_id: int, school_year_id: int) -> list[Class]:
    enrollments = (
        Enrollment.query.filter_by(student_id=student_id, is_active=True)
        .join(Class)
        .filter(Class.school_year_id == school_year_id, Class.is_active.is_(True))
        .all()
    )
    return [e.class_info for e in enrollments if e.class_info]


def build_child_academic_summary(student_id: int) -> dict[str, Any]:
    """Read-only grades, GPA, attendance for parent views."""
    student = Student.query.get_or_404(student_id)
    school_year = get_active_school_year()
    if not school_year:
        return {
            "student": student,
            "school_year": None,
            "classes": [],
            "class_grades": {},
            "gpa": 0.0,
            "attendance_summary": {},
            "recent_grades": [],
        }

    classes = enrolled_classes_for_student(student_id, school_year.id)
    class_grades: dict[str, float] = {}
    all_pcts: list[float] = []
    recent_grades: list[dict[str, Any]] = []

    for c in classes:
        pcts: list[float] = []
        for g in Grade.query.join(Assignment).filter(
            Grade.student_id == student_id,
            Assignment.class_id == c.id,
            Assignment.school_year_id == school_year.id,
        ).all():
            pct = _percentage_from_grade(g, assignment=g.assignment)
            if pct is not None:
                pcts.append(pct)

        for g in GroupGrade.query.join(GroupAssignment).filter(
            GroupGrade.student_id == student_id,
            GroupAssignment.class_id == c.id,
            GroupAssignment.school_year_id == school_year.id,
        ).all():
            pct = _percentage_from_grade(g, assignment=g.group_assignment)
            if pct is not None:
                pcts.append(pct)

        if pcts:
            avg = round(sum(pcts) / len(pcts), 1)
            class_grades[c.name] = avg
            all_pcts.extend(pcts)

    for g in (
        Grade.query.filter_by(student_id=student_id)
        .join(Assignment)
        .filter(Assignment.status != "Voided", Assignment.school_year_id == school_year.id)
        .order_by(Grade.graded_at.desc())
        .limit(8)
        .all()
    ):
        if g.is_voided:
            continue
        pct = _percentage_from_grade(g, assignment=g.assignment)
        if pct is None:
            continue
        recent_grades.append(
            {
                "assignment_title": g.assignment.title if g.assignment else "Assignment",
                "class_name": g.assignment.class_info.name if g.assignment and g.assignment.class_info else "",
                "percentage": pct,
                "graded_at": g.graded_at,
            }
        )

    attendance_records = Attendance.query.filter_by(student_id=student_id).filter(
        Attendance.date >= school_year.start_date,
        Attendance.date <= school_year.end_date,
    ).all()
    attendance_summary = {
        "Present": len([r for r in attendance_records if r.status == "Present"]),
        "Tardy": len([r for r in attendance_records if r.status == "Tardy"]),
        "Absent": len([r for r in attendance_records if r.status == "Absent"]),
    }

    return {
        "student": student,
        "school_year": school_year,
        "classes": classes,
        "class_grades": class_grades,
        "gpa": calculate_gpa_from_percentages(all_pcts),
        "attendance_summary": attendance_summary,
        "recent_grades": recent_grades,
    }


def parent_display_name(user: User) -> str:
    links = ParentStudentLink.query.filter_by(parent_user_id=user.id).limit(1).all()
    if links:
        info = parent_slot_fields(links[0].student, links[0].parent_slot or 1)
        name = f"{info['first_name']} {info['last_name']}".strip()
        if name:
            return name
    if user.email:
        return user.email.split("@", 1)[0].replace(".", " ").title()
    return user.username or "Parent"
