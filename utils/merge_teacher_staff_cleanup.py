"""
After consolidating two User rows, retire the duplicate TeacherStaff profile.

Reassigns FK references from merge_staff_id → keep_staff_id, then soft-deletes the merge row
so it no longer appears in the staff directory without a login.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from extensions import db


def _association_delete_duplicates(table_name: str, merge_id: int, keep_id: int) -> None:
    """Remove merge rows that would duplicate (class_id, keep_id) after UPDATE."""
    db.session.execute(
        text(
            f"""
            DELETE FROM {table_name}
            WHERE teacher_id = :merge_id
              AND class_id IN (
                SELECT class_id FROM {table_name} WHERE teacher_id = :keep_id
              )
            """
        ),
        {"merge_id": merge_id, "keep_id": keep_id},
    )


def _association_reassign(table_name: str, merge_id: int, keep_id: int) -> None:
    _association_delete_duplicates(table_name, merge_id, keep_id)
    db.session.execute(
        text(f"UPDATE {table_name} SET teacher_id = :keep_id WHERE teacher_id = :merge_id"),
        {"merge_id": merge_id, "keep_id": keep_id},
    )


def reassign_teacher_staff_foreign_keys(merge_staff_id: int, keep_staff_id: int) -> None:
    """Update models that reference teacher_staff.id (User rows handled separately)."""
    from models import (
        AdminAuditLog,
        AssignmentExtension,
        AssignmentRedo,
        AssignmentReopening,
        Attendance,
        Class,
        ExtensionRequest,
        GroupAssignmentExtension,
        GroupGrade,
        GroupTemplate,
        RedoRequest,
        StudentGroup,
        Submission,
    )

    pairs = [
        (Class, "teacher_id"),
        (Submission, "marked_by"),
        (Attendance, "teacher_id"),
        (AdminAuditLog, "teacher_staff_id"),
        (AssignmentRedo, "granted_by"),
        (StudentGroup, "created_by"),
        (GroupGrade, "graded_by"),
        (GroupTemplate, "created_by"),
        (AssignmentExtension, "granted_by"),
        (GroupAssignmentExtension, "granted_by"),
        (AssignmentReopening, "reopened_by"),
        (ExtensionRequest, "reviewed_by"),
        (RedoRequest, "reviewed_by"),
    ]
    for model, col in pairs:
        colattr = getattr(model, col)
        model.query.filter(colattr == merge_staff_id).update(
            {col: keep_staff_id}, synchronize_session=False
        )

    _association_reassign("class_additional_teachers", merge_staff_id, keep_staff_id)
    _association_reassign("class_substitute_teachers", merge_staff_id, keep_staff_id)


def soft_delete_merged_teacher_staff_profile(merge_staff_id: int, keep_staff_id: int) -> None:
    from models import TeacherStaff

    ts = db.session.get(TeacherStaff, merge_staff_id)
    if not ts or merge_staff_id == keep_staff_id:
        return
    ts.is_deleted = True
    ts.deleted_at = datetime.utcnow()
    ts.is_active = False
    ts.removal_note = (
        f"Duplicate profile merged into teacher_staff id {keep_staff_id}; login consolidated."
    )


def consolidate_duplicate_teacher_staff_rows(merge_staff_id: int | None, keep_staff_id: int | None) -> None:
    """
    When two User accounts pointed at different TeacherStaff rows for the same person:
    point references at keep_staff_id and soft-delete merge_staff_id.
    """
    if not merge_staff_id or not keep_staff_id or merge_staff_id == keep_staff_id:
        return
    reassign_teacher_staff_foreign_keys(merge_staff_id, keep_staff_id)
    soft_delete_merged_teacher_staff_profile(merge_staff_id, keep_staff_id)
