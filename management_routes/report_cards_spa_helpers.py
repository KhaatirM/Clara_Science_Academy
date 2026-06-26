"""Report cards hub payloads for the React management SPA."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc, nullslast, or_
from sqlalchemy.orm import selectinload

from extensions import db
from models import Class, Enrollment, ReportCard, ReportCardComment, SchoolYear, Student
from management_routes.reports import (
    REPORT_CARD_CATEGORIES,
    _build_entrance_school_year_options,
    _enrollment_eligible_for_report_card,
    _resolve_report_card_category,
    _sanitize_letter_grades_for_report,
    _selected_quarters_date_window,
    _sort_report_cards_newest_first,
    persist_report_card_record,
)
from management_routes.students import _calculate_expected_grad_date
from utils.report_card_portal import (
    count_pending_parent_approval,
    is_official_report_card,
)
from utils.report_card_warnings import (
    report_card_unfinalized_banner_message,
    report_card_warnings_template_context,
)
from utils.report_card_school_year import (
    enrollment_must_be_active_for_report_card,
    grade_display as rc_grade_display,
    grade_from_report_card_snapshot,
    grade_level_for_school_year,
)


def _grade_display(grade_level) -> str:
    if grade_level == 0:
        return "K"
    if grade_level is not None:
        return str(grade_level)
    return "N/A"


STANDARDS_CHECKLIST_LEGEND = [
    {"code": "M", "label": "Met academic standard"},
    {"code": "NA", "label": "Not assessed during this semester"},
    {"code": "W", "label": "Working towards meeting academic standard"},
    {"code": "UA", "label": "Unable to assess during this semester"},
]


def _standards_checklist_urls() -> dict[str, str]:
    from flask import current_app, url_for

    from management_routes.grade_standards_spa_helpers import (
        grade_standards_hub_path,
    )
    from utils.spa_management_urls import user_should_use_spa_management_shell

    urls: dict[str, str] = {}
    try:
        if user_should_use_spa_management_shell():
            urls["grade1_standards"] = grade_standards_hub_path(1)
            urls["grade3_standards"] = grade_standards_hub_path(3)
            return urls
        view_functions = current_app.view_functions
        if "teacher.grade1_standards.grade1_standards_index" in view_functions:
            urls["grade1_standards"] = url_for("teacher.grade1_standards.grade1_standards_index")
        if "teacher.grade3_standards.grade3_standards_index" in view_functions:
            urls["grade3_standards"] = url_for("teacher.grade3_standards.grade3_standards_index")
    except RuntimeError:
        pass
    return urls


def _standards_checklist_info(grade_level: int | None) -> dict[str, Any] | None:
    """Describe K–3 standards checklist behavior for SPA generate/detail views."""
    if grade_level is None:
        return None

    urls = _standards_checklist_urls()
    base = {
        "legend": STANDARDS_CHECKLIST_LEGEND,
        "pdf_pages": [],
    }

    if grade_level == 1:
        return {
            **base,
            "variant": "grade1",
            "title": "1st grade standards checklist",
            "description": (
                "Official 1st grade report cards include a multi-page PDF with Language Arts and "
                "Math standards checklists (pages 2–3). Marks are filled by teachers before generation."
            ),
            "editor_url": urls.get("grade1_standards"),
            "pdf_pages": ["Summary & course progress", "Language Arts checklist", "Math checklist", "Assignments & comments"],
        }

    if grade_level == 3:
        return {
            **base,
            "variant": "grade3",
            "title": "3rd grade standards checklist",
            "description": (
                "Official 3rd grade report cards include a multi-page PDF with Language Arts and "
                "Math standards checklists (pages 2–3). Marks are filled by teachers before generation."
            ),
            "editor_url": urls.get("grade3_standards"),
            "pdf_pages": ["Summary & course progress", "Language Arts checklist", "Math checklist", "Assignments & comments"],
        }

    if grade_level in (0, 2):
        label = "Kindergarten" if grade_level == 0 else "2nd grade"
        return {
            **base,
            "variant": "k2",
            "title": f"{label} progress report",
            "description": (
                f"{label} report cards use the K–2 progress report layout with a standards checklist "
                "section on the PDF. Full data-driven checklist editors are available for 1st and 3rd grade."
            ),
            "editor_url": None,
            "pdf_pages": ["Attendance, course progress, standards checklist, comments"],
        }

    return None


def _standards_marks_summary(student_id: int, school_year_id: int, grade_level: int) -> dict[str, Any] | None:
    """Lightweight completion counts for generate wizard preview."""
    if grade_level == 1:
        from utils.report_card_grade1_standards import (
            GRADE1_LANGUAGE_ARTS,
            GRADE1_MATH,
            get_marks_for_student,
            subject_for_standard,
        )

        marks = get_marks_for_student(student_id, school_year_id)
        la_catalog, math_catalog = GRADE1_LANGUAGE_ARTS, GRADE1_MATH
    elif grade_level == 3:
        from utils.report_card_grade3_standards import (
            GRADE3_LANGUAGE_ARTS,
            GRADE3_MATH,
            get_marks_for_student,
            subject_for_standard,
        )

        marks = get_marks_for_student(student_id, school_year_id)
        la_catalog, math_catalog = GRADE3_LANGUAGE_ARTS, GRADE3_MATH
    else:
        return None

    def _catalog_ids(catalog, subject_key):
        return [
            std["id"]
            for section in catalog.get("sections", [])
            for std in section.get("standards", [])
            if std.get("id")
        ]

    la_ids = set(_catalog_ids(la_catalog, "language_arts"))
    math_ids = set(_catalog_ids(math_catalog, "math"))

    la_marked = sum(
        1
        for std_id, per_q in marks.items()
        if std_id in la_ids and any((v or "").strip() for v in per_q.values())
    )
    math_marked = sum(
        1
        for std_id, per_q in marks.items()
        if std_id in math_ids and any((v or "").strip() for v in per_q.values())
    )

    return {
        "language_arts": {"marked": la_marked, "total": len(la_ids)},
        "math": {"marked": math_marked, "total": len(math_ids)},
    }


def _report_type_from_details(grades_details: str | None) -> str:
    if not grades_details:
        return "official"
    try:
        data = json.loads(grades_details)
        return data.get("report_type", "official") or "official"
    except (json.JSONDecodeError, TypeError):
        return "official"


def _format_generated_at(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.strftime("%b %d, %Y · %I:%M %p")


def _format_generated_at_long(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.strftime("%B %d, %Y at %I:%M %p")


def _spa_report_card_urls(report_card_id: int, student_id: int | None) -> dict[str, str | None]:
    return {
        "view": f"/management/report-cards/{report_card_id}",
        "pdf": f"/api/spa/report-cards/{report_card_id}/pdf",
        "history": f"/management/report-cards/student/{student_id}" if student_id else None,
    }


def _parse_report_card_snapshot(report_card: ReportCard) -> dict[str, Any]:
    report_card_data = json.loads(report_card.grades_details) if report_card.grades_details else {}
    student_display = {}
    if isinstance(report_card_data, dict):
        student_display = report_card_data.get("student_display") or {}
    if isinstance(report_card_data, dict) and "grades" in report_card_data:
        return {
            "grades": report_card_data.get("grades", {}),
            "grades_by_quarter": report_card_data.get("grades_by_quarter"),
            "attendance": report_card_data.get("attendance", {}),
            "selected_class_ids": report_card_data.get("classes", []),
            "include_attendance": bool(report_card_data.get("include_attendance", False)),
            "include_comments": bool(report_card_data.get("include_comments", False)),
            "comments_by_class": report_card_data.get("comments_by_class", {}) or {},
            "additional_comments": report_card_data.get("additional_comments", "") or "",
            "report_type": report_card_data.get("report_type", "official") or "official",
            "student_display": student_display,
        }
    return {
        "grades": report_card_data if report_card_data else {},
        "grades_by_quarter": None,
        "attendance": {},
        "selected_class_ids": [],
        "include_attendance": False,
        "include_comments": False,
        "comments_by_class": {},
        "additional_comments": "",
        "report_type": "official",
        "student_display": student_display,
    }


def _grade_for_report_card(rc: ReportCard, student: Student | None, school_year: SchoolYear | None) -> tuple[int | None, str]:
    snapshot_grade = grade_from_report_card_snapshot(rc.grades_details)
    if snapshot_grade is not None:
        return snapshot_grade, rc_grade_display(snapshot_grade)
    if student and school_year:
        derived = grade_level_for_school_year(student, school_year)
        if derived is not None:
            return derived, rc_grade_display(derived)
    if student:
        return student.grade_level, _grade_display(student.grade_level)
    return None, "N/A"


def _grade_rows_from_snapshot(grades: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sanitized = _sanitize_letter_grades_for_report(grades or {})
    for subject, grade_info in sanitized.items():
        if isinstance(grade_info, dict):
            percentage = float(grade_info.get("percentage", grade_info.get("average", 0)) or 0)
            letter_grade = grade_info.get("letter", grade_info.get("grade", "N/A"))
        else:
            try:
                percentage = float(grade_info)
            except (TypeError, ValueError):
                percentage = 0.0
            letter_grade = "N/A"
        rows.append(
            {
                "subject": subject,
                "letter_grade": letter_grade,
                "percentage": round(percentage, 1),
            }
        )
    return rows


def _attendance_rows_from_snapshot(attendance: dict) -> list[dict[str, Any]]:
    if not isinstance(attendance, dict) or not attendance:
        return []
    first_val = next(iter(attendance.values()), None)
    if not isinstance(first_val, dict):
        return []
    rows = []
    for class_name, att_data in attendance.items():
        if not isinstance(att_data, dict):
            continue
        rows.append(
            {
                "class_name": class_name,
                "present": att_data.get("Present", 0),
                "unexcused": att_data.get("Unexcused Absence", 0),
                "excused": att_data.get("Excused Absence", 0),
                "tardy": att_data.get("Tardy", 0),
            }
        )
    return rows


def _comment_rows_from_snapshot(
    comments_by_class: dict,
    selected_class_ids: list,
    additional_comments: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    class_map: dict[int, str] = {}
    if selected_class_ids:
        for class_obj in Class.query.filter(Class.id.in_(selected_class_ids)).all():
            class_map[class_obj.id] = class_obj.name
    for key, text in (comments_by_class or {}).items():
        if not (text or "").strip():
            continue
        try:
            class_id = int(key)
        except (TypeError, ValueError):
            class_id = None
        rows.append(
            {
                "class_id": class_id,
                "class_name": class_map.get(class_id, f"Class {key}") if class_id else str(key),
                "comment": text.strip(),
            }
        )
    if (additional_comments or "").strip():
        rows.append(
            {
                "class_id": None,
                "class_name": "Additional comments",
                "comment": additional_comments.strip(),
            }
        )
    return rows


def _serialize_report_card(rc: ReportCard) -> dict[str, Any]:
    student = rc.student
    school_year = rc.school_year
    report_type = _report_type_from_details(rc.grades_details)
    return {
        "id": rc.id,
        "student": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "grade_level": student.grade_level,
            "grade_display": _grade_display(student.grade_level),
            "initials": f"{(student.first_name or '?')[0]}{(student.last_name or '')[0]}",
        }
        if student
        else None,
        "school_year": {
            "id": school_year.id,
            "name": school_year.name,
        }
        if school_year
        else None,
        "quarter": rc.quarter,
        "report_type": report_type,
        "generated_at": rc.generated_at.isoformat() if rc.generated_at else None,
        "generated_at_display": _format_generated_at(rc.generated_at),
        "director_approved": bool(rc.director_approved),
        "publish_status": (
            "unofficial"
            if report_type == "unofficial"
            else ("published" if rc.director_approved else "pending")
        ),
        "urls": _spa_report_card_urls(rc.id, student.id if student else None),
    }


def _category_cards(category_counts: dict[str, int]) -> list[dict[str, Any]]:
    cards = [
        {
            "slug": "elementary",
            "title": "Elementary school",
            "range_label": "Kindergarten – 5th grade",
            "description": "Foundational through upper-elementary progress and standards-based grading.",
            "icon": "bi-pencil-square",
            "tone": "emerald",
            "student_count": category_counts.get("elementary", 0),
        },
        {
            "slug": "6-8",
            "title": "Middle school",
            "range_label": "6th – 8th grade",
            "description": "Subject-specific grades and teacher comments.",
            "icon": "bi-mortarboard-fill",
            "tone": "amber",
            "student_count": category_counts.get("6-8", 0),
        },
        {
            "slug": "9-12",
            "title": "High school",
            "range_label": "9th – 12th grade",
            "description": "Credit-based courses, GPA, and graduation requirements.",
            "icon": "bi-building",
            "tone": "sky",
            "student_count": category_counts.get("9-12", 0),
        },
    ]
    for card in cards:
        card["path"] = f"/management/report-cards/category/{card['slug']}"
    return cards


def query_report_cards_hub() -> dict[str, Any]:
    all_students = (
        Student.query.filter(Student.is_deleted.is_(False))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    category_counts = {
        key: sum(1 for student in all_students if student.grade_level in info["grades"])
        for key, info in REPORT_CARD_CATEGORIES.items()
    }

    recent_cards = (
        ReportCard.query.options(
            selectinload(ReportCard.student),
            selectinload(ReportCard.school_year),
        )
        .order_by(nullslast(desc(ReportCard.generated_at)))
        .limit(10)
        .all()
    )

    total_reports = ReportCard.query.count()

    return {
        "stats": {
            "total_students": len(all_students),
            "total_reports": total_reports,
            "pending_parent_approval": count_pending_parent_approval(),
            "school_years_count": SchoolYear.query.count(),
        },
        "categories": _category_cards(category_counts),
        "recent_reports": [_serialize_report_card(rc) for rc in recent_cards],
        "urls": {
            "generate_form": "/management/report-cards/generate",
            "students": "/management/students",
            "grades": "/management/assignments",
            "attendance": "/management/attendance",
            "home": "/management",
            **_standards_checklist_urls(),
        },
    }


def query_report_cards_category(category_slug: str) -> dict[str, Any] | None:
    category = _resolve_report_card_category(category_slug)
    if category not in REPORT_CARD_CATEGORIES:
        return None

    category_info = REPORT_CARD_CATEGORIES[category]
    students = (
        Student.query.options(
            selectinload(Student.report_cards).selectinload(ReportCard.school_year),
            selectinload(Student.enrollments),
        )
        .filter(
            Student.is_deleted.is_(False),
            Student.grade_level.in_(category_info["grades"]),
        )
        .order_by(Student.last_name, Student.first_name)
        .all()
    )

    student_items = []
    total_reports = 0
    with_reports = 0

    for student in students:
        recent = _sort_report_cards_newest_first(student.report_cards)[:5]
        report_count = len(student.report_cards or [])
        if report_count:
            with_reports += 1
            total_reports += report_count

        active_enrollments = sum(1 for e in (student.enrollments or []) if e.is_active)

        student_items.append(
            {
                "id": student.id,
                "student_id": student.student_id or "",
                "first_name": student.first_name,
                "last_name": student.last_name,
                "name": f"{student.first_name} {student.last_name}",
                "grade_level": student.grade_level,
                "grade_display": _grade_display(student.grade_level),
                "initials": f"{(student.first_name or '?')[0]}{(student.last_name or '')[0]}",
                "enrollment_count": active_enrollments,
                "report_count": report_count,
                "generate_url": f"/management/report-cards/generate/{student.id}?category={category}",
                "recent_reports": [_serialize_report_card(rc) for rc in recent],
            }
        )

    warnings_ctx = report_card_warnings_template_context()
    unfinalized_grades = warnings_ctx.get("report_card_unfinalized_grades", [])

    return {
        "category": {
            "slug": category,
            "name": category_info["name"],
            "short_name": {
                "elementary": "Elementary",
                "6-8": "Middle school",
                "9-12": "High school",
            }.get(category, category_info["name"]),
            "icon": category_info["icon"],
            "grade_levels": category_info["grades"],
            "grade_displays": [_grade_display(g) for g in category_info["grades"]],
        },
        "stats": {
            "total_students": len(students),
            "grade_levels": len(category_info["grades"]),
            "total_reports": total_reports,
            "students_without_reports": len(students) - with_reports,
        },
        "students": student_items,
        "urls": {
            "hub": "/management/report-cards",
            "generate_form": "/management/report-cards/generate",
            **(_standards_checklist_urls() if category == "elementary" else {}),
        },
        "warnings": {
            "unfinalized_grades": unfinalized_grades,
            "banner_messages": warnings_ctx.get("report_card_unfinalized_banner_messages", {}),
        },
    }


def delete_report_card_record(report_card_id: int) -> dict[str, Any]:
    report_card = ReportCard.query.get(report_card_id)
    if report_card is None:
        return {"success": False, "message": "Report card not found."}

    student = report_card.student
    student_name = f"{student.first_name} {student.last_name}" if student else "Unknown"
    quarter = report_card.quarter

    try:
        db.session.delete(report_card)
        db.session.commit()
        return {
            "success": True,
            "message": f"Report card deleted for {student_name} ({quarter}).",
        }
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "message": f"Error deleting report card: {exc}"}


def query_report_card_generate_form(
    student_id: int | None = None,
    category: str = "",
    default_school_year_id: int | None = None,
) -> dict[str, Any]:
    students = (
        Student.query.filter(Student.is_deleted.is_(False))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    active_sy = next((sy for sy in school_years if sy.is_active), None)
    resolved_default_year = default_school_year_id or (active_sy.id if active_sy else None)
    if resolved_default_year and not any(sy.id == resolved_default_year for sy in school_years):
        extra_sy = SchoolYear.query.get(resolved_default_year)
        if extra_sy:
            school_years = [extra_sy] + school_years
    preselected = None
    if student_id:
        student = Student.query.get(student_id)
        if student and not student.is_deleted:
            preselected = {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "grade_level": student.grade_level,
                "grade_display": _grade_display(student.grade_level),
                "student_id": student.student_id or "",
            }

    student_options = [
        {
            "id": s.id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "grade_level": s.grade_level,
            "grade_display": _grade_display(s.grade_level),
            "student_id": s.student_id or "",
            "is_active": bool(getattr(s, "is_active", True)),
            "label": f"{s.first_name} {s.last_name} — Grade {_grade_display(s.grade_level)}",
        }
        for s in students
    ]

    warnings_ctx = report_card_warnings_template_context()
    checklist_urls = _standards_checklist_urls()
    preselected_checklist = (
        _standards_checklist_info(preselected["grade_level"]) if preselected else None
    )
    return {
        "students": student_options,
        "school_years": [
            {
                "id": sy.id,
                "name": sy.name,
                "is_active": bool(sy.is_active),
            }
            for sy in school_years
        ],
        "default_school_year_id": resolved_default_year,
        "preselected_student": preselected,
        "category": category if category in REPORT_CARD_CATEGORIES else "",
        "entrance_school_year_options": _build_entrance_school_year_options(),
        "quarters": ["Q1", "Q2", "Q3", "Q4"],
        "standards_checklist_legend": STANDARDS_CHECKLIST_LEGEND,
        "standards_checklist_urls": checklist_urls,
        "preselected_standards_checklist": preselected_checklist,
        "urls": {
            "hub": "/management/report-cards",
            "students_profile": "/management/students",
            **checklist_urls,
        },
        "warnings": {
            "unfinalized_grades": warnings_ctx.get("report_card_unfinalized_grades", []),
            "banner_messages": warnings_ctx.get("report_card_unfinalized_banner_messages", {}),
        },
    }


def query_student_report_card_details(student_id: int) -> dict[str, Any] | None:
    student = Student.query.get(student_id)
    if not student or student.is_deleted:
        return None

    address_parts = []
    if student.street:
        address_parts.append(student.street)
    if student.apt_unit:
        address_parts.append(student.apt_unit)
    if student.city:
        address_parts.append(student.city)
    if student.state:
        address_parts.append(student.state)
    if student.zip_code:
        address_parts.append(student.zip_code)
    address = ", ".join(address_parts) if address_parts else ""

    expected_grad_date = getattr(student, "expected_grad_date", None) or _calculate_expected_grad_date(
        student.grade_level, getattr(student, "entrance_date", None)
    )
    student_id_formatted = student.student_id if student.student_id else "N/A"
    if hasattr(student, "student_id_formatted"):
        student_id_formatted = student.student_id_formatted

    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "student_id": student_id_formatted,
        "gender": getattr(student, "gender", None) or "",
        "grade_level": student.grade_level,
        "grade_display": _grade_display(student.grade_level),
        "address": address,
        "dob": student.dob if student.dob else None,
        "state_id": getattr(student, "ssn", None)
        or getattr(student, "state_student_id", None)
        or "",
        "entrance_date": getattr(student, "entrance_date", None) or "",
        "expected_grad_date": expected_grad_date or "",
        "profile_url": f"/management/students/{student.id}",
        "standards_checklist": _standards_checklist_info(student.grade_level),
    }


def query_student_classes_for_report_card(
    student_id: int,
    school_year_id: int | None = None,
    quarters: list[str] | None = None,
) -> dict[str, Any]:
    student = Student.query.get_or_404(student_id)
    school_year = None
    if not school_year_id:
        school_year = SchoolYear.query.filter_by(is_active=True).first()
        school_year_id = school_year.id if school_year else None
    else:
        school_year = SchoolYear.query.get(school_year_id)

    valid_quarters = [q for q in (quarters or []) if q in ("Q1", "Q2", "Q3", "Q4")]
    if not valid_quarters:
        valid_quarters = ["Q1", "Q2", "Q3", "Q4"]

    window_start = window_end = None
    if school_year_id:
        window_start, window_end = _selected_quarters_date_window(school_year_id, valid_quarters)

    require_active = enrollment_must_be_active_for_report_card(student, school_year)

    enrollments_q = Enrollment.query.filter_by(student_id=student_id).join(Class)
    if school_year_id:
        enrollments_q = enrollments_q.filter(Class.school_year_id == school_year_id)
    if require_active:
        enrollments_q = enrollments_q.filter(Enrollment.is_active.is_(True))
    enrollments = enrollments_q.all()

    classes_data = []
    for enrollment in enrollments:
        class_info = enrollment.class_info
        if not class_info:
            continue
        if window_start and window_end:
            if not _enrollment_eligible_for_report_card(enrollment, window_start, window_end):
                continue
        classes_data.append(
            {
                "id": class_info.id,
                "name": class_info.name,
                "subject": class_info.subject or "N/A",
                "teacher_name": (
                    f"{class_info.teacher.first_name} {class_info.teacher.last_name}"
                    if class_info.teacher
                    else "N/A"
                ),
            }
        )
    grade_at_year = grade_level_for_school_year(student, school_year) if school_year else None
    effective_grade = grade_at_year if grade_at_year is not None else student.grade_level
    standards_checklist = _standards_checklist_info(effective_grade)
    standards_summary = None
    if school_year_id and effective_grade in (1, 3):
        standards_summary = _standards_marks_summary(student_id, school_year_id, effective_grade)

    return {
        "classes": classes_data,
        "quarters": valid_quarters,
        "school_year": {
            "id": school_year.id,
            "name": school_year.name,
            "is_active": bool(school_year.is_active),
        }
        if school_year
        else None,
        "grade_at_year": grade_at_year,
        "grade_at_year_display": rc_grade_display(grade_at_year) if grade_at_year is not None else None,
        "includes_inactive_enrollments": not require_active,
        "standards_checklist": standards_checklist,
        "standards_marks_summary": standards_summary,
    }


def query_report_card_comment_prefill(
    student_id: int,
    school_year_id: int,
    class_ids: list[int],
) -> dict[str, Any]:
    if not student_id or not school_year_id or not class_ids:
        return {"success": False, "message": "Missing required parameters"}

    class_map = {}
    for class_obj in Class.query.filter(Class.id.in_(class_ids)).all():
        class_map[str(class_obj.id)] = class_obj.name

    comments = ReportCardComment.query.filter(
        ReportCardComment.student_id == student_id,
        ReportCardComment.school_year_id == school_year_id,
        ReportCardComment.quarter == "ALL",
        ReportCardComment.class_id.in_(class_ids),
    ).all()

    by_class = {str(row.class_id): row.comment_text or "" for row in comments}
    return {
        "success": True,
        "class_map": class_map,
        "comments_by_class": by_class,
    }


def submit_report_card_generate(payload: dict[str, Any]) -> dict[str, Any]:
    student_id = payload.get("student_id")
    school_year_id = payload.get("school_year_id")
    class_ids = payload.get("class_ids") or []
    selected_quarters = payload.get("quarters") or []
    report_type = payload.get("report_type", "official")
    include_attendance = bool(payload.get("include_attendance", True))
    include_comments = bool(payload.get("include_comments", True))
    persist_comment_overrides = bool(payload.get("persist_comment_overrides", False))
    additional_comments = (payload.get("additional_comments") or "").strip()
    return_category = (payload.get("return_category") or "").strip()
    comment_overrides = payload.get("comment_overrides") or {}

    if not student_id or not school_year_id:
        return {"success": False, "message": "Please select a student and school year."}
    if not class_ids:
        return {"success": False, "message": "Please select at least one class."}
    if not selected_quarters:
        return {"success": False, "message": "Please select at least one quarter."}

    try:
        student_id_int = int(student_id)
        school_year_id_int = int(school_year_id)
        class_ids_int = [int(cid) for cid in class_ids]
    except (TypeError, ValueError):
        return {"success": False, "message": "Invalid student, school year, or class selection."}

    valid_quarters = ["Q1", "Q2", "Q3", "Q4"]
    quarters_to_include = [q for q in selected_quarters if q in valid_quarters]
    if not quarters_to_include:
        return {"success": False, "message": "Invalid quarter selection."}

    if report_type not in ("official", "unofficial"):
        report_type = "official"

    comments_overrides = {}
    for cid in class_ids_int:
        key = str(cid)
        if key in comment_overrides:
            comments_overrides[key] = (comment_overrides[key] or "").strip()
        elif f"comment_{cid}" in payload:
            comments_overrides[key] = (payload.get(f"comment_{cid}") or "").strip()

    rc_result = persist_report_card_record(
        student_id_int=student_id_int,
        school_year_id_int=school_year_id_int,
        class_ids_int=class_ids_int,
        quarters_to_include=quarters_to_include,
        report_type=report_type,
        include_attendance=include_attendance,
        include_comments=include_comments,
        additional_comments=additional_comments,
        comments_overrides=comments_overrides,
        persist_comment_overrides=persist_comment_overrides,
        enrollment_must_be_active=True,
        notify_admins=True,
    )
    if not rc_result["ok"]:
        return {"success": False, "message": rc_result.get("error") or "Could not generate report card."}

    student = rc_result["student"]
    report_card = rc_result["report_card"]
    warnings = list(rc_result.get("warnings") or [])
    school_year = SchoolYear.query.get(school_year_id_int)
    grade_for_warning = grade_level_for_school_year(student, school_year) if school_year else student.grade_level
    unfinalized_msg = report_card_unfinalized_banner_message(grade_for_warning)
    if unfinalized_msg:
        warnings.append(unfinalized_msg)

    urls = _spa_report_card_urls(report_card.id, student.id)
    response: dict[str, Any] = {
        "success": True,
        "report_card_id": report_card.id,
        "warnings": warnings,
        "inconsistency_flag": bool(rc_result.get("inconsistency_flag")),
        "urls": urls,
        "student": {
            "id": student.id,
            "name": f"{student.first_name} {student.last_name}".strip(),
        },
    }
    if return_category in REPORT_CARD_CATEGORIES:
        response["return_category"] = return_category
        response["urls"]["return_category"] = (
            f"/management/report-cards/category/{return_category}"
            f"?highlight={student.id}&saved=1"
        )
    return response


def query_report_card_detail(report_card_id: int, *, is_director: bool) -> dict[str, Any] | None:
    report_card = (
        ReportCard.query.options(
            selectinload(ReportCard.student),
            selectinload(ReportCard.school_year),
            selectinload(ReportCard.approved_by),
        )
        .get(report_card_id)
    )
    if not report_card:
        return None

    snapshot = _parse_report_card_snapshot(report_card)
    student = report_card.student
    class_objects = []
    for class_id in snapshot["selected_class_ids"]:
        class_obj = Class.query.get(class_id)
        if class_obj:
            class_objects.append(
                {
                    "id": class_obj.id,
                    "name": class_obj.name,
                    "subject": class_obj.subject or "N/A",
                }
            )

    approved_at_display = None
    if report_card.approved_at:
        approved_at_display = report_card.approved_at.strftime("%B %d, %Y at %I:%M %p")

    grade_level, grade_display = _grade_for_report_card(
        report_card, student, report_card.school_year
    )

    return {
        "report_card": {
            "id": report_card.id,
            "quarter": report_card.quarter,
            "report_type": snapshot["report_type"],
            "generated_at": report_card.generated_at.isoformat() if report_card.generated_at else None,
            "generated_at_display": _format_generated_at(report_card.generated_at),
            "director_approved": bool(report_card.director_approved),
            "publish_status": (
                "unofficial"
                if snapshot["report_type"] == "unofficial"
                else ("published" if report_card.director_approved else "pending")
            ),
            "is_official": is_official_report_card(report_card),
            "approved_at_display": approved_at_display,
            "approved_by": report_card.approved_by.username if report_card.approved_by else None,
        },
        "student": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "grade_level": grade_level if grade_level is not None else student.grade_level,
            "grade_display": grade_display,
            "student_id": student.student_id or "N/A",
        }
        if student
        else None,
        "school_year": {
            "id": report_card.school_year.id,
            "name": report_card.school_year.name,
        }
        if report_card.school_year
        else None,
        "classes": class_objects,
        "grades": _grade_rows_from_snapshot(snapshot["grades"]),
        "attendance": _attendance_rows_from_snapshot(snapshot["attendance"]),
        "include_attendance": snapshot["include_attendance"],
        "include_comments": snapshot["include_comments"],
        "comments": _comment_rows_from_snapshot(
            snapshot["comments_by_class"],
            snapshot["selected_class_ids"],
            snapshot["additional_comments"],
        ),
        "is_director": is_director,
        "urls": _spa_report_card_urls(report_card.id, student.id if student else None),
        "standards_checklist": _standards_checklist_info(grade_level),
        "standards_marks_summary": (
            _standards_marks_summary(student.id, report_card.school_year_id, grade_level)
            if student and report_card.school_year_id and grade_level in (1, 3)
            else None
        ),
    }


def query_student_report_card_school_years(student_id: int) -> dict[str, Any] | None:
    student = Student.query.get(student_id)
    if not student or student.is_deleted:
        return None

    enrolled_year_ids = {
        row[0]
        for row in (
            db.session.query(Class.school_year_id)
            .join(Enrollment, Enrollment.class_id == Class.id)
            .filter(Enrollment.student_id == student_id)
            .distinct()
            .all()
        )
        if row[0] is not None
    }

    report_cards = (
        ReportCard.query.filter_by(student_id=student_id)
        .options(selectinload(ReportCard.school_year))
        .all()
    )
    cards_by_year_id: dict[int, list[ReportCard]] = {}
    for rc in report_cards:
        if rc.school_year_id:
            cards_by_year_id.setdefault(rc.school_year_id, []).append(rc)

    year_ids = enrolled_year_ids | set(cards_by_year_id.keys())
    school_years = (
        SchoolYear.query.filter(SchoolYear.id.in_(year_ids)).order_by(SchoolYear.start_date.desc()).all()
        if year_ids
        else []
    )

    years_payload = []
    for sy in school_years:
        derived = grade_level_for_school_year(student, sy)
        grade_level = derived
        grade_display = rc_grade_display(derived) if derived is not None else "N/A"
        year_cards = cards_by_year_id.get(sy.id, [])
        if year_cards:
            snapshot_grade, snapshot_display = _grade_for_report_card(
                year_cards[0], student, sy
            )
            if snapshot_grade is not None:
                grade_level, grade_display = snapshot_grade, snapshot_display

        class_payload = query_student_classes_for_report_card(student_id, sy.id, ["Q1", "Q2", "Q3", "Q4"])
        years_payload.append(
            {
                "id": sy.id,
                "name": sy.name,
                "is_active": bool(sy.is_active),
                "status_label": "Active" if sy.is_active else "Closed",
                "grade_level": grade_level,
                "grade_display": grade_display,
                "class_count": len(class_payload.get("classes") or []),
                "report_count": len(year_cards),
                "report_cards": [_serialize_report_card(rc) for rc in _sort_report_cards_newest_first(year_cards)],
                "generate_url": f"/management/report-cards/generate/{student.id}?school_year_id={sy.id}",
                "has_enrollment": sy.id in enrolled_year_ids,
            }
        )

    return {
        "student": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "grade_level": student.grade_level,
            "grade_display": _grade_display(student.grade_level),
            "entrance_date": getattr(student, "entrance_date", None) or "",
        },
        "school_years": years_payload,
        "urls": {
            "history": f"/management/report-cards/student/{student.id}",
            "generate": f"/management/report-cards/generate/{student.id}",
            "hub": "/management/report-cards",
        },
    }


def query_student_report_card_history(student_id: int) -> dict[str, Any] | None:
    student = Student.query.get(student_id)
    if not student or student.is_deleted:
        return None

    report_cards_list = (
        ReportCard.query.filter_by(student_id=student_id)
        .join(SchoolYear)
        .options(selectinload(ReportCard.school_year))
        .order_by(SchoolYear.start_date.desc(), ReportCard.quarter.desc())
        .all()
    )

    by_year: dict[str, dict[str, Any]] = {}
    for rc in report_cards_list:
        year_name = rc.school_year.name if rc.school_year else "Unknown"
        snapshot = _parse_report_card_snapshot(rc)
        class_count = len(snapshot["selected_class_ids"])
        grade_level, grade_display = _grade_for_report_card(rc, student, rc.school_year)
        if rc.school_year:
            derived = grade_level_for_school_year(student, rc.school_year)
            if derived is not None and grade_from_report_card_snapshot(rc.grades_details) is None:
                grade_level, grade_display = derived, rc_grade_display(derived)
        entry = by_year.setdefault(
            year_name,
            {
                "school_year": year_name,
                "school_year_id": rc.school_year_id,
                "is_active": bool(rc.school_year.is_active) if rc.school_year else False,
                "grade_level": grade_level,
                "grade_display": grade_display,
                "report_cards": [],
            },
        )
        entry["report_cards"].append(
            {
                **_serialize_report_card(rc),
                "generated_at_long": _format_generated_at_long(rc.generated_at),
                "class_count": class_count,
                "class_count_label": (
                    f"{class_count} class{'es' if class_count != 1 else ''}"
                    if class_count
                    else "All enrolled classes"
                ),
            }
        )

    school_years_summary = query_student_report_card_school_years(student_id)

    return {
        "student": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "grade_level": student.grade_level,
            "grade_display": _grade_display(student.grade_level),
            "student_id": student.student_id or "",
            "initials": f"{(student.first_name or '?')[0]}{(student.last_name or '')[0]}",
        },
        "total_count": len(report_cards_list),
        "report_cards_by_year": list(by_year.values()),
        "school_years": (school_years_summary or {}).get("school_years", []),
        "urls": {
            "generate": f"/management/report-cards/generate/{student.id}",
            "hub": "/management/report-cards",
        },
    }


def query_report_cards_filter_options() -> dict[str, Any]:
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    students = (
        Student.query.filter(Student.is_deleted.is_(False))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    classes = Class.query.order_by(Class.name).all()
    return {
        "school_years": [
            {"id": sy.id, "name": sy.name, "is_active": bool(sy.is_active)}
            for sy in school_years
        ],
        "students": [
            {
                "id": s.id,
                "name": f"{s.first_name} {s.last_name}",
                "grade_display": _grade_display(s.grade_level),
            }
            for s in students
        ],
        "classes": [
            {
                "id": c.id,
                "name": c.name,
                "school_year_id": c.school_year_id,
            }
            for c in classes
        ],
        "quarters": ["Q1", "Q2", "Q3", "Q4"],
    }


def query_pending_report_cards(limit: int = 50) -> dict[str, Any]:
    candidates = (
        ReportCard.query.options(
            selectinload(ReportCard.student),
            selectinload(ReportCard.school_year),
        )
        .filter(ReportCard.director_approved.is_(False))
        .order_by(nullslast(desc(ReportCard.generated_at)))
        .limit(max(limit * 5, limit))
        .all()
    )
    pending = [rc for rc in candidates if is_official_report_card(rc)][:limit]
    return {
        "total": count_pending_parent_approval(),
        "report_cards": [_serialize_report_card(rc) for rc in pending],
    }


def query_report_cards_search(params: dict[str, Any]) -> dict[str, Any]:
    page = max(1, int(params.get("page") or 1))
    per_page = min(100, max(1, int(params.get("per_page") or 25)))
    school_year_id = params.get("school_year_id")
    quarter = (params.get("quarter") or "").strip()
    student_id = params.get("student_id")
    class_id = params.get("class_id")
    search_q = (params.get("q") or "").strip()

    query = ReportCard.query.options(
        selectinload(ReportCard.student),
        selectinload(ReportCard.school_year),
    )

    if school_year_id:
        query = query.filter(ReportCard.school_year_id == int(school_year_id))
    if quarter and quarter not in ("All", ""):
        query = query.filter(ReportCard.quarter == quarter)
    if student_id:
        query = query.filter(ReportCard.student_id == int(student_id))
    if search_q:
        like = f"%{search_q}%"
        query = query.join(Student).filter(
            Student.is_deleted.is_(False),
            or_(
                Student.first_name.ilike(like),
                Student.last_name.ilike(like),
                Student.student_id.ilike(like),
            ),
        )

    query = query.order_by(nullslast(desc(ReportCard.generated_at)))

    if class_id:
        class_id_int = int(class_id)
        all_rows = query.all()
        filtered = [
            rc
            for rc in all_rows
            if class_id_int in (_parse_report_card_snapshot(rc).get("selected_class_ids") or [])
        ]
        total = len(filtered)
        start = (page - 1) * per_page
        items = filtered[start : start + per_page]
    else:
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()

    pages = max(1, (total + per_page - 1) // per_page)

    return {
        "report_cards": [_serialize_report_card(rc) for rc in items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
        },
        "filters": query_report_cards_filter_options(),
        "applied": {
            "school_year_id": int(school_year_id) if school_year_id else None,
            "quarter": quarter or None,
            "student_id": int(student_id) if student_id else None,
            "class_id": int(class_id) if class_id else None,
            "q": search_q or None,
        },
    }
