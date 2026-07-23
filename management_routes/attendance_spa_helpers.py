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
                "take_attendance_url": f"/app/management/attendance/take/{class_obj.id}?date={class_date_str_out}",
                "view_class_url": f"/app/management/classes/{class_obj.id}",
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


def query_take_class_attendance(class_id: int, date_str: str | None = None) -> dict[str, Any]:
    """Payload for class-period attendance (React SPA)."""
    from utils.attendance_status import (
        VALID_ATTENDANCE_STATUSES,
        attendance_status_form_value,
        count_class_attendance_stats,
    )

    class_obj = Class.query.get_or_404(class_id)
    if not getattr(class_obj, "school_year_id", None):
        raise ValueError("This class is not associated with an active school year.")
    if getattr(class_obj, "is_active", True) is False:
        raise ValueError("This class is archived or inactive.")

    enrolled = (
        db.session.query(Student)
        .join(Enrollment)
        .filter(Enrollment.class_id == class_id, Enrollment.is_active.is_(True))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    if not enrolled:
        raise ValueError("No students are enrolled in this class.")

    today = datetime.now().date()
    attendance_date, attendance_date_str = _parse_date_arg(date_str, today)
    if attendance_date > today:
        attendance_date = today
        attendance_date_str = today.strftime("%Y-%m-%d")

    existing_records = {
        rec.student_id: rec
        for rec in Attendance.query.filter_by(class_id=class_id, date=attendance_date).all()
    }
    school_day_records = {
        rec.student_id: rec
        for rec in SchoolDayAttendance.query.filter_by(date=attendance_date).all()
    }
    selected_rows = list(existing_records.values())
    stats = count_class_attendance_stats(selected_rows, len(enrolled))
    stats["total"] = len(enrolled)
    stats["suspended"] = sum(
        1 for rec in selected_rows if (rec.status or "").strip().lower() == "suspended"
    )

    rows = []
    for student in enrolled:
        rec = existing_records.get(student.id)
        school_day = school_day_records.get(student.id)
        rows.append(
            {
                "student_id": student.id,
                "display_name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
                "grade_level": getattr(student, "grade_level", None),
                "status": attendance_status_form_value(rec.status) if rec else "",
                "notes": (rec.notes or "") if rec else "",
                "school_day_status": school_day.status if school_day else None,
            }
        )

    return {
        "class": {
            "id": class_obj.id,
            "name": class_obj.name,
            "subject": getattr(class_obj, "subject", None),
        },
        "date": attendance_date_str,
        "statuses": list(VALID_ATTENDANCE_STATUSES),
        "rows": rows,
        "stats": stats,
        "urls": {
            "attendance_hub": "/app/management/attendance",
            "class_view": f"/app/management/classes/{class_id}",
        },
    }


def save_take_class_attendance(
    class_id: int,
    date_str: str,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    from utils.attendance_status import VALID_ATTENDANCE_STATUSES, normalize_attendance_status

    Class.query.get_or_404(class_id)
    try:
        attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"success": False, "message": "Invalid date. Use YYYY-MM-DD."}

    if attendance_date > datetime.now().date():
        return {"success": False, "message": "Cannot record attendance for a future date."}

    teacher_id = getattr(current_user, "teacher_staff_id", None)
    saved = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        student_id = entry.get("student_id")
        status = normalize_attendance_status(entry.get("status"))
        notes = (entry.get("notes") or "").strip()
        if not student_id or not status:
            continue
        if status not in VALID_ATTENDANCE_STATUSES:
            continue
        enrollment = Enrollment.query.filter_by(
            student_id=int(student_id),
            class_id=class_id,
            is_active=True,
        ).first()
        if not enrollment:
            continue
        record = Attendance.query.filter_by(
            student_id=int(student_id),
            class_id=class_id,
            date=attendance_date,
        ).first()
        if record:
            record.status = status
            record.notes = notes
            record.teacher_id = teacher_id
        else:
            db.session.add(
                Attendance(
                    student_id=int(student_id),
                    class_id=class_id,
                    date=attendance_date,
                    status=status,
                    notes=notes,
                    teacher_id=teacher_id,
                )
            )
        saved += 1

    if not saved:
        return {"success": False, "message": "No attendance rows were saved."}
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "message": f"Error saving attendance: {exc}"}
    return {
        "success": True,
        "message": "Attendance recorded successfully.",
        "redirect_url": f"/app/management/attendance?class_date={date_str}",
    }


