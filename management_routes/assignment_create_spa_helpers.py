"""SPA helpers for assignment creation (type selector + create forms)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from flask import url_for

from models import Class

from .utils import get_current_quarter

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


def _class_brief(class_obj: Class | None) -> dict[str, Any] | None:
    if not class_obj:
        return None
    return {
        "id": class_obj.id,
        "name": class_obj.name,
        "subject": getattr(class_obj, "subject", None),
    }


def _classes_payload() -> list[dict[str, Any]]:
    classes = Class.query.filter_by(is_active=True).order_by(Class.name).all()
    return [{"id": c.id, "name": c.name, "subject": getattr(c, "subject", None)} for c in classes]


def _in_class_due_datetime() -> str:
    try:
        est = ZoneInfo("America/New_York")
        now_est = datetime.now(est)
        in_class_dt = datetime.combine(now_est.date(), time(16, 0))
    except Exception:
        in_class_dt = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
    return in_class_dt.strftime("%Y-%m-%dT%H:%M")


def _back_urls(class_id: int | None) -> dict[str, str]:
    type_selector = "/app/management/assignments/create"
    if class_id:
        return {
            "back_url": f"/app/management/assignments/{class_id}",
            "type_selector_url": f"{type_selector}?class_id={class_id}",
        }
    return {
        "back_url": "/app/management/assignments",
        "type_selector_url": type_selector,
    }


def _spa_pdf_url(context: str, class_id: int | None) -> str:
    params = [f"context={context}"]
    if class_id:
        params.append(f"class_id={class_id}")
    return f"/app/management/assignments/create/pdf?{'&'.join(params)}"


def query_create_assignment_meta(class_id: int | None = None) -> dict[str, Any]:
    """Links and context for the React assignment type selector."""
    class_obj = Class.query.get(class_id) if class_id else None
    preselected = _class_brief(class_obj)
    urls = _back_urls(class_id)

    discussion_qs = f"?class_id={class_id}" if class_id else ""
    quiz_qs = f"?class_id={class_id}" if class_id else ""

    if class_id:
        group_url = f"/app/management/assignments/create/group/{class_id}"
    else:
        group_url = "/app/management/assignments/create/group"

    return {
        "preselected_class": preselected,
        "back_url": urls["back_url"],
        "links": {
            "pdf_in_class": _spa_pdf_url("in-class", class_id),
            "pdf_homework": _spa_pdf_url("homework", class_id),
            "quiz": f"/app/management/assignments/create/quiz{quiz_qs}",
            "discussion": f"/app/management/assignments/create/discussion{discussion_qs}",
            "group": group_url,
        },
    }


def query_pdf_assignment_form(context: str = "homework", class_id: int | None = None) -> dict[str, Any]:
    class_obj = Class.query.get(class_id) if class_id else None
    in_class_due = _in_class_due_datetime()
    default_due = in_class_due if context == "in-class" else None
    urls = _back_urls(class_id)

    return {
        "context": context if context in ("homework", "in-class") else "homework",
        "current_quarter": get_current_quarter(),
        "classes": _classes_payload(),
        "preselected_class": _class_brief(class_obj),
        "default_due_date": default_due,
        "in_class_due_date": in_class_due,
        "post_url": url_for("management.add_assignment"),
        **urls,
    }


def query_discussion_assignment_form(class_id: int | None = None) -> dict[str, Any]:
    class_obj = Class.query.get(class_id) if class_id else None
    urls = _back_urls(class_id)

    return {
        "current_quarter": get_current_quarter(),
        "classes": _classes_payload(),
        "preselected_class": _class_brief(class_obj),
        "post_url": url_for("management.create_discussion_assignment"),
        "defaults": {
            "min_initial_posts": 1,
            "min_replies": 2,
            "total_points": 100,
        },
        **urls,
    }


def query_quiz_assignment_form(class_id: int | None = None) -> dict[str, Any]:
    class_obj = Class.query.get(class_id) if class_id else None
    urls = _back_urls(class_id)

    return {
        "current_quarter": get_current_quarter(),
        "classes": _classes_payload(),
        "preselected_class": _class_brief(class_obj),
        "post_url": url_for("management.create_quiz_assignment"),
        "question_types": [
            {"value": "multiple_choice", "label": "Multiple choice"},
            {"value": "true_false", "label": "True / false"},
            {"value": "short_answer", "label": "Short answer"},
        ],
        **urls,
    }
