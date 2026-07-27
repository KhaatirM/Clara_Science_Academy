"""Teacher assignment view/grade workspace APIs for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import teacher_required
from management_routes.assignment_workspace_spa_helpers import (
    _assignment_action_links,
    query_group_assignment_grade,
    query_group_assignment_submissions,
    query_group_assignment_view,
    query_individual_assignment_grade,
    query_individual_assignment_grade_statistics,
    query_individual_assignment_submissions,
    query_individual_assignment_view,
    save_quiz_open_ended_grades,
)
from models import Assignment, GroupAssignment
from teacher_routes.utils import is_authorized_for_class

from . import spa_api_blueprint


def _teacher_workspace_meta() -> dict:
    return {"scope": "teacher"}


def _with_teacher_submission_links(payload: dict, *, is_group: bool = False) -> dict:
    assignment = payload.get("assignment") or {}
    class_id = assignment.get("class_id")
    assignment_id = assignment.get("id")
    if class_id and assignment_id:
        base = f"/teacher/assignments-and-grades/{class_id}"
        kind = "group" if is_group else "individual"
        payload["links"] = {
            "view_spa": f"{base}/{kind}/{assignment_id}/view",
            "grade_spa": f"{base}/{kind}/{assignment_id}/grade",
            "submissions_spa": f"{base}/{kind}/{assignment_id}/submissions",
        }
    return payload


def _with_teacher_links(payload: dict) -> dict:
    item_type = payload.get("type")
    is_group = item_type == "group"
    class_id = (payload.get("class") or {}).get("id")
    assignment = payload.get("assignment") or {}
    assignment_id = assignment.get("id")
    if class_id and assignment_id:
        payload["links"] = _assignment_action_links(
            int(assignment_id),
            int(class_id),
            is_group=is_group,
            scope="teacher",
        )
    return payload


def _authorized_individual(assignment_id: int) -> tuple[Assignment | None, tuple | None]:
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return None, (jsonify({"error": "Assignment not found"}), 404)
    if not assignment.class_info or not is_authorized_for_class(assignment.class_info):
        return None, (jsonify({"error": "Forbidden"}), 403)
    return assignment, None


def _authorized_group(assignment_id: int) -> tuple[GroupAssignment | None, tuple | None]:
    assignment = GroupAssignment.query.get(assignment_id)
    if not assignment:
        return None, (jsonify({"error": "Assignment not found"}), 404)
    if not assignment.class_info or not is_authorized_for_class(assignment.class_info):
        return None, (jsonify({"error": "Forbidden"}), 403)
    return assignment, None


@spa_api_blueprint.route("/teacher/assignments/individual/<int:assignment_id>/view")
@login_required
@teacher_required
def teacher_individual_assignment_view(assignment_id: int):
    _, err = _authorized_individual(assignment_id)
    if err:
        return err
    return jsonify(
        {
            **_with_teacher_links(query_individual_assignment_view(assignment_id)),
            "meta": _teacher_workspace_meta(),
        }
    )


@spa_api_blueprint.route("/teacher/assignments/individual/<int:assignment_id>/grade")
@login_required
@teacher_required
def teacher_individual_assignment_grade(assignment_id: int):
    _, err = _authorized_individual(assignment_id)
    if err:
        return err
    return jsonify(
        {
            **_with_teacher_links(query_individual_assignment_grade(assignment_id)),
            "meta": _teacher_workspace_meta(),
        }
    )


@spa_api_blueprint.route("/teacher/assignments/individual/<int:assignment_id>/grade/statistics")
@login_required
@teacher_required
def teacher_individual_assignment_grade_statistics(assignment_id: int):
    _, err = _authorized_individual(assignment_id)
    if err:
        return err
    return jsonify(
        {
            **query_individual_assignment_grade_statistics(assignment_id),
            "meta": _teacher_workspace_meta(),
        }
    )


@spa_api_blueprint.route("/teacher/assignments/group/<int:assignment_id>/view")
@login_required
@teacher_required
def teacher_group_assignment_view(assignment_id: int):
    _, err = _authorized_group(assignment_id)
    if err:
        return err
    return jsonify(
        {
            **_with_teacher_links(query_group_assignment_view(assignment_id)),
            "meta": _teacher_workspace_meta(),
        }
    )


@spa_api_blueprint.route("/teacher/assignments/group/<int:assignment_id>/grade")
@login_required
@teacher_required
def teacher_group_assignment_grade(assignment_id: int):
    _, err = _authorized_group(assignment_id)
    if err:
        return err
    return jsonify(
        {
            **_with_teacher_links(query_group_assignment_grade(assignment_id)),
            "meta": _teacher_workspace_meta(),
        }
    )


@spa_api_blueprint.route("/teacher/assignments/individual/<int:assignment_id>/submissions")
@login_required
@teacher_required
def teacher_individual_assignment_submissions(assignment_id: int):
    _, err = _authorized_individual(assignment_id)
    if err:
        return err
    return jsonify(
        {
            **_with_teacher_submission_links(query_individual_assignment_submissions(assignment_id)),
            "meta": _teacher_workspace_meta(),
        }
    )


@spa_api_blueprint.route("/teacher/assignments/group/<int:assignment_id>/submissions")
@login_required
@teacher_required
def teacher_group_assignment_submissions(assignment_id: int):
    _, err = _authorized_group(assignment_id)
    if err:
        return err
    return jsonify(
        {
            **_with_teacher_submission_links(query_group_assignment_submissions(assignment_id), is_group=True),
            "meta": _teacher_workspace_meta(),
        }
    )


@spa_api_blueprint.route(
    "/teacher/assignments/individual/<int:assignment_id>/quiz-open-ended-grades",
    methods=["POST"],
)
@login_required
@teacher_required
def teacher_quiz_open_ended_grades(assignment_id: int):
    _, err = _authorized_individual(assignment_id)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    result = save_quiz_open_ended_grades(assignment_id, body.get("entries") or [])
    status = 200 if result.get("success") else 400
    return jsonify(result), status
