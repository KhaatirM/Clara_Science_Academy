"""PDF login letter for a Family Portal parent account."""

from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Any

from flask import current_app, has_request_context, make_response, render_template, url_for
from werkzeug.security import generate_password_hash

from extensions import db
from models import ParentStudentLink, Student, User
from utils.parent_portal import (
    _temporary_parent_password,
    enrolled_classes_for_student,
    get_active_school_year,
    normalize_parent_email,
    parent_display_name,
    parent_slot_fields,
)


def _login_url() -> str:
    if has_request_context():
        try:
            return url_for("auth.login", _external=True)
        except Exception:
            pass
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    return f"{base}/login" if base else "/login"


def _letter_filename(display_name: str) -> str:
    last = (display_name or "Parent").strip().split()[-1]
    safe = re.sub(r"[^A-Za-z0-9_-]+", "", last) or "Parent"
    return f"Family-Portal-Login-{safe}.pdf"


def _phone_for_parent(user: User, links: list[ParentStudentLink]) -> str:
    email = normalize_parent_email(user.email)
    for link in links:
        student = link.student
        if not student:
            continue
        info = parent_slot_fields(student, link.parent_slot or 1)
        if email and normalize_parent_email(info.get("email")) == email and info.get("phone"):
            return info["phone"] or ""
    for link in links:
        student = link.student
        if not student:
            continue
        info = parent_slot_fields(student, link.parent_slot or 1)
        if info.get("phone"):
            return info["phone"] or ""
    return ""


def _student_rows(links: list[ParentStudentLink], school_year) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for link in links:
        student = link.student
        if not student:
            continue
        if getattr(student, "is_deleted", False) or not getattr(student, "is_active", True):
            continue
        classes: list[str] = []
        if school_year:
            for class_obj in enrolled_classes_for_student(student.id, school_year.id):
                label = class_obj.name or "Class"
                subject = (getattr(class_obj, "subject", None) or "").strip()
                if subject and subject.lower() not in label.lower():
                    label = f"{label} ({subject})"
                classes.append(label)
        rows.append(
            {
                "name": f"{student.first_name or ''} {student.last_name or ''}".strip() or "Student",
                "student_id": student.student_id or "—",
                "grade_level": student.grade_level if student.grade_level is not None else "—",
                "relationship": (link.relationship or "Parent").strip() or "Parent",
                "classes": classes,
            }
        )
    return rows


def issue_temporary_password(user: User, links: list[ParentStudentLink] | None = None) -> str:
    """Set a new temporary password on the session. Caller commits after the PDF exists."""
    if links is None:
        links = ParentStudentLink.query.filter_by(parent_user_id=user.id).all()
    temp_password = _temporary_parent_password(_phone_for_parent(user, links))
    user.password_hash = generate_password_hash(temp_password)
    user.is_temporary_password = True
    return temp_password


def build_parent_login_letter_pdf(user: User, *, reset_password: bool) -> tuple[bytes, str, bool]:
    """
    Build the login letter.

    Returns ``(pdf_bytes, filename, password_reset)``.
    A still-temporary account is always re-issued so the letter can show a password.
    An account that already has a chosen password is reset only when ``reset_password`` is True.
    The password change is committed only after the PDF is generated.
    """
    if (user.role or "") != "Parent":
        raise ValueError("That account is not a parent login.")

    links = (
        ParentStudentLink.query.filter_by(parent_user_id=user.id)
        .join(Student)
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    still_temporary = bool(getattr(user, "is_temporary_password", False))
    should_reset = bool(reset_password) or still_temporary
    temp_password = issue_temporary_password(user, links) if should_reset else None

    school_year = get_active_school_year()
    display_name = parent_display_name(user)
    students = _student_rows(links, school_year)
    filename = _letter_filename(display_name)

    try:
        html = render_template(
            "management/parent_login_letter_pdf.html",
            parent_name=display_name,
            parent_email=user.email or "",
            username=user.username or "",
            login_url=_login_url(),
            temporary_password=temp_password,
            password_was_reset=should_reset,
            students=students,
            school_year_name=school_year.name if school_year else None,
            generated_on=datetime.now().strftime("%B %d, %Y"),
        )
        from weasyprint import HTML

        buffer = BytesIO()
        HTML(string=html, base_url=current_app.root_path).write_pdf(buffer)
        pdf_bytes = buffer.getvalue()
    except Exception:
        db.session.rollback()
        raise

    if should_reset:
        db.session.commit()
    return pdf_bytes, filename, should_reset


def parent_login_letter_response(user: User, *, reset_password: bool):
    pdf_bytes, filename, _reset = build_parent_login_letter_pdf(user, reset_password=reset_password)
    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
