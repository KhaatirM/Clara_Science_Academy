"""Student group management payloads and mutations for the React management SPA."""

from __future__ import annotations

from typing import Any

from flask_login import current_user

from extensions import db
from models import (
    Class,
    CollaborationMetrics,
    ConflictParticipant,
    ConflictResolution,
    DraftFeedback,
    DraftSubmission,
    Enrollment,
    GroupAssignment,
    GroupConflict,
    GroupContract,
    GroupGrade,
    GroupProgress,
    GroupQuizAnswer,
    GroupSubmission,
    IndividualContribution,
    PeerEvaluation,
    PeerReview,
    ReflectionJournal,
    Student,
    StudentGroup,
    StudentGroupMember,
    TimeTracking,
)

from management_routes.class_spa_helpers import serialize_student_brief


def _group_member_rows(group_id: int) -> list[dict[str, Any]]:
    members = StudentGroupMember.query.filter_by(group_id=group_id).all()
    rows = []
    for m in members:
        if not m.student:
            continue
        rows.append(
            {
                "student_id": m.student_id,
                "display_name": f"{m.student.first_name or ''} {m.student.last_name or ''}".strip(),
                "is_leader": bool(m.is_leader),
            }
        )
    return rows


def query_class_groups(class_id: int) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).order_by(StudentGroup.name).all()
    enrolled = (
        db.session.query(Student)
        .join(Enrollment)
        .filter(Enrollment.class_id == class_id, Enrollment.is_active.is_(True), Student.is_deleted.is_(False))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    payload_groups = []
    member_counts = []
    for group in groups:
        members = _group_member_rows(group.id)
        member_counts.append(len(members))
        payload_groups.append(
            {
                "id": group.id,
                "name": group.name,
                "description": group.description or "",
                "max_students": group.max_students,
                "member_count": len(members),
                "members": members,
            }
        )
    total_groups = len(payload_groups)
    total_students = len(enrolled)
    avg_size = round(sum(member_counts) / total_groups, 1) if total_groups else 0
    return {
        "class": {
            "id": class_obj.id,
            "name": class_obj.name,
            "subject": class_obj.subject,
            "grade_levels": class_obj.get_grade_levels() or [],
        },
        "groups": payload_groups,
        "enrolled_students": [serialize_student_brief(s) for s in enrolled],
        "stats": {
            "total_groups": total_groups,
            "total_students": total_students,
            "avg_group_size": avg_size,
        },
    }


def _max_group_size(class_id: int) -> int | None:
    group_assignments = GroupAssignment.query.filter_by(class_id=class_id).all()
    limits = [ga.group_size_max for ga in group_assignments if ga.group_size_max is not None]
    return min(limits) if limits else None


def _delete_student_group(group_id: int) -> None:
    GroupGrade.query.filter_by(group_id=group_id).update({GroupGrade.group_id: None})
    GroupSubmission.query.filter_by(group_id=group_id).update({GroupSubmission.group_id: None})
    GroupQuizAnswer.query.filter_by(group_id=group_id).update({GroupQuizAnswer.group_id: None})
    TimeTracking.query.filter_by(group_id=group_id).update({TimeTracking.group_id: None})

    conflict_ids = [c.id for c in GroupConflict.query.filter_by(group_id=group_id).all()]
    if conflict_ids:
        ConflictResolution.query.filter(ConflictResolution.conflict_id.in_(conflict_ids)).delete(
            synchronize_session=False
        )
        ConflictParticipant.query.filter(ConflictParticipant.conflict_id.in_(conflict_ids)).delete(
            synchronize_session=False
        )
    GroupConflict.query.filter_by(group_id=group_id).delete()

    draft_ids = [d.id for d in DraftSubmission.query.filter_by(group_id=group_id).all()]
    if draft_ids:
        DraftFeedback.query.filter(DraftFeedback.draft_submission_id.in_(draft_ids)).delete(synchronize_session=False)
    DraftSubmission.query.filter_by(group_id=group_id).delete()

    PeerEvaluation.query.filter_by(group_id=group_id).delete(synchronize_session=False)
    GroupContract.query.filter_by(group_id=group_id).delete(synchronize_session=False)
    ReflectionJournal.query.filter_by(group_id=group_id).delete(synchronize_session=False)
    GroupProgress.query.filter_by(group_id=group_id).delete(synchronize_session=False)
    PeerReview.query.filter_by(group_id=group_id).delete(synchronize_session=False)
    IndividualContribution.query.filter_by(group_id=group_id).delete(synchronize_session=False)
    CollaborationMetrics.query.filter_by(group_id=group_id).delete(synchronize_session=False)
    StudentGroupMember.query.filter_by(group_id=group_id).delete()

    group = StudentGroup.query.get_or_404(group_id)
    db.session.delete(group)


def mutate_class_groups(class_id: int, body: dict[str, Any]) -> dict[str, Any]:
    class_obj = Class.query.get_or_404(class_id)
    action = (body.get("action") or "").strip()

    if action == "create":
        name = (body.get("name") or "").strip()
        if not name:
            return {"success": False, "message": "Group name is required."}
        staff_id = getattr(current_user, "teacher_staff_id", None) or class_obj.teacher_id
        if not staff_id:
            return {"success": False, "message": "No teacher is assigned to this class."}
        group = StudentGroup(
            name=name,
            description=(body.get("description") or "").strip() or None,
            class_id=class_id,
            max_students=body.get("max_students"),
            created_by=staff_id,
            is_active=True,
        )
        db.session.add(group)
        db.session.commit()
        return {"success": True, "message": "Group created.", "group_id": group.id}

    group_id = body.get("group_id")
    if not group_id:
        return {"success": False, "message": "Group is required."}
    group = StudentGroup.query.filter_by(id=int(group_id), class_id=class_id, is_active=True).first()
    if not group:
        return {"success": False, "message": "Group not found."}

    if action == "update":
        name = (body.get("name") or "").strip()
        if name:
            group.name = name
        if "description" in body:
            group.description = (body.get("description") or "").strip() or None
        if "max_students" in body:
            group.max_students = body.get("max_students")
        db.session.commit()
        return {"success": True, "message": "Group updated."}

    if action == "delete":
        try:
            _delete_student_group(group.id)
            db.session.commit()
            return {
                "success": True,
                "message": "Group deleted. Existing grades for that group were kept per student.",
            }
        except Exception:
            db.session.rollback()
            return {"success": False, "message": "Could not delete group. Please try again."}

    if action == "add_members":
        student_ids = [int(x) for x in (body.get("student_ids") or []) if str(x).isdigit()]
        if not student_ids:
            return {"success": False, "message": "Select at least one student."}
        current_members = StudentGroupMember.query.filter_by(group_id=group.id).all()
        current_member_ids = {m.student_id for m in current_members}
        max_allowed = _max_group_size(class_id)
        new_count = sum(1 for sid in student_ids if sid not in current_member_ids)
        if max_allowed is not None and len(current_members) + new_count > max_allowed:
            return {
                "success": False,
                "message": f"Group size cannot exceed {max_allowed} students.",
            }
        leader_id = body.get("leader_id")
        leader_id = int(leader_id) if leader_id else None
        added = 0
        for student_id in student_ids:
            if student_id in current_member_ids:
                if leader_id == student_id:
                    member = StudentGroupMember.query.filter_by(group_id=group.id, student_id=student_id).first()
                    if member and not member.is_leader:
                        member.is_leader = True
                        added += 1
                continue
            db.session.add(
                StudentGroupMember(
                    group_id=group.id,
                    student_id=student_id,
                    is_leader=leader_id == student_id,
                )
            )
            added += 1
        if leader_id:
            StudentGroupMember.query.filter_by(group_id=group.id).filter(
                StudentGroupMember.student_id != leader_id
            ).update({"is_leader": False}, synchronize_session=False)
        db.session.commit()
        return {"success": True, "message": f"{added} student(s) added to group." if added else "No changes made."}

    if action == "remove_member":
        student_id = body.get("student_id")
        if not student_id:
            return {"success": False, "message": "Student is required."}
        member = StudentGroupMember.query.filter_by(group_id=group.id, student_id=int(student_id)).first()
        if not member:
            return {"success": False, "message": "Student is not in this group."}
        db.session.delete(member)
        db.session.commit()
        return {"success": True, "message": "Student removed from group."}

    if action == "set_leader":
        student_id = body.get("student_id")
        if not student_id:
            return {"success": False, "message": "Student is required."}
        member = StudentGroupMember.query.filter_by(group_id=group.id, student_id=int(student_id)).first()
        if not member:
            return {"success": False, "message": "Student is not in this group."}
        StudentGroupMember.query.filter_by(group_id=group.id).update({"is_leader": False})
        member.is_leader = True
        db.session.commit()
        return {"success": True, "message": "Group leader updated."}

    return {"success": False, "message": "Invalid action."}
