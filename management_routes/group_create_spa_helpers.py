"""SPA helpers for group assignment creation."""

from __future__ import annotations

from typing import Any

from flask import url_for

from models import AcademicPeriod, Class, SchoolYear

from .assignment_create_spa_helpers import _back_urls, _class_brief, _classes_payload
from .utils import get_current_quarter


def query_group_class_picker() -> dict[str, Any]:
    urls = _back_urls(None)
    return {
        "classes": _classes_payload(),
        "back_url": urls["back_url"],
        "type_selector_url": "/app/management/assignments/create",
    }


def query_group_type_selector(class_id: int) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    preselected = _class_brief(class_obj)
    return {
        "class": preselected,
        "back_url": f"/app/management/assignments/{class_id}",
        "class_picker_url": "/app/management/assignments/create/group",
        "type_selector_url": f"/app/management/assignments/create/group/{class_id}",
        "links": {
            "pdf": f"/app/management/assignments/create/group/{class_id}/pdf",
            "quiz": f"/app/management/assignments/create/group/{class_id}/quiz",
            "discussion": None,
        },
    }


def query_group_quiz_form(class_id: int) -> dict[str, Any]:
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

    return {
        "class": _class_brief(class_obj),
        "current_quarter": get_current_quarter(),
        "academic_periods": academic_periods,
        "groups_api_url": url_for("management.classes.management_api_class_groups", class_id=class_id),
        "post_url": url_for(
            "management.classes.admin_create_group_quiz_assignment", class_id=class_id
        ),
        "back_url": f"/app/management/assignments/create/group/{class_id}",
        "type_selector_url": f"/app/management/assignments/create/group/{class_id}",
        "assignments_url": f"/app/management/assignments/{class_id}",
        "defaults": {
            "allow_save_and_continue": True,
            "time_limit_minutes": 30,
            "passing_score": 70,
            "group_size_min": 2,
        },
    }


def query_group_pdf_form(class_id: int) -> dict[str, Any]:
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

    return {
        "class": _class_brief(class_obj),
        "accessible_classes": _classes_payload(),
        "current_quarter": get_current_quarter(),
        "academic_periods": academic_periods,
        "groups_api_url": url_for("management.classes.management_api_class_groups", class_id=class_id),
        "post_url": url_for(
            "management.classes.admin_create_group_pdf_assignment", class_id=class_id
        ),
        "back_url": f"/app/management/assignments/create/group/{class_id}",
        "type_selector_url": f"/app/management/assignments/create/group/{class_id}",
        "assignments_url": f"/app/management/assignments/{class_id}",
    }
