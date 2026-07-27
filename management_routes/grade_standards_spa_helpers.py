"""Grade 1 & 3 standards checklist data for the management React SPA."""

from __future__ import annotations

from typing import Any

from flask import abort
from models import Class, Enrollment, SchoolYear, Student, db
from teacher_routes.utils import get_current_quarter

_LA_TOKENS = ("language arts", "language", "reading", "english", "ela", "literacy")
_MATH_TOKENS = ("math",)


def _load_grade_utils(grade_level: int):
    if grade_level == 1:
        import utils.report_card_grade1_standards as mod

        return mod
    if grade_level == 3:
        import utils.report_card_grade3_standards as mod

        return mod
    raise ValueError(f"Unsupported grade level: {grade_level}")


def _parse_grade_level(raw: str | int) -> int:
    if isinstance(raw, int):
        level = raw
    else:
        text = str(raw or "").strip().lower()
        if text.startswith("grade"):
            text = text[5:]
        if not text.isdigit():
            raise ValueError("Invalid grade level")
        level = int(text)
    if level not in (1, 3):
        raise ValueError("Invalid grade level")
    return level


def _is_grade_class(class_obj: Class, grade_level: int) -> bool:
    if not class_obj:
        return False
    try:
        levels = class_obj.get_grade_levels() or []
    except Exception:
        levels = []
    return grade_level in [int(level) for level in levels if str(level).isdigit() or isinstance(level, int)]


def _class_subject_key(class_obj: Class) -> str | None:
    if not class_obj or not class_obj.subject:
        return None
    subject = class_obj.subject.lower()
    if any(token in subject for token in _MATH_TOKENS):
        return "math"
    if any(token in subject for token in _LA_TOKENS):
        return "language_arts"
    return None


def _active_school_year() -> SchoolYear | None:
    return SchoolYear.query.filter_by(is_active=True).first()


def _normalize_quarter(raw: str | None, utils_mod) -> str:
    if raw:
        candidate = raw.strip().upper()
        if candidate in utils_mod.QUARTER_COLUMNS:
            return candidate
    try:
        num = get_current_quarter()
        if num and str(num).strip().isdigit():
            candidate = f"Q{int(num)}"
            if candidate in utils_mod.QUARTER_COLUMNS:
                return candidate
    except Exception:
        pass
    return "Q1"


def _all_eligible_classes(school_year_id: int, grade_level: int) -> list[Class]:
    candidates = Class.query.filter(
        Class.school_year_id == school_year_id,
        Class.is_active.is_(True),
    ).all()
    classes: list[Class] = []
    for class_obj in candidates:
        if not _is_grade_class(class_obj, grade_level):
            continue
        if not _class_subject_key(class_obj):
            continue
        classes.append(class_obj)
    classes.sort(key=lambda item: (item.subject or "", item.name or ""))
    return classes


