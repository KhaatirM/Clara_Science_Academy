"""
After consolidating two User rows, retire the duplicate TeacherStaff profile.

Reassigns FK references from merge_staff_id → keep_staff_id, then soft-deletes the merge row
so it no longer appears in the staff directory without a login.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from extensions import db


def _csv_parts(s: str | None) -> list[str]:
    if not s or not str(s).strip():
        return []
    out: list[str] = []
    for chunk in str(s).split(","):
        p = chunk.strip()
        if p:
            out.append(p)
    return out


def _merge_truncated_csv(
    keep_val: str | None, merge_val: str | None, max_len: int = 100
) -> str | None:
    """Union comma-separated labels (order: keep first, then merge-only), truncate for VARCHAR(max_len)."""
    combined: list[str] = []
    seen: set[str] = set()
    for part in _csv_parts(keep_val) + _csv_parts(merge_val):
        if part not in seen:
            seen.add(part)
            combined.append(part)
    if not combined:
        return None
    s = ", ".join(combined)
    if len(s) > max_len:
        s = s[: max_len - 3].rstrip(", ") + "..."
    return s


def merge_teacher_staff_profile_lists(merge_staff_id: int, keep_staff_id: int) -> None:
    """
    Copy union of department and assigned_role from merge profile onto keep profile
    so directory / HR fields show everything on the surviving TeacherStaff row.
    """
    from models import TeacherStaff

    keep = db.session.get(TeacherStaff, keep_staff_id)
    merge = db.session.get(TeacherStaff, merge_staff_id)
    if not keep or not merge or merge_staff_id == keep_staff_id:
        return

    dept = _merge_truncated_csv(keep.department, merge.department, max_len=100)
    if dept is not None:
        keep.department = dept

    roles = _merge_truncated_csv(keep.assigned_role, merge.assigned_role, max_len=100)
    if roles is not None:
        keep.assigned_role = roles


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
    merge_teacher_staff_profile_lists(merge_staff_id, keep_staff_id)
    reassign_teacher_staff_foreign_keys(merge_staff_id, keep_staff_id)
    soft_delete_merged_teacher_staff_profile(merge_staff_id, keep_staff_id)
