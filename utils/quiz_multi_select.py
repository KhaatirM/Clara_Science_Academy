"""Helpers for quiz multiple-select (select-all-that-apply) questions."""

from __future__ import annotations

import json
from typing import Any


def parse_selected_option_ids(raw: Any) -> list[int]:
    """Parse student multi-select answers from form/JSON/answer_text."""
    if raw is None or raw == "":
        return []
    if isinstance(raw, (list, tuple, set)):
        out: list[int] = []
        for item in raw:
            try:
                out.append(int(item))
            except (TypeError, ValueError):
                continue
        return sorted(set(out))
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return [int(raw)]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            return parse_selected_option_ids(parsed)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    out: list[int] = []
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except (TypeError, ValueError):
            continue
    return sorted(set(out))


def encode_selected_option_ids(option_ids: list[int]) -> str:
    return json.dumps(sorted({int(i) for i in option_ids}))


def grade_multiple_select(*, options, selected_ids: list[int], question_points: float) -> tuple[bool, float]:
    """Exact-match scoring: every correct option selected, no incorrect ones."""
    correct_ids = {int(o.id) for o in options if getattr(o, "is_correct", False)}
    selected = {int(i) for i in selected_ids}
    is_correct = bool(correct_ids) and selected == correct_ids
    points = float(question_points or 0) if is_correct else 0.0
    return is_correct, points


def correct_indices_from_form(form, question_id: str, *, multi: bool) -> set[str]:
    """Option indices marked correct when authoring a quiz question."""
    if multi:
        values = list(form.getlist(f"correct_answer_{question_id}[]"))
        if not values:
            raw = form.get(f"correct_answer_{question_id}", "") or ""
            values = [v.strip() for v in str(raw).split(",") if v.strip()]
        return {str(v).strip() for v in values if str(v).strip() != ""}
    raw = form.get(f"correct_answer_{question_id}", "")
    if raw is None or str(raw).strip() == "":
        return set()
    return {str(raw).strip()}


def add_choice_options_from_form(*, question, question_type: str, form, question_id: str) -> int:
    """Create QuizOption rows for multiple_choice or multiple_select. Returns count added."""
    from extensions import db
    from models import QuizOption

    option_values = form.getlist(f"option_text_{question_id}[]")
    multi = question_type == "multiple_select"
    correct = correct_indices_from_form(form, question_id, multi=multi)
    count = 0
    for option_text in option_values:
        option_text = (option_text or "").strip()
        if not option_text:
            continue
        db.session.add(
            QuizOption(
                question_id=question.id,
                option_text=option_text,
                is_correct=str(count) in correct,
                order=count,
            )
        )
        count += 1
    return count
