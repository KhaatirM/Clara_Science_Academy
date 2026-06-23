"""Shared class payloads and mutations for the React management SPA."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from flask import current_app
from flask_login import current_user

from decorators import user_can_manage_student_assistants
from extensions import db
from management_routes.student_assistant_utils import (
    MAX_ASSISTANTS_PER_CLASS,
    MAX_CLASSES_PER_ASSISTANT,
    count_assistant_classes_for_student_excluding,
    filter_eligible_assistant_candidates,
    is_eligible_student_assistant_candidate,
    students_in_school_year_for_assistant_pool,
)
from models import (
    Assignment,
    Class,
    Enrollment,
    Grade,
    GroupAssignment,
    GroupGrade,
    SchoolYear,
    Student,
    StudentAssistant,
    StudentGroup,
    StudentGroupMember,
    TeacherStaff,
)
from services.class_google_group import try_provision_class_google_group
from utils.grade_helpers import get_points_earned

from .classes import (
    _staff_can_be_assigned_to_classes,
    serialize_class_list_item,
)


def _teacher_display(staff: TeacherStaff | None) -> dict[str, Any]:
    if not staff:
        return {"id": None, "display_name": "N/A", "email": None, "phone": None}
    return {
        "id": staff.id,
        "display_name": f"{staff.first_name or ''} {staff.last_name or ''}".strip() or "N/A",
        "email": staff.email,
        "phone": staff.phone,
    }


def assignable_teachers() -> list[dict[str, Any]]:
    rows = TeacherStaff.query.filter(TeacherStaff.is_deleted.is_(False)).order_by(
        TeacherStaff.last_name, TeacherStaff.first_name
    ).all()
    out = []
    for t in rows:
        if not _staff_can_be_assigned_to_classes(t):
            continue
        out.append(
            {
                "id": t.id,
                "first_name": t.first_name or "",
                "last_name": t.last_name or "",
                "display_name": f"{t.first_name or ''} {t.last_name or ''}".strip(),
            }
        )
    return out


def _enrollment_count(class_id: int) -> int:
    return Enrollment.query.filter_by(class_id=class_id, is_active=True).count()


def _assignment_count(class_id: int) -> int:
    individual = Assignment.query.filter_by(class_id=class_id).count()
    try:
        group = GroupAssignment.query.filter_by(class_id=class_id).count()
    except Exception:
        group = 0
    return individual + group


def serialize_student_brief(student: Student) -> dict[str, Any]:
    import re

    photo = getattr(student, "photo_filename", None)
    safe_photo = photo if photo and re.match(r"^[a-zA-Z0-9._-]+$", str(photo)) else None
    return {
        "id": student.id,
        "student_id": getattr(student, "student_id", None) or None,
        "first_name": student.first_name or "",
        "last_name": student.last_name or "",
        "display_name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
        "grade_level": student.grade_level,
        "initial": f"{(student.first_name or '?')[0]}{(student.last_name or '?')[0]}".upper(),
        "photo_url": f"/static/uploads/{safe_photo}" if safe_photo else None,
    }


def _subject_has_standards(subject: str | None) -> bool:
    subj = (subject or "").lower()
    return any(k in subj for k in ("math", "language", "reading", "english", "ela", "literacy"))


def _standards_flags(class_info: Class) -> dict[str, bool]:
    from flask import current_app

    levels = class_info.get_grade_levels() if hasattr(class_info, "get_grade_levels") else []
    eligible = _subject_has_standards(class_info.subject)
    g1 = 1 in (levels or []) and eligible
    g3 = 3 in (levels or []) and eligible
    return {
        "grade1_standards": g1 and "teacher.grade1_standards.grade1_standards_editor" in current_app.view_functions,
        "grade3_standards": g3 and "teacher.grade3_standards.grade3_standards_editor" in current_app.view_functions,
    }


def _class_management_links(class_id: int) -> dict[str, str]:
    from flask import url_for

    return {
        "add_assignment": url_for("management.assignment_type_selector", class_id=class_id),
        "attendance": url_for("management.unified_attendance"),
        "manage_roster": f"/app/management/classes/{class_id}/roster",
        "grade1_standards": url_for("teacher.grade1_standards.grade1_standards_editor", class_id=class_id),
        "grade3_standards": url_for("teacher.grade3_standards.grade3_standards_editor", class_id=class_id),
        "assistant_approvals": url_for("teacher.assignments.pending_assistant_assignments", class_id=class_id),
        "view_grades": f"/app/management/classes/{class_id}/grades",
        "edit_class": f"/app/management/classes/{class_id}/edit",
        "analytics": url_for("management.admin_class_analytics", class_id=class_id),
        "feedback_360": url_for("management.admin_class_360_feedback", class_id=class_id),
        "reflection_journals": url_for("management.admin_class_reflection_journals", class_id=class_id),
        "conflicts": url_for("management.admin_class_conflicts", class_id=class_id),
        "assignments_and_grades": url_for("management.assignments_and_grades", class_id=class_id),
        "manage_groups": url_for("management.admin_class_groups", class_id=class_id),
        "deadline_reminders": url_for("management.admin_class_deadline_reminders", class_id=class_id),
        "class_assignments": f"/management/assignments/class/{class_id}",
        "take_attendance": url_for("management.take_class_attendance", class_id=class_id),
    }


def query_class_detail(class_id: int) -> dict[str, Any]:
    from management_routes.student_assistant_utils import count_pending_assistant_proposals_for_class

    class_info = Class.query.get_or_404(class_id)
    teacher = TeacherStaff.query.get(class_info.teacher_id) if class_info.teacher_id else None
    enrolled = (
        db.session.query(Student)
        .join(Enrollment)
        .filter(Enrollment.class_id == class_id, Enrollment.is_active.is_(True), Student.is_deleted.is_(False))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    assignment_count = _assignment_count(class_id)
    school_year = class_info.school_year
    item = serialize_class_list_item(
        class_info,
        enrollment_count=len(enrolled),
        assignment_count=assignment_count,
    )
    room = class_info.room_number or None
    schedule = class_info.schedule or None
    return {
        "class": {
            **item,
            "description": class_info.description,
            "max_students": class_info.max_students,
            "term_type": class_info.term_type,
            "term_value": class_info.term_value,
            "school_year_name": school_year.name if school_year else None,
            "room_display": room or "N/A",
            "schedule_display": schedule or "TBD",
        },
        "teacher": _teacher_display(teacher),
        "enrolled_students": [serialize_student_brief(s) for s in enrolled],
        "stats": {
            "students": len(enrolled),
            "assignments": assignment_count,
            "teacher_count": 1 if teacher else 0,
            "grade_levels_display": class_info.get_grade_levels_display() or "All",
        },
        "pending_assistant_count": count_pending_assistant_proposals_for_class(class_id),
        "features": _standards_flags(class_info),
        "links": _class_management_links(class_id),
    }


def query_class_edit_form(class_id: int) -> dict[str, Any]:
    class_info = Class.query.get_or_404(class_id)
    detail = query_class_detail(class_id)
    substitute_ids = [t.id for t in class_info.substitute_teachers]
    additional_ids = [t.id for t in class_info.additional_teachers]
    assistant_ids = [
        sa.student_id
        for sa in StudentAssistant.query.filter_by(class_id=class_id).all()
        if sa.student_id
    ]
    eligible_assistants = []
    if user_can_manage_student_assistants(current_user):
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        enrolled_ids = {e.student_id for e in enrollments}
        pool = students_in_school_year_for_assistant_pool(class_info.school_year_id)
        eligible_assistants = [
            serialize_student_brief(s)
            for s in filter_eligible_assistant_candidates(class_info, pool, enrolled_ids)
        ]
    return {
        **detail,
        "form": {
            "substitute_teacher_ids": substitute_ids,
            "additional_teacher_ids": additional_ids,
            "student_assistant_ids": assistant_ids,
            "is_active": bool(class_info.is_active),
        },
        "teachers": assignable_teachers(),
        "eligible_assistants": eligible_assistants,
        "max_assistants_per_class": MAX_ASSISTANTS_PER_CLASS,
        "can_manage_assistants": user_can_manage_student_assistants(current_user),
    }


def query_class_roster(class_id: int) -> dict[str, Any]:
    class_info = Class.query.get_or_404(class_id)
    enrolled_ids = {
        e.student_id
        for e in Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    }
    all_students = (
        Student.query.filter(Student.is_deleted.is_(False))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    enrolled = [s for s in all_students if s.id in enrolled_ids]
    available = [s for s in all_students if s.id not in enrolled_ids]
    return {
        "class": serialize_class_list_item(
            class_info,
            enrollment_count=len(enrolled),
            assignment_count=_assignment_count(class_id),
        ),
        "enrolled_students": [serialize_student_brief(s) for s in enrolled],
        "available_students": [serialize_student_brief(s) for s in available],
    }


def mutate_class_roster(class_id: int, action: str, student_ids: list[int]) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    if action == "add":
        added = 0
        for sid in student_ids:
            stu = Student.query.get(sid)
            if not stu or getattr(stu, "is_deleted", False):
                continue
            exists = Enrollment.query.filter_by(
                class_id=class_id, student_id=sid, is_active=True
            ).first()
            if exists:
                continue
            db.session.add(Enrollment(student_id=sid, class_id=class_id, is_active=True))
            added += 1
        if added:
            db.session.commit()
            try_provision_class_google_group(class_id)
            from management_routes.late_enrollment_utils import void_assignments_for_late_enrollment

            for sid in student_ids:
                try:
                    void_assignments_for_late_enrollment(int(sid), class_id)
                except Exception:
                    pass
            return {"success": True, "message": f"{added} student(s) added to class.", "added": added}
        return {"success": False, "message": "Selected students are already enrolled or invalid.", "added": 0}
    if action == "remove":
        removed = 0
        for sid in student_ids:
            enrollment = Enrollment.query.filter_by(
                class_id=class_id, student_id=sid, is_active=True
            ).first()
            if enrollment:
                enrollment.is_active = False
                enrollment.dropped_at = datetime.utcnow()
                removed += 1
        if removed:
            db.session.commit()
            try_provision_class_google_group(class_id)
            return {"success": True, "message": f"Removed {removed} student(s) from this class.", "removed": removed}
        return {"success": False, "message": "No matching enrollments to remove.", "removed": 0}
    return {"success": False, "message": "Invalid roster action."}


def _parse_schedule_text(class_id: int, schedule_text: str | None, room_number: str | None) -> None:
    from models import ClassSchedule

    for schedule in ClassSchedule.query.filter_by(class_id=class_id).all():
        db.session.delete(schedule)
    if not schedule_text:
        return
    day_mapping = {
        "mon": 0, "monday": 0, "tue": 1, "tuesday": 1, "wed": 2, "wednesday": 2,
        "thu": 3, "thursday": 3, "fri": 4, "friday": 4, "sat": 5, "saturday": 5,
        "sun": 6, "sunday": 6,
    }
    for entry in [s.strip() for s in schedule_text.split(",")]:
        if not entry:
            continue
        try:
            parts = entry.split()
            if len(parts) < 2:
                continue
            day_of_week = day_mapping.get(parts[0].lower())
            if day_of_week is None:
                continue
            time_str = " ".join(parts[1:])
            if "-" in time_str:
                start_str, end_str = [x.strip() for x in time_str.split("-", 1)]
            else:
                start_str = time_str.strip()
                start_time_obj = datetime.strptime(start_str, "%I:%M %p").time()
                end_str = (datetime.combine(datetime.today(), start_time_obj) + timedelta(hours=1)).strftime("%I:%M %p")
            start_time = datetime.strptime(start_str, "%I:%M %p").time()
            end_time = datetime.strptime(end_str, "%I:%M %p").time()
            db.session.add(
                ClassSchedule(
                    class_id=class_id,
                    day_of_week=day_of_week,
                    start_time=start_time,
                    end_time=end_time,
                    room=room_number,
                )
            )
        except Exception:
            continue


def create_class_from_body(body: dict[str, Any]) -> dict[str, Any]:
    name = (body.get("name") or "").strip()
    subject = (body.get("subject") or "").strip()
    teacher_id = body.get("teacher_id")
    if not name or not subject or not teacher_id:
        return {"success": False, "message": "Class name, subject, and primary teacher are required."}
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not current_school_year:
        return {"success": False, "message": "Cannot create class: No active school year."}
    try:
        new_class = Class(
            name=name,
            subject=subject,
            teacher_id=int(teacher_id),
            school_year_id=current_school_year.id,
            room_number=(body.get("room_number") or "").strip() or None,
            schedule=(body.get("schedule") or "").strip() or None,
            term_type=(body.get("term_type") or "full_year").strip() or "full_year",
            term_value=(body.get("term_value") or "").strip() or None,
            max_students=int(body.get("max_students") or 30),
            description=(body.get("description") or "").strip() or None,
            is_active=True,
        )
        db.session.add(new_class)
        db.session.flush()
        grade_levels = body.get("grade_levels") or []
        if grade_levels:
            new_class.set_grade_levels([int(g) for g in grade_levels if str(g).isdigit()])
        for tid in body.get("substitute_teacher_ids") or []:
            teacher = TeacherStaff.query.get(int(tid))
            if teacher:
                new_class.substitute_teachers.append(teacher)
        for tid in body.get("additional_teacher_ids") or []:
            teacher = TeacherStaff.query.get(int(tid))
            if teacher:
                new_class.additional_teachers.append(teacher)
        db.session.commit()
        try_provision_class_google_group(new_class.id)
        return {
            "success": True,
            "message": f'Class "{name}" created successfully.',
            "class_id": new_class.id,
            "redirect": f"/app/management/classes/{new_class.id}",
        }
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("create_class_from_body failed")
        return {"success": False, "message": f"Error creating class: {exc}"}


def update_class_from_body(class_id: int, body: dict[str, Any]) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    try:
        class_obj.name = (body.get("name") or "").strip()
        class_obj.subject = (body.get("subject") or "").strip()
        class_obj.teacher_id = int(body.get("teacher_id"))
        class_obj.room_number = (body.get("room_number") or "").strip() or None
        schedule_text = (body.get("schedule") or "").strip() or None
        class_obj.schedule = schedule_text
        term_type = (body.get("term_type") or "full_year").strip() or "full_year"
        term_value = (body.get("term_value") or "").strip() or None
        if term_type not in ("full_year", "semester", "quarter"):
            term_type = "full_year"
        if term_type == "full_year":
            term_value = None
        class_obj.term_type = term_type
        class_obj.term_value = term_value
        class_obj.max_students = int(body.get("max_students") or 30)
        class_obj.description = (body.get("description") or "").strip() or None
        class_obj.is_active = bool(body.get("is_active", True))
        grade_levels = body.get("grade_levels") or []
        class_obj.set_grade_levels([int(g) for g in grade_levels if str(g).isdigit()])
        class_obj.substitute_teachers = []
        class_obj.additional_teachers = []
        for tid in body.get("substitute_teacher_ids") or []:
            teacher = TeacherStaff.query.get(int(tid))
            if teacher:
                class_obj.substitute_teachers.append(teacher)
        for tid in body.get("additional_teacher_ids") or []:
            teacher = TeacherStaff.query.get(int(tid))
            if teacher:
                class_obj.additional_teachers.append(teacher)
        _parse_schedule_text(class_id, schedule_text, class_obj.room_number)
        if user_can_manage_student_assistants(current_user):
            raw_ids = body.get("student_assistant_ids") or []
            new_ids = []
            for x in raw_ids:
                if x and str(x).isdigit():
                    sid = int(x)
                    if sid not in new_ids:
                        new_ids.append(sid)
            if len(new_ids) > MAX_ASSISTANTS_PER_CLASS:
                return {"success": False, "message": f"At most {MAX_ASSISTANTS_PER_CLASS} student assistants per class."}
            enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
            enrolled_ids = {e.student_id for e in enrollments}
            for sid in new_ids:
                stu = Student.query.get(sid)
                if not stu or not is_eligible_student_assistant_candidate(class_obj, stu, enrolled_ids):
                    return {"success": False, "message": "Invalid student selected for assistant."}
                if count_assistant_classes_for_student_excluding(sid, exclude_class_id=class_id) >= MAX_CLASSES_PER_ASSISTANT:
                    return {"success": False, "message": "Student assistant is already assigned to the maximum number of classes."}
            StudentAssistant.query.filter_by(class_id=class_id).delete()
            for sid in new_ids:
                db.session.add(
                    StudentAssistant(class_id=class_id, student_id=sid, assigned_by_user_id=current_user.id)
                )
        db.session.commit()
        try_provision_class_google_group(class_id)
        return {"success": True, "message": f'Class "{class_obj.name}" updated successfully.', "class_id": class_id}
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("update_class_from_body failed")
        return {"success": False, "message": f"Error updating class: {exc}"}


def query_class_grades(class_id: int, view_mode: str = "table") -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = [
        e.student for e in enrollments if e.student and not getattr(e.student, "is_deleted", False)
    ]
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    try:
        group_assignments = GroupAssignment.query.filter_by(class_id=class_id).order_by(GroupAssignment.due_date.desc()).all()
    except Exception:
        group_assignments = []
    columns = []
    for a in assignments:
        columns.append(
            {
                "key": str(a.id),
                "id": a.id,
                "title": a.title,
                "type": "individual",
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "status": a.status,
            }
        )
    for ga in group_assignments:
        columns.append(
            {
                "key": f"group_{ga.id}",
                "id": ga.id,
                "title": ga.title,
                "type": "group",
                "due_date": ga.due_date.isoformat() if ga.due_date else None,
                "status": ga.status,
            }
        )
    rows = []
    student_averages: dict[int, Any] = {}
    for student in enrolled_students:
        grades: dict[str, Any] = {}
        valid_numeric: list[float] = []
        for assignment in assignments:
            if assignment.status == "Voided":
                continue
            grade = (
                Grade.query.filter_by(student_id=student.id, assignment_id=assignment.id)
                .order_by(Grade.graded_at.desc())
                .first()
            )
            key = str(assignment.id)
            if grade:
                try:
                    grade_data = json.loads(grade.grade_data)
                    points = get_points_earned(grade_data)
                    total = assignment.total_points or 100.0
                    display = round((float(points) / total * 100), 1) if points is not None and total > 0 else "N/A"
                except Exception:
                    display = "N/A"
                grades[key] = {"grade": display, "type": "individual"}
                if isinstance(display, (int, float)):
                    valid_numeric.append(float(display))
            else:
                grades[key] = {"grade": "Not Graded", "type": "individual"}
        for ga in group_assignments:
            if ga.status == "Voided":
                continue
            key = f"group_{ga.id}"
            gg = GroupGrade.query.filter_by(student_id=student.id, group_assignment_id=ga.id).first()
            if gg:
                try:
                    grade_data = json.loads(gg.grade_data) if gg.grade_data else {}
                    points = get_points_earned(grade_data)
                    total = ga.total_points or 100.0
                    display = round((float(points) / total * 100), 1) if points is not None and total > 0 else "N/A"
                except Exception:
                    display = "N/A"
                grades[key] = {"grade": display, "type": "group"}
                if isinstance(display, (int, float)):
                    valid_numeric.append(float(display))
            else:
                grades[key] = {"grade": "Not Graded", "type": "group"}
        student_averages[student.id] = round(sum(valid_numeric) / len(valid_numeric), 2) if valid_numeric else "N/A"
        rows.append(
            {
                "student": serialize_student_brief(student),
                "grades": grades,
                "average": student_averages[student.id],
            }
        )
    return {
        "class": serialize_class_list_item(
            class_obj,
            enrollment_count=len(enrolled_students),
            assignment_count=len(columns),
        ),
        "view_mode": view_mode,
        "columns": columns,
        "rows": rows,
    }


def google_classroom_options(class_id: int) -> dict[str, Any]:
    class_to_link = Class.query.get_or_404(class_id)
    if not current_user.google_refresh_token:
        return {"success": False, "message": "Connect your Google account first.", "settings_url": "/teacher/settings"}
    from google_classroom_service import get_google_service

    service = get_google_service(current_user)
    if not service:
        return {"success": False, "message": "Could not connect to Google."}
    results = service.courses().list(teacherId="me", courseStates=["ACTIVE"]).execute()
    courses = results.get("courses", [])
    return {
        "success": True,
        "class_id": class_id,
        "items": [
            {"id": c.get("id"), "name": c.get("name"), "section": c.get("section"), "room": c.get("room")}
            for c in courses
        ],
        "class_name": class_to_link.name,
    }


def google_classroom_action(class_id: int, action: str, google_classroom_id: str | None = None) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    if action == "unlink":
        if not class_obj.google_classroom_id:
            return {"success": False, "message": "This class is not linked to Google Classroom."}
        class_obj.google_classroom_id = None
        db.session.commit()
        return {"success": True, "message": "Successfully unlinked from Google Classroom."}
    if not current_user.google_refresh_token:
        return {"success": False, "message": "Connect your Google account first.", "settings_url": "/teacher/settings"}
    from google_classroom_service import get_google_service

    service = get_google_service(current_user)
    if not service:
        return {"success": False, "message": "Could not connect to Google."}
    if action == "create":
        course = {
            "name": class_obj.name,
            "section": class_obj.subject or "",
            "descriptionHeading": f"Class: {class_obj.name}",
            "description": class_obj.description or f"Welcome to {class_obj.name}",
            "room": class_obj.room_number or "",
            "ownerId": "me",
            "courseState": "ACTIVE",
        }
        created = service.courses().create(body=course).execute()
        class_obj.google_classroom_id = created.get("id")
        db.session.commit()
        return {"success": True, "message": "Google Classroom created and linked.", "google_classroom_id": class_obj.google_classroom_id}
    if action == "link" and google_classroom_id:
        class_obj.google_classroom_id = google_classroom_id
        db.session.commit()
        return {"success": True, "message": "Google Classroom linked.", "google_classroom_id": google_classroom_id}
    return {"success": False, "message": "Invalid Google Classroom action."}


def query_core_setup_form() -> dict[str, Any]:
    from utils.core_class_catalog import (
        SETUP_GRADE_LEVELS,
        catalog_entries_for_grade,
        class_name_for_grade,
        grade_label,
        guide_by_grade,
        setup_key_for_entry,
    )
    from services.school_year_class_setup import teacher_assignment_key

    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    active = SchoolYear.query.filter_by(is_active=True).first()
    grades = []
    for g in SETUP_GRADE_LEVELS:
        entries = []
        for i, entry in enumerate(catalog_entries_for_grade(g)):
            entries.append(
                {
                    "index": i,
                    "subject": entry.get("subject"),
                    "class_name": class_name_for_grade(g, entry),
                    "setup_key": setup_key_for_entry(entry),
                    "assignment_key": teacher_assignment_key(g, setup_key_for_entry(entry)),
                }
            )
        grades.append({"grade_level": g, "label": grade_label(g), "entries": entries})
    return {
        "school_years": [{"id": y.id, "name": y.name, "is_active": bool(y.is_active)} for y in school_years],
        "default_school_year_id": active.id if active else None,
        "setup_grade_levels": SETUP_GRADE_LEVELS,
        "grades": grades,
        "teachers": assignable_teachers(),
        "guide": guide_by_grade(),
    }


def parse_core_setup_body(body: dict[str, Any]) -> tuple[int | None, list[int], dict[str, int]]:
    from services.school_year_class_setup import teacher_assignment_key
    from utils.core_class_catalog import catalog_entries_for_grade, setup_key_for_entry

    school_year_id = body.get("school_year_id")
    grade_levels = [int(g) for g in (body.get("grade_levels") or []) if str(g).isdigit()]
    assignments: dict[str, int] = {}
    raw = body.get("teacher_assignments") or {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if v:
                assignments[str(k)] = int(v)
    grade_defaults = body.get("grade_default_teachers") or {}
    for g in grade_levels:
        default_tid = grade_defaults.get(str(g)) or grade_defaults.get(g)
        for i, entry in enumerate(catalog_entries_for_grade(g)):
            key = teacher_assignment_key(g, setup_key_for_entry(entry))
            if key not in assignments and default_tid:
                assignments[key] = int(default_tid)
            per_key = f"{g}:{i}"
            if per_key in (body.get("per_subject_teachers") or {}):
                assignments[key] = int(body["per_subject_teachers"][per_key])
    return int(school_year_id) if school_year_id else None, grade_levels, assignments


def core_setup_preview(body: dict[str, Any]) -> dict[str, Any]:
    from services.school_year_class_setup import preview_core_class_setup

    school_year_id, grade_levels, teacher_assignments = parse_core_setup_body(body)
    if not school_year_id:
        return {"success": False, "message": "Select a school year.", "preview": None}
    if not grade_levels:
        return {"success": False, "message": "Select at least one grade level.", "preview": None}
    preview = preview_core_class_setup(school_year_id, grade_levels, teacher_assignments)
    return {"success": True, "preview": preview}


def core_setup_create(body: dict[str, Any]) -> dict[str, Any]:
    from services.school_year_class_setup import run_core_class_setup

    school_year_id, grade_levels, teacher_assignments = parse_core_setup_body(body)
    if not school_year_id or not grade_levels:
        return {"success": False, "message": "School year and grade levels are required."}
    result = run_core_class_setup(school_year_id, grade_levels, teacher_assignments)
    if result.get("errors"):
        return {"success": False, "message": "; ".join(result["errors"]), "result": result}
    return {
        "success": True,
        "message": f"Created {result.get('created_count', 0)} core class(es).",
        "result": result,
        "redirect": f"/app/management/classes?school_year_id={school_year_id}",
    }

