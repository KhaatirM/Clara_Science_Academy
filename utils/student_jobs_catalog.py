"""Inspection types, checklists and scoring for Student Jobs.

Each inspection type carries its own checklist and point values. The original
cleaning checklist is backed by dedicated columns on ``CleaningInspection``;
anything added later (Stairway, Lunch Hall) is stored in ``checklist_json`` so
new checklists never need another migration.
"""

from __future__ import annotations

import json
from typing import Any

CLEANING = "cleaning"
LUNCH_HALL = "lunch_hall"

_SEVERITY_BY_POINTS = {20: "major", 10: "major", 5: "moderate", 2: "minor"}


def _deduction(key: str, label: str, points: int) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "points": points,
        "severity": _SEVERITY_BY_POINTS.get(points, "minor"),
    }


def _bonus(key: str, label: str, points: int) -> dict[str, Any]:
    return {"key": key, "label": label, "points": points}


SHARED_BONUSES: list[dict[str, Any]] = [
    _bonus("exceptional_finish", "Exceptional finish", 5),
    _bonus("speed_efficiency", "Speed and efficiency", 5),
    _bonus("going_above_beyond", "Going above and beyond", 3),
    _bonus("teamwork_award", "Teamwork award", 2),
]

CLEANING_DEDUCTIONS: list[dict[str, Any]] = [
    _deduction("bathroom_not_restocked", "Bathroom not restocked", 10),
    _deduction("trash_can_left_full", "Trash can left full", 10),
    _deduction("floor_not_swept", "Floor not swept", 10),
    _deduction("materials_left_out", "Materials left out", 10),
    _deduction("stairway_not_cleaned", "Stairway not swept or cleaned", 10),
    _deduction("tables_missed", "Tables missed", 5),
    _deduction("classroom_trash_full", "Classroom trash full", 5),
    _deduction("bathroom_floor_poor", "Bathroom floor in poor condition", 5),
    _deduction("not_finished_on_time", "Not finished on time", 5),
    _deduction("small_debris_left", "Small debris left behind", 2),
    _deduction("trash_spilled", "Trash spilled", 2),
    _deduction("dispensers_half_filled", "Dispensers only half filled", 2),
]

LUNCH_HALL_DEDUCTIONS: list[dict[str, Any]] = [
    _deduction("lunch_tables_not_wiped", "Tables not wiped down or cleared", 20),
    _deduction("lunch_trash_on_floor", "Trash left on the floor", 20),
    _deduction("lunch_dishes_left", "Dishes left out", 20),
    _deduction("lunch_food_not_put_up", "Food and condiments not put up", 20),
    _deduction("lunch_trash_not_taken_out", "Trash not taken out", 20),
]

INSPECTION_TYPES: dict[str, dict[str, Any]] = {
    CLEANING: {
        "value": CLEANING,
        "label": "Cleaning",
        "description": "The standard classroom, hallway, restroom and stairway checklist.",
        "starting_score": 100,
        "pass_threshold": 60,
        "deductions": CLEANING_DEDUCTIONS,
        "bonuses": SHARED_BONUSES,
    },
    LUNCH_HALL: {
        "value": LUNCH_HALL,
        "label": "Lunch Hall",
        "description": "Scored on its own — every miss costs 20 points.",
        "starting_score": 100,
        "pass_threshold": 60,
        "deductions": LUNCH_HALL_DEDUCTIONS,
        "bonuses": SHARED_BONUSES,
    },
}

DEFAULT_INSPECTION_TYPE = CLEANING

# Checklist keys that predate ``checklist_json`` and still live in real columns.
COLUMN_BACKED_KEYS = frozenset(
    {
        "bathroom_not_restocked",
        "trash_can_left_full",
        "floor_not_swept",
        "materials_left_out",
        "tables_missed",
        "classroom_trash_full",
        "bathroom_floor_poor",
        "not_finished_on_time",
        "small_debris_left",
        "trash_spilled",
        "dispensers_half_filled",
        "exceptional_finish",
        "speed_efficiency",
        "going_above_beyond",
        "teamwork_award",
    }
)


def normalize_type(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in INSPECTION_TYPES else DEFAULT_INSPECTION_TYPE


def get_inspection_type(value: str | None) -> dict[str, Any]:
    return INSPECTION_TYPES[normalize_type(value)]


def inspection_type_options() -> list[dict[str, Any]]:
    return [
        {
            "value": definition["value"],
            "label": definition["label"],
            "description": definition["description"],
            "starting_score": definition["starting_score"],
            "pass_threshold": definition["pass_threshold"],
            "deductions": definition["deductions"],
            "bonuses": definition["bonuses"],
        }
        for definition in INSPECTION_TYPES.values()
    ]


def all_labels() -> dict[str, str]:
    """Every checklist key mapped to its label, across all inspection types."""
    labels: dict[str, str] = {}
    for definition in INSPECTION_TYPES.values():
        for item in list(definition["deductions"]) + list(definition["bonuses"]):
            labels[item["key"]] = item["label"]
    return labels


def _extra_flags(inspection) -> dict[str, Any]:
    raw = getattr(inspection, "checklist_json", None)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_flag(inspection, key: str) -> bool:
    """Whether a checklist item was marked, from its column or the JSON blob."""
    if key in COLUMN_BACKED_KEYS:
        return bool(getattr(inspection, key, False))
    return bool(_extra_flags(inspection).get(key))


def apply_flags(inspection, data: dict[str, Any], definition: dict[str, Any]) -> None:
    """Write the submitted checklist onto the inspection record."""
    extras: dict[str, bool] = {}
    for item in list(definition["deductions"]) + list(definition["bonuses"]):
        key = item["key"]
        checked = bool(data.get(key))
        if key in COLUMN_BACKED_KEYS:
            setattr(inspection, key, checked)
        elif checked:
            extras[key] = True
    inspection.checklist_json = json.dumps(extras) if extras else None


def score_inspection(definition: dict[str, Any], data: dict[str, Any]) -> dict[str, int]:
    """Authoritative score for a submitted checklist; the client only previews it."""
    major = moderate = minor = 0
    for item in definition["deductions"]:
        if not data.get(item["key"]):
            continue
        if item["severity"] == "major":
            major += item["points"]
        elif item["severity"] == "moderate":
            moderate += item["points"]
        else:
            minor += item["points"]

    bonus = sum(item["points"] for item in definition["bonuses"] if data.get(item["key"]))
    starting = int(definition["starting_score"])
    return {
        "starting_score": starting,
        "major_deductions": major,
        "moderate_deductions": moderate,
        "minor_deductions": minor,
        "bonus_points": bonus,
        "final_score": max(0, starting - major - moderate - minor + bonus),
    }
