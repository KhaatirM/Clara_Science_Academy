"""SPA payloads for teacher student grades/attendance reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models import Attendance, Class, Enrollment, SchoolYear, Student
from teacher_routes.utils import get_teacher_or_admin, is_admin
from utils.quarter_grade_calculator import get_quarter_grades_for_report


def _teacher_can_access_student(student_id: int) -> bool:
    if is_admin():
        return True
    teacher = get_teacher_or_admin()
    if teacher is None:
        return False
    teacher_classes = Class.query.filter_by(teacher_id=teacher.id).all()
    class_ids = [c.id for c in teacher_classes]
    if not class_ids:
        return False
    return (
        Enrollment.query.filter(
            Enrollment.student_id == student_id,
            Enrollment.class_id.in_(class_ids),
            Enrollment.is_active.is_(True),
        ).first()
        is not None
    )


def _student_brief(student: Student) -> dict[str, Any]:
    address = student.address or ""
    if not address and (student.street or student.city):
        address = f"{student.street or ''}, {student.city or ''}, {student.state or ''} {student.zip_code or ''}".strip(
            " ,"
        )
    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "name": f"{student.first_name} {student.last_name}".strip(),
        "grade_level": student.grade_level,
        "student_id": student.student_id or "N/A",
        "date_of_birth": str(student.dob) if student.dob else "N/A",
        "address": address or "N/A",
    }


def build_teacher_student_grades_report(student_id: int) -> tuple[dict[str, Any] | None, str | None]:
    student = Student.query.get(student_id)
    if not student:
        return None, "Student not found"
    if not _teacher_can_access_student(student_id):
        return None, "Forbidden"

    school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not school_year:
        return None, "No active school year found"

    enrollments = (
        Enrollment.query.filter_by(student_id=student_id, is_active=True)
        .join(Class)
        .filter(Class.school_year_id == school_year.id)
        .all()
    )
    class_ids = [e.class_id for e in enrollments]
    grades_by_quarter = get_quarter_grades_for_report(
        student_id=student_id,
        school_year_id=school_year.id,
        class_ids=class_ids if class_ids else None,
    )

    # Serialize nested grade structures for JSON
    quarters_payload: dict[str, list[dict[str, Any]]] = {}
    for quarter, by_class in (grades_by_quarter or {}).items():
        rows = []
        for class_id, grade_info in (by_class or {}).items():
            if isinstance(grade_info, dict):
                rows.append(
                    {
                        "class_id": class_id,
                        "class_name": grade_info.get("class_name") or f"Class {class_id}",
                        "letter": grade_info.get("letter"),
                        "percentage": grade_info.get("percentage"),
                        "assignments_count": grade_info.get("assignments_count"),
                    }
                )
            else:
                rows.append({"class_id": class_id, "class_name": f"Class {class_id}", "grade": grade_info})
        quarters_payload[str(quarter)] = rows

    classes = [
        {
            "id": e.class_info.id,
            "name": e.class_info.name,
            "subject": getattr(e.class_info, "subject", None),
        }
        for e in enrollments
        if e.class_info
    ]

    return {
        "kind": "grades",
        "student": _student_brief(student),
        "school_year": {"id": school_year.id, "name": school_year.name},
        "classes": classes,
        "grades_by_quarter": quarters_payload,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "urls": {
            "printable": f"/teacher/student/{student_id}/grades?legacy=1",
            "pdf": f"/teacher/student/{student_id}/grades/pdf",
            "back": "/app/teacher/students",
        },
    }, None


def build_teacher_student_attendance_report(
    student_id: int,
) -> tuple[dict[str, Any] | None, str | None]:
    student = Student.query.get(student_id)
    if not student:
        return None, "Student not found"
    if not _teacher_can_access_student(student_id):
        return None, "Forbidden"

    school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not school_year:
        return None, "No active school year found"

    attendance_records = (
        Attendance.query.filter_by(student_id=student_id)
        .join(Class, Attendance.class_id == Class.id)
        .filter(Class.school_year_id == school_year.id)
        .order_by(Attendance.date.desc())
        .all()
    )

    total_records = len(attendance_records)
    present_count = sum(1 for r in attendance_records if r.status and r.status.lower() == "present")
    late_count = sum(1 for r in attendance_records if r.status and r.status.lower() == "late")
    absent_count = sum(
        1
        for r in attendance_records
        if r.status and r.status.lower() in ["absent", "unexcused absence", "excused absence"]
    )
    excused_absent_count = sum(
        1 for r in attendance_records if r.status and "excused" in r.status.lower()
    )
    unexcused_absent_count = sum(
        1 for r in attendance_records if r.status and "unexcused" in r.status.lower()
    )
    attendance_rate = round((present_count / total_records * 100) if total_records > 0 else 0, 1)

    records_by_month: dict[str, list[dict[str, Any]]] = {}
    for record in attendance_records:
        month_key = record.date.strftime("%Y-%m")
        records_by_month.setdefault(month_key, []).append(
            {
                "id": record.id,
                "date": record.date.isoformat(),
                "date_display": record.date.strftime("%b %d, %Y"),
                "status": record.status,
                "class_name": record.class_info.name if record.class_info else "—",
                "notes": getattr(record, "notes", None) or "",
            }
        )

    return {
        "kind": "attendance",
        "student": _student_brief(student),
        "school_year": {"id": school_year.id, "name": school_year.name},
        "stats": {
            "total_records": total_records,
            "present_count": present_count,
            "late_count": late_count,
            "absent_count": absent_count,
            "excused_absent_count": excused_absent_count,
            "unexcused_absent_count": unexcused_absent_count,
            "attendance_rate": attendance_rate,
        },
        "records_by_month": [
            {"month": month, "records": rows}
            for month, rows in sorted(records_by_month.items(), reverse=True)
        ],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "urls": {
            "printable": f"/teacher/student/{student_id}/attendance?legacy=1",
            "pdf": f"/teacher/student/{student_id}/attendance/pdf",
            "back": "/app/teacher/students",
        },
    }, None
