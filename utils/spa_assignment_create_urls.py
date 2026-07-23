"""Shared redirect targets after assignment creation in the React SPA."""

from __future__ import annotations


def assignment_create_success_redirect(class_id: int) -> str:
    """Return the SPA path to open after creating an assignment for a class."""
    from utils.spa_teacher_urls import user_should_use_spa_teacher_shell
    from utils.spa_management_urls import user_should_use_spa_management_shell

    if user_should_use_spa_teacher_shell() and not user_should_use_spa_management_shell():
        return f"/app/teacher/assignments-and-grades/{class_id}"
    return f"/app/management/assignments/{class_id}"


def assignment_create_hub_redirect(class_id: int | None = None) -> str:
    from utils.spa_teacher_urls import user_should_use_spa_teacher_shell
    from utils.spa_management_urls import user_should_use_spa_management_shell

    if user_should_use_spa_teacher_shell() and not user_should_use_spa_management_shell():
        if class_id:
            return f"/app/teacher/assignments-and-grades/{class_id}"
        return "/app/teacher/assignments-and-grades"
    if class_id:
        return f"/app/management/assignments/{class_id}"
    return "/app/management/assignments"
