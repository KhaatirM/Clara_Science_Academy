"""Teacher classes list payload for the React SPA."""

from __future__ import annotations

from typing import Any

from flask import url_for
from sqlalchemy import func, or_

from extensions import db
from management_routes.class_spa_helpers import _standards_flags
from management_routes.classes import serialize_class_list_item
from models import Assignment, Class, Enrollment, class_additional_teachers, class_substitute_teachers
from teacher_routes.utils import get_teacher_or_admin, is_admin
from utils.school_year_filters import get_active_school_year


def _teacher_accessible_classes(teacher) -> list[Class]:
    if is_admin():
        return Class.query.order_by(Class.name).all()
    if teacher is None:
        return []
    return (
        Class.query.filter(
            or_(
                Class.teacher_id == teacher.id,
                Class.id.in_(
                    db.session.query(class_additional_teachers.c.class_id).filter(
                        class_additional_teachers.c.teacher_id == teacher.id
                    )
                ),
                Class.id.in_(
                    db.session.query(class_substitute_teachers.c.class_id).filter(
                        class_substitute_teachers.c.teacher_id == teacher.id
                    )
                ),
            )
        )
        .order_by(Class.name)
        .all()
    )


def _teacher_classes_for_active_school_year(teacher) -> list[Class]:
    """Classes this teacher can access in the active school year only."""
    active = get_active_school_year()
    if not active:
        return []
    return [
        c
        for c in _teacher_accessible_classes(teacher)
        if c.school_year_id == active.id and c.is_active
    ]


def _teacher_class_links(class_id: int, features: dict[str, bool], google_classroom_id: str | None) -> dict[str, str]:
    links: dict[str, str] = {
        "view_class": f"/app/teacher/classes/{class_id}",
        "attendance": f"/app/teacher/attendance/take/{class_id}",
        "assignment": f"/app/teacher/assignments/create?class_id={class_id}",
        "link_google": "spa",
        "create_google": "spa",
        "unlink_google": "spa",
    }
    if features.get("grade1_standards"):
        links["grade1_standards"] = f"/app/teacher/classes/{class_id}/standards/grade1"
    if features.get("grade3_standards"):
        links["grade3_standards"] = f"/app/teacher/classes/{class_id}/standards/grade3"
    if google_classroom_id:
        links["open_google"] = f"https://classroom.google.com/c/{google_classroom_id}"
    return links


def build_teacher_classes_payload() -> tuple[dict[str, Any] | None, str | None]:
    try:
        from services.class_google_group import class_needs_google_integration

        teacher = get_teacher_or_admin()
        classes = _teacher_classes_for_active_school_year(teacher)
        active_school_year = get_active_school_year()

        class_ids = [c.id for c in classes]
        enrollment_counts = (
            dict(
                db.session.query(Enrollment.class_id, func.count(Enrollment.id))
                .filter(Enrollment.is_active.is_(True), Enrollment.class_id.in_(class_ids))
                .group_by(Enrollment.class_id)
                .all()
            )
            if class_ids
            else {}
        )
        assignment_counts = (
            dict(
                db.session.query(Assignment.class_id, func.count(Assignment.id))
                .filter(Assignment.class_id.in_(class_ids))
                .group_by(Assignment.class_id)
                .all()
            )
            if class_ids
            else {}
        )

        items: list[dict[str, Any]] = []
        linked_count = 0
        for cls in classes:
            show_google = class_needs_google_integration(cls)
            features = _standards_flags(cls)
            base = serialize_class_list_item(
                cls,
                enrollment_count=enrollment_counts.get(cls.id, 0),
                assignment_count=assignment_counts.get(cls.id, 0),
            )
            if show_google and base.get("google_classroom_linked"):
                linked_count += 1
            teacher_name = base["teacher"]["display_name"]
            items.append(
                {
                    **base,
                    "teacher_display": teacher_name if teacher_name and teacher_name != "N/A" else "Not Assigned",
                    "google_group_email": (cls.google_group_email or None) if show_google else None,
                    "show_google_integration": show_google,
                    "features": features,
                    "links": _teacher_class_links(cls.id, features, cls.google_classroom_id),
                }
            )

        total_enrollments = sum(i["enrollment_count"] for i in items)
        total_assignments = sum(i["assignment_count"] for i in items)

        return (
            {
                "items": items,
                "stats": {
                    "total_classes": len(items),
                    "total_enrollments": total_enrollments,
                    "linked_classrooms": linked_count,
                    "total_assignments": total_assignments,
                },
                "meta": {
                    "active_school_year_id": active_school_year.id if active_school_year else None,
                    "active_school_year_name": active_school_year.name if active_school_year else None,
                    "has_active_school_year": active_school_year is not None,
                },
            },
            None,
        )
    except Exception as exc:
        return None, str(exc)
