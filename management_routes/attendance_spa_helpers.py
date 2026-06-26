"""Unified attendance hub payloads for the React management SPA."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import url_for
from flask_login import current_user

from extensions import db
from models import Attendance, Class, Enrollment, SchoolDayAttendance, Student
from utils.school_year_filters import classes_for_active_school_year, get_active_school_year


SCHOOL_DAY_STATUSES = ("Present", "Unexcused Absence", "Late", "Excused Absence")


def _display_grade_label(grade_level) -> str:
    if grade_level == 0:
        return "K"
    if grade_level is not None:
        return str(grade_level)
    return "N/A"


def _parse_date_arg(value: str | None, default):
    if not value:
        return default, default.strftime("%Y-%m-%d")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        return parsed, value
    except ValueError:
        return default, default.strftime("%Y-%m-%d")


def query_unified_attendance_hub(
    school_date_str: str | None = None,
    class_date_str: str | None = None,
) -> dict[str, Any]:
    from flask import current_app
    from utils.student_roster import active_roster_students_query

    today = datetime.now().date()
    selected_date, selected_date_str = _parse_date_arg(school_date_str, today)

    students = (
        active_roster_students_query(require_active_enrollment=False)
        .order_by(Student.last_name, Student.first_name)
        .all()
    )

    try:
        from services.attendance_on_login import (
            _now_in_school_tz,
            apply_end_of_day_automark,
            is_past_end_of_day_cutoff,
        )

        school_today, _ = _now_in_school_tz(current_app)
        if selected_date == school_today and is_past_end_of_day_cutoff(current_app):
            apply_end_of_day_automark(current_app, selected_date)
    except Exception as exc:
        current_app.logger.warning("End-of-day attendance automark failed: %s", exc)

    existing_records: dict[int, SchoolDayAttendance] = {}
    if selected_date:
        records = SchoolDayAttendance.query.filter_by(date=selected_date).all()
        existing_records = {record.student_id: record for record in records}

    present_count = sum(1 for record in existing_records.values() if record.status == "Present")
    absent_count = sum(
        1
        for record in existing_records.values()
        if record.status in ("Absent", "Unexcused Absence")
    )
    late_count = sum(1 for record in existing_records.values() if record.status == "Late")
    excused_count = sum(
        1 for record in existing_records.values() if record.status == "Excused Absence"
    )
    total_students = len(students)

    school_day_stats = {
        "total": total_students,
        "present": present_count,
        "absent": absent_count,
        "late": late_count,
        "excused": excused_count,
    }

    school_day_students = []
    for student in students:
        record = existing_records.get(student.id)
        school_day_students.append(
            {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}",
                "grade_display": _display_grade_label(student.grade_level),
                "status": record.status if record else "",
                "notes": (record.notes or "") if record else "",
            }
        )

    class_date, class_date_str_out = _parse_date_arg(class_date_str, today)
    active_school_year = get_active_school_year()
    classes = classes_for_active_school_year()
    class_ids = [class_obj.id for class_obj in classes]
    class_items = []
    classes_completed = 0

    for class_obj in classes:
        student_count = (
            db.session.query(Student)
            .join(Enrollment)
            .filter(Enrollment.class_id == class_obj.id, Enrollment.is_active.is_(True))
            .count()
        )

        date_attendance = Attendance.query.filter_by(
            class_id=class_obj.id,
            date=class_date,
        ).count()
        attendance_taken = date_attendance > 0
        if attendance_taken:
            classes_completed += 1

        today_present = 0
        today_absent = 0
        if attendance_taken:
            today_present = Attendance.query.filter_by(
                class_id=class_obj.id,
                date=class_date,
                status="Present",
            ).count()
            today_absent = Attendance.query.filter(
                Attendance.class_id == class_obj.id,
                Attendance.date == class_date,
                Attendance.status.in_(["Unexcused Absence", "Excused Absence"]),
            ).count()

        teacher_name = "N/A"
        if class_obj.teacher:
            teacher_name = f"{class_obj.teacher.first_name} {class_obj.teacher.last_name}"

        class_items.append(
            {
                "id": class_obj.id,
                "name": class_obj.name,
                "subject": class_obj.subject or "General",
                "student_count": student_count,
                "teacher_name": teacher_name,
                "grade_levels_display": class_obj.get_grade_levels_display() or "N/A",
                "attendance_taken": attendance_taken,
                "today_present": today_present,
                "today_absent": today_absent,
                "take_attendance_url": (
                    url_for("management.take_class_attendance", class_id=class_obj.id)
                    + f"?date={class_date_str_out}"
                ),
                "view_class_url": url_for("management.view_class", class_id=class_obj.id),
            }
        )

    pending_classes = len(classes) - classes_completed
    if class_ids:
        total_attendance_records = Attendance.query.filter(
            Attendance.date == class_date,
            Attendance.class_id.in_(class_ids),
        ).count()
        present_records = Attendance.query.filter(
            Attendance.date == class_date,
            Attendance.class_id.in_(class_ids),
            Attendance.status == "Present",
        ).count()
    else:
        total_attendance_records = 0
        present_records = 0
    overall_rate = (
        round((present_records / total_attendance_records * 100), 1)
        if total_attendance_records > 0
        else 0
    )

    return {
        "school_date": selected_date_str,
        "class_date": class_date_str_out,
        "status_options": list(SCHOOL_DAY_STATUSES),
        "insights": {
            "total_students": total_students,
            "school_day_present": present_count,
            "classes_completed": classes_completed,
            "class_period_rate": overall_rate,
        },
        "school_day_stats": school_day_stats,
        "school_day_students": school_day_students,
        "class_period_stats": {
            "classes_completed": classes_completed,
            "pending_classes": pending_classes,
            "overall_rate": overall_rate,
        },
        "classes": class_items,
        "meta": {
            "has_active_school_year": active_school_year is not None,
            "active_school_year_id": active_school_year.id if active_school_year else None,
            "active_school_year_name": active_school_year.name if active_school_year else None,
            "school_day_year_independent": True,
        },
        "urls": {
            "analytics": "/management/attendance/analytics",
            "reports": "/management/attendance/reports",
        },
    }


def _teacher_display_name(teacher) -> str | None:
    if not teacher:
        return None
    return f"{teacher.first_name} {teacher.last_name}".strip()


def _report_date_presets(today) -> list[dict[str, str]]:
    from datetime import timedelta

    defs = [
        ("Today", today, today),
        ("7 days", today - timedelta(days=6), today),
        ("30 days", today - timedelta(days=29), today),
        ("90 days", today - timedelta(days=89), today),
    ]
    return [
        {
            "label": label,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
        }
        for label, start, end in defs
    ]


def _analytics_date_presets(today) -> list[dict[str, str]]:
    from datetime import timedelta

    defs = [
        ("7 days", today - timedelta(days=6), today),
        ("30 days", today - timedelta(days=29), today),
        ("90 days", today - timedelta(days=89), today),
        ("Year", today - timedelta(days=364), today),
    ]
    return [
        {
            "label": label,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
        }
        for label, start, end in defs
    ]


def serialize_attendance_reports(ctx: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime

    today = datetime.now().date()
    pagination = ctx["pagination"]
    records = []
    for record in ctx["records"]:
        student = record.student
        class_info = record.class_info
        records.append(
            {
                "id": record.id,
                "date": record.date.strftime("%Y-%m-%d"),
                "date_display": record.date.strftime("%m/%d/%Y"),
                "student": {
                    "id": student.id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "label": f"{student.last_name}, {student.first_name}",
                }
                if student
                else None,
                "class": {
                    "id": class_info.id,
                    "name": class_info.name,
                }
                if class_info
                else None,
                "status": record.status,
                "notes": record.notes or "",
                "recorded_by": _teacher_display_name(record.teacher),
            }
        )

    return {
        "filters": {
            "start_date": ctx["selected_start_date"],
            "end_date": ctx["selected_end_date"],
            "student_ids": ctx["selected_student_ids"],
            "class_ids": ctx["selected_class_ids"],
            "status": ctx["selected_status"],
        },
        "summary_stats": ctx["summary_stats"],
        "records": records,
        "pagination": {
            "page": pagination.page,
            "per_page": ctx["reports_per_page"],
            "total": pagination.total,
            "pages": pagination.pages or 1,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
            "prev_page": pagination.prev_num,
            "next_page": pagination.next_num,
        },
        "filter_options": {
            "students": [
                {
                    "id": student.id,
                    "label": f"{student.last_name}, {student.first_name}",
                }
                for student in ctx["all_students"]
            ],
            "classes": [{"id": class_item.id, "name": class_item.name} for class_item in ctx["all_classes"]],
            "statuses": ctx["all_statuses"],
        },
        "presets": _report_date_presets(today),
        "default_range_days": ctx["default_range_days"],
    }


def serialize_attendance_analytics(ctx: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime

    today = datetime.now().date()
    at_risk_students = []
    for item in ctx["at_risk_students"]:
        student = item["student"]
        pattern = item["pattern"]
        at_risk_students.append(
            {
                "student": {
                    "id": student.id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "label": f"{student.last_name}, {student.first_name}",
                    "grade_display": _display_grade_label(student.grade_level),
                    "view_url": url_for("management.view_student", student_id=student.id),
                },
                "attendance_rate": item["attendance_rate"],
                "risk_level": item["risk_level"],
                "pattern": {
                    "total_days": pattern["total_days"],
                    "present": pattern["present"],
                    "absent": pattern["absent"],
                    "late": pattern["late"],
                    "excused": pattern["excused"],
                    "max_consecutive_absences": pattern["max_consecutive_absences"],
                },
            }
        )

    daily_trend = []
    for day in ctx["daily_trend"]:
        daily_trend.append(
            {
                "date": day["date"].strftime("%Y-%m-%d"),
                "date_label": day["date_label"],
                "date_short": day["date"].strftime("%m/%d"),
                "total": day["total"],
                "present": day["present"],
                "rate": day["rate"],
            }
        )

    return {
        "filters": {
            "start_date": ctx["selected_start_date"],
            "end_date": ctx["selected_end_date"],
            "risk": ctx["risk_filter"],
        },
        "summary": {
            "overall_rate": ctx["overall_rate"],
            "total_records": ctx["total_records"],
            "present_count": ctx["present_count"],
            "students_tracked": ctx["students_tracked"],
            "at_risk_high": ctx["at_risk_high"],
            "at_risk_medium": ctx["at_risk_medium"],
            "days_analyzed": ctx["days_analyzed"],
        },
        "status_counts": ctx["status_counts"],
        "daily_trend": daily_trend,
        "trend_max": ctx["trend_max"],
        "at_risk_students": at_risk_students,
        "presets": _analytics_date_presets(today),
    }


def save_school_day_attendance(attendance_date_str: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not attendance_date_str:
        return {"success": False, "message": "Please select a date."}

    try:
        attendance_date = datetime.strptime(attendance_date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"success": False, "message": "Invalid date format."}

    updated_count = 0
    created_count = 0

    for entry in entries:
        student_id = entry.get("student_id")
        status = (entry.get("status") or "").strip()
        notes = (entry.get("notes") or "").strip()

        if not student_id or not status:
            continue
        if status not in SCHOOL_DAY_STATUSES:
            return {"success": False, "message": f"Invalid status: {status}"}

        existing_record = SchoolDayAttendance.query.filter_by(
            student_id=student_id,
            date=attendance_date,
        ).first()

        if existing_record:
            existing_record.status = status
            existing_record.notes = notes
            existing_record.recorded_by = current_user.id
            existing_record.updated_at = datetime.utcnow()
            updated_count += 1
        else:
            db.session.add(
                SchoolDayAttendance(
                    student_id=student_id,
                    date=attendance_date,
                    status=status,
                    notes=notes,
                    recorded_by=current_user.id,
                )
            )
            created_count += 1

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "message": f"Error saving attendance: {exc}"}

    if created_count > 0 and updated_count > 0:
        message = (
            f"Recorded attendance for {created_count} students and updated "
            f"{updated_count} existing records."
        )
    elif created_count > 0:
        message = f"Recorded attendance for {created_count} students."
    elif updated_count > 0:
        message = f"Updated attendance for {updated_count} students."
    else:
        message = "No attendance changes were made."

    return {
        "success": True,
        "message": message,
        "created_count": created_count,
        "updated_count": updated_count,
    }


def mark_class_all_present(class_id: int, date_str: str) -> dict[str, Any]:
    if not date_str:
        return {"success": False, "message": "Please select a date."}

    class_obj = Class.query.get(class_id)
    if class_obj is None:
        return {"success": False, "message": "Class not found."}

    active_school_year = get_active_school_year()
    if not active_school_year:
        return {"success": False, "message": "No active school year is set."}
    if class_obj.school_year_id != active_school_year.id or not class_obj.is_active:
        return {"success": False, "message": "Class is not part of the active school year."}

    try:
        attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"success": False, "message": "Invalid date format."}

    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    teacher_id = getattr(current_user, "teacher_staff_id", None)

    for student in students:
        existing_attendance = Attendance.query.filter_by(
            class_id=class_id,
            student_id=student.id,
            date=attendance_date,
        ).first()

        if existing_attendance:
            existing_attendance.status = "Present"
            existing_attendance.teacher_id = teacher_id
        else:
            db.session.add(
                Attendance(
                    class_id=class_id,
                    student_id=student.id,
                    date=attendance_date,
                    status="Present",
                    teacher_id=teacher_id,
                )
            )

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "message": f"Error marking all present: {exc}"}

    return {"success": True, "message": "All students marked as present."}