def _class_roster(class_obj: Class) -> list[Student]:
    students = (
        db.session.query(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(
            Enrollment.class_id == class_obj.id,
            Enrollment.is_active.is_(True),
        )
        .distinct()
        .all()
    )
    students.sort(key=lambda student: ((student.last_name or "").lower(), (student.first_name or "").lower()))
    return students


def _serialize_student(student: Student) -> dict[str, Any]:
    return {
        "id": student.id,
        "first_name": student.first_name or "",
        "last_name": student.last_name or "",
        "display_name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
    }


def _serialize_class(
    class_obj: Class,
    subject_key: str,
    school_year_id: int,
    utils_mod,
    grade_level: int,
) -> dict[str, Any]:
    students = _class_roster(class_obj)
    stats = utils_mod.class_completeness([student.id for student in students], school_year_id, subject_key)
    return {
        "id": class_obj.id,
        "name": class_obj.name or "",
        "subject": class_obj.subject or "",
        "subject_key": subject_key,
        "student_count": len(students),
        "stats": stats,
        "editor_path": f"/management/report-cards/standards/grade{grade_level}/{class_obj.id}",
    }


def _format_last_updated(value) -> str | None:
    if not value:
        return None
    try:
        return value.strftime("%b %d, %I:%M %p")
    except Exception:
        return str(value)


def grade_standards_hub_path(grade_level: int | str) -> str:
    level = _parse_grade_level(grade_level)
    return f"/management/report-cards/standards/grade{level}"


def grade_standards_editor_path(grade_level: int | str, class_id: int) -> str:
    level = _parse_grade_level(grade_level)
    return f"/management/report-cards/standards/grade{level}/{class_id}"


def query_grade_standards_hub(grade_level: int | str) -> dict[str, Any]:
    level = _parse_grade_level(grade_level)
    utils_mod = _load_grade_utils(level)
    school_year = _active_school_year()
    if not school_year:
        return {
            "grade_level": level,
            "school_year": None,
            "current_quarter": _normalize_quarter(None, utils_mod),
            "quarter_columns": utils_mod.QUARTER_COLUMNS,
            "valid_marks": utils_mod.VALID_MARKS,
            "legend": [
                {"code": "M", "label": "Met academic standard"},
                {"code": "NA", "label": "Not assessed during this semester"},
                {"code": "W", "label": "Working towards meeting academic standard"},
                {"code": "UA", "label": "Unable to assess during this semester"},
            ],
            "groups": {"language_arts": [], "math": []},
            "summary": {
                "total_classes": 0,
                "total_students": 0,
                "overall_percent": 0,
                "overall_filled": 0,
                "overall_total": 0,
            },
            "urls": {
                "hub": grade_standards_hub_path(level),
                "report_cards": "/management/report-cards",
            },
            "error": "No active school year is configured.",
        }

    classes = _all_eligible_classes(school_year.id, level)
    grouped: dict[str, list[dict[str, Any]]] = {"language_arts": [], "math": []}
    for class_obj in classes:
        subject_key = _class_subject_key(class_obj)
        if subject_key in grouped:
            grouped[subject_key].append(
                _serialize_class(class_obj, subject_key, school_year.id, utils_mod, level)
            )

    total_classes = len(classes)
    total_students = sum(item["student_count"] for item in grouped["language_arts"] + grouped["math"])
    overall_filled = sum(
        item["stats"]["overall"]["filled"] for item in grouped["language_arts"] + grouped["math"]
    )
    overall_total = sum(
        item["stats"]["overall"]["total"] for item in grouped["language_arts"] + grouped["math"]
    )
    overall_percent = int(round(100 * overall_filled / overall_total)) if overall_total else 0

    title = "1st Grade Standards Checklist" if level == 1 else "3rd Grade Standards Checklist"
    return {
        "grade_level": level,
        "title": title,
        "school_year": {"id": school_year.id, "name": school_year.name},
        "current_quarter": _normalize_quarter(None, utils_mod),
        "quarter_columns": utils_mod.QUARTER_COLUMNS,
        "valid_marks": utils_mod.VALID_MARKS,
        "legend": [
            {"code": "M", "label": "Met academic standard"},
            {"code": "NA", "label": "Not assessed during this semester"},
            {"code": "W", "label": "Working towards meeting academic standard"},
            {"code": "UA", "label": "Unable to assess during this semester"},
        ],
        "groups": grouped,
        "summary": {
            "total_classes": total_classes,
            "total_students": total_students,
            "overall_percent": overall_percent,
            "overall_filled": overall_filled,
            "overall_total": overall_total,
        },
        "urls": {
            "hub": grade_standards_hub_path(level),
            "report_cards": "/management/report-cards",
        },
    }


def query_grade_standards_editor(
    grade_level: int | str,
    class_id: int,
    *,
    quarter: str | None = None,
    view: str = "grid",
    student_id: int | None = None,
) -> dict[str, Any]:
    level = _parse_grade_level(grade_level)
    utils_mod = _load_grade_utils(level)
    class_obj = Class.query.get_or_404(class_id)

    if not _is_grade_class(class_obj, level):
        abort(400, description=f"This is not a {level}{'st' if level == 1 else 'rd'} grade class.")

    subject_key = _class_subject_key(class_obj)
    if not subject_key:
        abort(
            400,
            description="This class subject is not Language Arts or Math, so it cannot use the standards checklist.",
        )

    school_year = class_obj.school_year or _active_school_year()
    if not school_year:
        abort(400, description="No active school year is configured.")

    quarter = _normalize_quarter(quarter, utils_mod)
    view_mode = (view or "grid").strip().lower()
    if view_mode not in ("grid", "student"):
        view_mode = "grid"

    students = _class_roster(class_obj)
    student_ids = [student.id for student in students]
    standards = utils_mod.flat_standards(subject_key)
    marks_by_student = utils_mod.get_marks_for_students(
        student_ids,
        school_year.id,
        subject_key=subject_key,
    )

    marks_grid: dict[int, dict[str, str]] = {}
    for sid in student_ids:
        per_std = marks_by_student.get(sid, {})
        marks_grid[sid] = {
            std["id"]: (per_std.get(std["id"]) or {}).get(quarter, "") for std in standards
        }

    marks_student_view: dict[int, dict[str, dict[str, str]]] = {}
    for sid in student_ids:
        per_std = marks_by_student.get(sid, {})
        marks_student_view[sid] = {
            std["id"]: {q: (per_std.get(std["id"]) or {}).get(q, "") for q in utils_mod.QUARTER_COLUMNS}
            for std in standards
        }

    if view_mode == "student":
        if student_id not in student_ids:
            student_id = student_ids[0] if student_ids else None
    else:
        student_id = None

    overall_stats = utils_mod.class_completeness(student_ids, school_year.id, subject_key)
    section_stats = utils_mod.section_completeness(student_ids, school_year.id, subject_key, quarter)
    other_classes = [
        _serialize_class(item, _class_subject_key(item) or subject_key, school_year.id, utils_mod, level)
        for item in _all_eligible_classes(school_year.id, level)
    ]

    return {
        "grade_level": level,
        "class": {
            "id": class_obj.id,
            "name": class_obj.name or "",
            "subject": class_obj.subject or "",
            "subject_key": subject_key,
        },
        "subject_catalog": utils_mod.SUBJECT_CATALOGS[subject_key],
        "school_year": {"id": school_year.id, "name": school_year.name},
        "students": [_serialize_student(student) for student in students],
        "standards": standards,
        "quarter": quarter,
        "quarter_columns": utils_mod.QUARTER_COLUMNS,
        "valid_marks": utils_mod.VALID_MARKS,
        "view_mode": view_mode,
        "selected_student_id": student_id,
        "marks_grid": marks_grid,
        "marks_student_view": marks_student_view,
        "overall_stats": {
            **overall_stats,
            "last_updated_display": _format_last_updated(overall_stats.get("last_updated")),
        },
        "section_stats": section_stats,
        "other_classes": other_classes,
        "can_copy_previous": quarter != "Q1",
        "urls": {
            "hub": grade_standards_hub_path(level),
            "report_cards": "/management/report-cards",
        },
    }


def apply_grade_standards_changes(
    grade_level: int | str,
    class_id: int,
    payload: dict[str, Any],
    user_id: int | None,
) -> dict[str, Any]:
    level = _parse_grade_level(grade_level)
    utils_mod = _load_grade_utils(level)
    class_obj = Class.query.get_or_404(class_id)

    if not _is_grade_class(class_obj, level):
        abort(400, description=f"This is not a {level}{'st' if level == 1 else 'rd'} grade class.")

    subject_key = _class_subject_key(class_obj)
    if not subject_key:
        abort(400, description="This class cannot use the standards checklist.")

    school_year = class_obj.school_year or _active_school_year()
    if not school_year:
        abort(400, description="No active school year is configured.")

    quarter = _normalize_quarter(payload.get("quarter"), utils_mod)
    students = _class_roster(class_obj)
    student_ids = [student.id for student in students]
    standards = utils_mod.flat_standards(subject_key)
    standard_id_set = {std["id"] for std in standards}
    student_id_set = set(student_ids)

    bulk_action = (payload.get("bulk_action") or "").strip()
    changed = 0

    if bulk_action == "copy_previous":
        copied = utils_mod.copy_marks_from_previous_quarter(
            student_ids,
            school_year.id,
            subject_key,
            quarter,
            user_id=user_id,
        )
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            abort(500, description="Could not copy marks from the previous quarter.")
        return {
            "success": True,
            "changed": copied,
            "message": (
                f"Copied {copied} mark(s) from the previous quarter into {quarter}."
                if copied
                else "No new marks were copied (target cells were already filled or empty in previous quarter)."
            ),
        }

    if bulk_action in ("mark_all_m", "mark_all_w", "mark_all_na", "mark_all_ua"):
        mark_value = bulk_action.split("_")[-1].upper()
        for sid in student_ids:
            for std in standards:
                if utils_mod.upsert_mark(
                    sid, std["id"], school_year.id, quarter, mark_value, user_id=user_id
                ):
                    changed += 1
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            abort(500, description="Could not apply the bulk mark.")
        return {
            "success": True,
            "changed": changed,
            "message": f"Set {changed} cell(s) to {mark_value} for {quarter}.",
        }

    if bulk_action == "clear_all":
        for sid in student_ids:
            for std in standards:
                if utils_mod.upsert_mark(sid, std["id"], school_year.id, quarter, "", user_id=user_id):
                    changed += 1
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            abort(500, description="Could not clear marks.")
        return {
            "success": True,
            "changed": changed,
            "message": f"Cleared {changed} mark(s) for {quarter}.",
        }

    marks = payload.get("marks") or []
    if not isinstance(marks, list):
        abort(400, description="Invalid marks payload.")

    for item in marks:
        if not isinstance(item, dict):
            continue
        try:
            sid = int(item.get("student_id"))
        except (TypeError, ValueError):
            continue
        std_id = str(item.get("standard_id") or "")
        if sid not in student_id_set or std_id not in standard_id_set:
            continue
        target_q = (item.get("quarter") or quarter).strip().upper()
        if target_q not in utils_mod.QUARTER_COLUMNS:
            continue
        mark_value = (item.get("value") or "").strip().upper()
        if mark_value and mark_value not in utils_mod.VALID_MARKS:
            continue
        if utils_mod.upsert_mark(sid, std_id, school_year.id, target_q, mark_value, user_id=user_id):
            changed += 1

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        abort(500, description="Could not save standards marks. Please try again.")

    return {
        "success": True,
        "changed": changed,
        "message": f"Saved {changed} change(s)." if changed else "No changes to save.",
    }
