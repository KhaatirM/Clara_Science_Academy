"""SPA helpers for group assignment creation."""

from __future__ import annotations

from typing import Any

from flask import url_for

from models import AcademicPeriod, Class, SchoolYear

from .assignment_create_spa_helpers import (
    CreateScope,
    _back_urls,
    _class_brief,
    _classes_payload,
    _spa_create_prefix,
)
from .utils import get_current_quarter


def _group_assignments_url(class_id: int, scope: CreateScope) -> str:
    if scope == "teacher":
        return f"/app/teacher/assignments-and-grades/{class_id}"
    return f"/app/management/assignments/{class_id}"


def _groups_api_url(class_id: int, scope: CreateScope) -> str:
    if scope == "teacher":
        return f"/api/spa/teacher/classes/{class_id}/groups"
    return url_for("management.classes.management_api_class_groups", class_id=class_id)


def query_group_class_picker(*, scope: CreateScope = "management") -> dict[str, Any]:
    urls = _back_urls(None, scope)
    return {
        "classes": _classes_payload(scope),
        "back_url": urls["back_url"],
        "type_selector_url": _spa_create_prefix(scope),
    }


def query_group_type_selector(class_id: int, *, scope: CreateScope = "management") -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    preselected = _class_brief(class_obj)
    prefix = _spa_create_prefix(scope)
    return {
        "class": preselected,
        "back_url": _group_assignments_url(class_id, scope),
        "class_picker_url": f"{prefix}/group",
        "type_selector_url": f"{prefix}/group/{class_id}",
        "links": {
            "pdf": f"{prefix}/group/{class_id}/pdf",
            "quiz": f"{prefix}/group/{class_id}/quiz",
            "discussion": f"{prefix}/group/{class_id}/discussion",
        },
    }


def query_group_discussion_form(class_id: int, *, scope: CreateScope = "management") -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    academic_periods: list[dict[str, Any]] = []
    if current_school_year:
        periods = AcademicPeriod.query.filter_by(
            school_year_id=current_school_year.id, is_active=True
        ).all()
        academic_periods = [
            {"id": p.id, "name": p.name, "period_type": getattr(p, "period_type", None)}
            for p in periods
        ]
    prefix = _spa_create_prefix(scope)

    return {
        "class": _class_brief(class_obj),
        "current_quarter": get_current_quarter(),
        "academic_periods": academic_periods,
        "groups_api_url": _groups_api_url(class_id, scope),
        "post_url": url_for(
            "management.classes.admin_create_group_discussion_assignment", class_id=class_id
        ),
        "back_url": f"{prefix}/group/{class_id}",
        "type_selector_url": f"{prefix}/group/{class_id}",
        "assignments_url": _group_assignments_url(class_id, scope),
        "defaults": {
            "min_posts": 2,
            "min_words": 100,
            "max_posts": 10,
            "group_size_min": 2,
        },
    }


def query_group_quiz_form(class_id: int, *, scope: CreateScope = "management") -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    academic_periods: list[dict[str, Any]] = []
    if current_school_year:
        periods = AcademicPeriod.query.filter_by(
            school_year_id=current_school_year.id, is_active=True
        ).all()
        academic_periods = [
            {"id": p.id, "name": p.name, "period_type": getattr(p, "period_type", None)}
            for p in periods
        ]
    prefix = _spa_create_prefix(scope)

    return {
        "class": _class_brief(class_obj),
        "current_quarter": get_current_quarter(),
        "academic_periods": academic_periods,
        "groups_api_url": _groups_api_url(class_id, scope),
        "post_url": url_for(
            "management.classes.admin_create_group_quiz_assignment", class_id=class_id
        ),
        "back_url": f"{prefix}/group/{class_id}",
        "type_selector_url": f"{prefix}/group/{class_id}",
        "assignments_url": _group_assignments_url(class_id, scope),
        "defaults": {
            "allow_save_and_continue": True,
            "time_limit_minutes": 30,
            "passing_score": 70,
            "group_size_min": 2,
        },
    }


def query_group_pdf_form(class_id: int, *, scope: CreateScope = "management") -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    academic_periods: list[dict[str, Any]] = []
    if current_school_year:
        periods = AcademicPeriod.query.filter_by(
            school_year_id=current_school_year.id, is_active=True
        ).all()
        academic_periods = [
            {"id": p.id, "name": p.name, "period_type": getattr(p, "period_type", None)}
            for p in periods
        ]
    prefix = _spa_create_prefix(scope)

    return {
        "class": _class_brief(class_obj),
        "accessible_classes": _classes_payload(scope),
        "current_quarter": get_current_quarter(),
        "academic_periods": academic_periods,
        "groups_api_url": _groups_api_url(class_id, scope),
        "post_url": url_for(
            "management.classes.admin_create_group_pdf_assignment", class_id=class_id
        ),
        "back_url": f"{prefix}/group/{class_id}",
        "type_selector_url": f"{prefix}/group/{class_id}",
        "assignments_url": _group_assignments_url(class_id, scope),
    }
