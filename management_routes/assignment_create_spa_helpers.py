"""SPA helpers for assignment creation (type selector + create forms)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, Literal

from flask import url_for

from models import Class

from .utils import get_current_quarter

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

CreateScope = Literal["management", "teacher"]


def _class_brief(class_obj: Class | None) -> dict[str, Any] | None:
    if not class_obj:
        return None
    return {
        "id": class_obj.id,
        "name": class_obj.name,
        "subject": getattr(class_obj, "subject", None),
    }


def _classes_payload(scope: CreateScope = "management") -> list[dict[str, Any]]:
    if scope == "teacher":
        from teacher_routes.classes_spa_helpers import _teacher_accessible_classes
        from teacher_routes.utils import get_teacher_or_admin

        classes = _teacher_accessible_classes(get_teacher_or_admin())
        return [
            {"id": c.id, "name": c.name, "subject": getattr(c, "subject", None)}
            for c in classes
            if getattr(c, "is_active", True)
        ]

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


def _spa_create_prefix(scope: CreateScope = "management") -> str:
    if scope == "teacher":
        return "/app/teacher/assignments/create"
    return "/app/management/assignments/create"


def _back_urls(class_id: int | None, scope: CreateScope = "management") -> dict[str, str]:
    type_selector = _spa_create_prefix(scope)
    if scope == "teacher":
        if class_id:
            return {
                "back_url": f"/app/teacher/assignments-and-grades/{class_id}",
                "type_selector_url": f"{type_selector}?class_id={class_id}",
            }
        return {
            "back_url": "/app/teacher/assignments-and-grades",
            "type_selector_url": type_selector,
        }

    if class_id:
        return {
            "back_url": f"/app/management/assignments/{class_id}",
            "type_selector_url": f"{type_selector}?class_id={class_id}",
        }
    return {
        "back_url": "/app/management/assignments",
        "type_selector_url": type_selector,
    }


def _spa_pdf_url(context: str, class_id: int | None, scope: CreateScope = "management") -> str:
    params = [f"context={context}"]
    if class_id:
        params.append(f"class_id={class_id}")
    return f"{_spa_create_prefix(scope)}/pdf?{'&'.join(params)}"


def _pdf_post_url(class_id: int | None, scope: CreateScope) -> str:
    if scope == "teacher":
        if class_id:
            return url_for("teacher.assignments.add_assignment_for_class", class_id=class_id)
        return url_for("teacher.assignments.add_assignment")
    return url_for("management.add_assignment")


def query_create_assignment_meta(
    class_id: int | None = None,
    *,
    scope: CreateScope = "management",
) -> dict[str, Any]:
    """Links and context for the React assignment type selector."""
    class_obj = Class.query.get(class_id) if class_id else None
    preselected = _class_brief(class_obj)
    urls = _back_urls(class_id, scope)

    discussion_qs = f"?class_id={class_id}" if class_id else ""
    quiz_qs = f"?class_id={class_id}" if class_id else ""

    prefix = _spa_create_prefix(scope)
    if class_id:
        group_url = f"{prefix}/group/{class_id}"
    else:
        group_url = f"{prefix}/group"

    return {
        "preselected_class": preselected,
        "back_url": urls["back_url"],
        "links": {
            "pdf_in_class": _spa_pdf_url("in-class", class_id, scope),
            "pdf_homework": _spa_pdf_url("homework", class_id, scope),
            "quiz": f"{prefix}/quiz{quiz_qs}",
            "discussion": f"{prefix}/discussion{discussion_qs}",
            "group": group_url,
        },
    }


def query_pdf_assignment_form(
    context: str = "homework",
    class_id: int | None = None,
    *,
    scope: CreateScope = "management",
) -> dict[str, Any]:
    class_obj = Class.query.get(class_id) if class_id else None
    in_class_due = _in_class_due_datetime()
    default_due = in_class_due if context == "in-class" else None
    urls = _back_urls(class_id, scope)

    return {
        "context": context if context in ("homework", "in-class") else "homework",
        "current_quarter": get_current_quarter(),
        "classes": _classes_payload(scope),
        "preselected_class": _class_brief(class_obj),
        "default_due_date": default_due,
        "in_class_due_date": in_class_due,
        "post_url": _pdf_post_url(class_id, scope),
        **urls,
    }


def query_discussion_assignment_form(
    class_id: int | None = None,
    *,
    scope: CreateScope = "management",
    edit_id: int | None = None,
) -> dict[str, Any]:
    from models import Assignment
    from teacher_routes.assignment_utils import parse_discussion_description

    assignment = None
    if edit_id:
        assignment = Assignment.query.get(edit_id)
        if not assignment or assignment.assignment_type != "discussion":
            raise ValueError("Discussion assignment not found")
        class_id = class_id or assignment.class_id

    class_obj = Class.query.get(class_id) if class_id else None
    urls = _back_urls(class_id, scope)

    if scope == "teacher":
        post_url = url_for("teacher.create_discussion_assignment")
        if edit_id:
            post_url = f"{post_url}?edit={edit_id}"
    else:
        post_url = url_for("management.create_discussion_assignment")
        if edit_id:
            post_url = f"{post_url}?edit={edit_id}"

    defaults = {
        "min_initial_posts": 1,
        "min_replies": 2,
        "total_points": 100,
    }
    edit: dict[str, Any] | None = None
    if assignment:
        prompt, instructions, rubric, min_initial_posts, min_replies = parse_discussion_description(
            assignment.description or ""
        )
        defaults = {
            "min_initial_posts": min_initial_posts or 1,
            "min_replies": min_replies or 2,
            "total_points": int(assignment.total_points or 100),
        }
        edit = {
            "id": assignment.id,
            "title": assignment.title or "",
            "class_id": assignment.class_id,
            "discussion_prompt": prompt or "",
            "description": instructions or "",
            "min_initial_posts": min_initial_posts or 1,
            "min_replies": min_replies or 2,
            "require_peer_response": bool(getattr(assignment, "require_peer_response", True)),
            "allow_student_threads": bool(getattr(assignment, "allow_student_threads", True)),
            "allow_student_edit_posts": bool(getattr(assignment, "allow_student_edit_posts", False)),
            "total_points": float(assignment.total_points or 100),
            "quarter": str(assignment.quarter or get_current_quarter()),
            "assignment_context": getattr(assignment, "assignment_context", None) or "homework",
            "due_date": _dt_local(assignment.due_date),
            "open_date": _dt_local(getattr(assignment, "open_date", None)),
            "close_date": _dt_local(getattr(assignment, "close_date", None)),
            "use_rubric": bool(rubric),
            "rubric_criteria": rubric or "",
        }

    return {
        "current_quarter": get_current_quarter(),
        "classes": _classes_payload(scope),
        "preselected_class": _class_brief(class_obj),
        "post_url": post_url,
        "defaults": defaults,
        "edit": edit,
        **urls,
    }


def query_quiz_assignment_form(
    class_id: int | None = None,
    *,
    scope: CreateScope = "management",
    edit_id: int | None = None,
) -> dict[str, Any]:
    from management_routes.assignments import _build_quiz_data_for_edit
    from models import Assignment

    assignment = None
    if edit_id:
        assignment = Assignment.query.get(edit_id)
        if not assignment or assignment.assignment_type != "quiz":
            raise ValueError("Quiz assignment not found")
        class_id = class_id or assignment.class_id

    class_obj = Class.query.get(class_id) if class_id else None
    urls = _back_urls(class_id, scope)

    if scope == "teacher":
        post_url = url_for("teacher.create_quiz_assignment")
        question_banks_url = url_for("teacher.quizzes.question_banks_json")
        save_to_bank_url = url_for("teacher.quizzes.save_to_bank")
    else:
        post_url = url_for("management.create_quiz_assignment")
        question_banks_url = url_for("management.assignments.question_banks_json")
        save_to_bank_url = url_for("management.assignments.save_to_bank")

    edit: dict[str, Any] | None = None
    if assignment:
        quiz_data = _build_quiz_data_for_edit(assignment)
        edit = {
            "id": assignment.id,
            "title": assignment.title or "",
            "class_id": assignment.class_id,
            "description": assignment.description or "",
            "due_date": _dt_local(assignment.due_date),
            "quarter": str(assignment.quarter or get_current_quarter()),
            "assignment_context": getattr(assignment, "assignment_context", None) or "homework",
            "assignment_category": getattr(assignment, "assignment_category", None) or "Quizzes",
            "category_weight": float(getattr(assignment, "category_weight", 0) or 0),
            "allow_extra_credit": bool(getattr(assignment, "allow_extra_credit", False)),
            "max_extra_credit_points": float(getattr(assignment, "max_extra_credit_points", 0) or 0),
            "open_date": _dt_local(getattr(assignment, "open_date", None)),
            "close_date": _dt_local(getattr(assignment, "close_date", None)),
            "time_limit": (
                str(int(assignment.time_limit_minutes))
                if getattr(assignment, "time_limit_minutes", None)
                else ""
            ),
            "attempts": str(int(getattr(assignment, "max_attempts", None) or 1)),
            "shuffle_questions": bool(getattr(assignment, "shuffle_questions", False)),
            "show_correct_answers": bool(getattr(assignment, "show_correct_answers", True)),
            "link_google_form": bool(getattr(assignment, "google_form_linked", False)),
            "google_form_url": getattr(assignment, "google_form_url", None) or "",
            "allow_save_and_continue": bool(getattr(assignment, "allow_save_and_continue", True)),
            "max_save_attempts": str(int(getattr(assignment, "max_save_attempts", None) or 10)),
            "save_timeout_minutes": str(int(getattr(assignment, "save_timeout_minutes", None) or 30)),
            "blocks": quiz_data.get("blocks") or [],
            "is_draft": bool(getattr(assignment, "quiz_authoring_is_draft", False)),
        }

    return {
        "current_quarter": get_current_quarter(),
        "classes": _classes_payload(scope),
        "preselected_class": _class_brief(class_obj),
        "post_url": post_url,
        "question_banks_url": question_banks_url,
        "save_to_bank_url": save_to_bank_url,
        "question_types": [
            {"value": "multiple_choice", "label": "Multiple choice"},
            {"value": "true_false", "label": "True / false"},
            {"value": "short_answer", "label": "Short answer"},
            {"value": "essay", "label": "Long essay"},
        ],
        "edit": edit,
        **urls,
    }


def _dt_local(value: Any) -> str:
    if not value:
        return ""
    try:
        return value.strftime("%Y-%m-%dT%H:%M")
    except Exception:
        return ""