def query_class_attendance_records(
    class_id: int,
    *,
    start_date_str: str | None = None,
    end_date_str: str | None = None,
    student_id: int | None = None,
    status_filter: str | None = None,
) -> dict[str, Any]:
    from datetime import timedelta
    from sqlalchemy.orm import joinedload

    class_obj = Class.query.get_or_404(class_id)
    today = datetime.now().date()
    if not start_date_str:
        start_date = today - timedelta(days=30)
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = today - timedelta(days=30)

    if not end_date_str:
        end_date = today
    else:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            end_date = today

    query = (
        Attendance.query.options(joinedload(Attendance.student))
        .join(Student)
        .filter(
            Attendance.class_id == class_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date,
        )
    )
    if student_id:
        query = query.filter(Attendance.student_id == student_id)
    if status_filter:
        query = query.filter(Attendance.status.ilike(f"%{status_filter}%"))

    records = query.order_by(Attendance.date.desc(), Student.last_name, Student.first_name).all()
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [
        {
            "id": e.student.id,
            "display_name": f"{e.student.first_name or ''} {e.student.last_name or ''}".strip(),
            "student_id": getattr(e.student, "student_id", None),
        }
        for e in enrollments
        if e.student is not None
    ]

    records_by_date: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if not record.student:
            continue
        date_key = record.date.isoformat()
        records_by_date.setdefault(date_key, []).append(
            {
                "id": record.id,
                "student_id": record.student_id,
                "display_name": f"{record.student.first_name or ''} {record.student.last_name or ''}".strip(),
                "status": record.status or "",
                "notes": record.notes or "",
            }
        )

    total_records = len(records)
    present_count = sum(1 for r in records if (r.status or "").lower() == "present")
    late_count = sum(1 for r in records if (r.status or "").lower() == "late")
    absent_count = sum(
        1
        for r in records
        if (r.status or "").lower() in ("absent", "unexcused absence", "excused absence")
    )

    return {
        "class": {
            "id": class_obj.id,
            "name": class_obj.name,
            "subject": getattr(class_obj, "subject", None),
        },
        "students": students,
        "records_by_date": records_by_date,
        "summary": {
            "total": total_records,
            "present": present_count,
            "late": late_count,
            "absent": absent_count,
            "rate": round((present_count / total_records * 100) if total_records > 0 else 0, 1),
        },
        "filters": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "student_id": student_id,
            "status": status_filter or "",
        },
    }


def process_attendance_csv_upload(class_id: int, file_storage, teacher_id: int | None) -> dict[str, Any]:
    import csv
    import io
    from datetime import date as date_cls

    Class.query.get_or_404(class_id)
    if not file_storage or not getattr(file_storage, "filename", ""):
        return {"success": False, "message": "No file uploaded."}
    if not file_storage.filename.lower().endswith(".csv"):
        return {"success": False, "message": "Please upload a CSV file."}

    stream = io.StringIO(file_storage.stream.read().decode("UTF-8"), newline=None)
    csv_reader = csv.DictReader(stream)
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    student_id_map = {
        enrollment.student.student_id: enrollment.student.id
        for enrollment in enrollments
        if enrollment.student and enrollment.student.student_id
    }
    valid_statuses = ["Present", "Late", "Unexcused Absence", "Excused Absence", "Suspended"]
    records_added = 0
    records_updated = 0
    records_skipped = 0
    errors: list[str] = []

    for row_num, row in enumerate(csv_reader, start=2):
        try:
            date_str = (row.get("Date (MM/DD/YYYY)") or "").strip()
            if date_str.startswith("#") or not date_str:
                continue
            student_id_str = (row.get("Student ID") or "").strip()
            status = (row.get("Status") or "").strip()
            notes = (row.get("Notes (Optional)") or "").strip()
            if not date_str or not student_id_str or not status:
                errors.append(f"Row {row_num}: Missing required fields")
                records_skipped += 1
                continue
            try:
                attendance_date = datetime.strptime(date_str, "%m/%d/%Y").date()
            except ValueError:
                try:
                    attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    errors.append(f'Row {row_num}: Invalid date "{date_str}"')
                    records_skipped += 1
                    continue
            if attendance_date > date_cls.today():
                errors.append(f"Row {row_num}: Future date {date_str}")
                records_skipped += 1
                continue
            if status not in valid_statuses:
                errors.append(f'Row {row_num}: Invalid status "{status}"')
                records_skipped += 1
                continue
            if student_id_str not in student_id_map:
                errors.append(f'Row {row_num}: Student ID "{student_id_str}" not in roster')
                records_skipped += 1
                continue
            student_db_id = student_id_map[student_id_str]
            existing_record = Attendance.query.filter_by(
                class_id=class_id,
                student_id=student_db_id,
                date=attendance_date,
            ).first()
            if existing_record:
                existing_record.status = status
                existing_record.notes = notes or existing_record.notes
                existing_record.teacher_id = teacher_id
                records_updated += 1
            else:
                db.session.add(
                    Attendance(
                        class_id=class_id,
                        student_id=student_db_id,
                        date=attendance_date,
                        status=status,
                        notes=notes,
                        teacher_id=teacher_id,
                    )
                )
                records_added += 1
        except Exception as exc:
            errors.append(f"Row {row_num}: {exc}")
            records_skipped += 1

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "message": f"Error saving CSV data: {exc}"}

    return {
        "success": True,
        "message": f"CSV processed: {records_added} added, {records_updated} updated, {records_skipped} skipped.",
        "records_added": records_added,
        "records_updated": records_updated,
        "records_skipped": records_skipped,
        "errors": errors[:20],
    }
