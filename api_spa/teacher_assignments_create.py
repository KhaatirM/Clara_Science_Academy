"""Teacher assignment creation APIs for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from decorators import teacher_required
from management_routes.assignment_create_spa_helpers import (
    query_create_assignment_meta,
    query_discussion_assignment_form,
    query_pdf_assignment_form,
    query_quiz_assignment_form,
)
from management_routes.class_groups_spa_helpers import query_class_groups
from management_routes.group_create_spa_helpers import (
    query_group_class_picker,
    query_group_discussion_form,
    query_group_pdf_form,
    query_group_quiz_form,
    query_group_type_selector,
)
from models import Class
from teacher_routes.utils import is_authorized_for_class

from . import spa_api_blueprint


def _teacher_create_meta() -> dict:
    return {"can_manage": False, "scope": "teacher"}


def _authorized_class_or_404(class_id: int) -> Class | None:
    class_obj = Class.query.get(class_id)
    if not class_obj:
        return None
    if not is_authorized_for_class(class_obj):
        return None
    return class_obj


@spa_api_blueprint.route("/teacher/assignments/create")
@login_required
@teacher_required
def teacher_create_assignment_meta():
    class_id = request.args.get("class_id", type=int)
    if class_id and not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(
        {**query_create_assignment_meta(class_id, scope="teacher"), "meta": _teacher_create_meta()}
    )


@spa_api_blueprint.route("/teacher/assignments/create/pdf")
@login_required
@teacher_required
def teacher_pdf_assignment_form_meta():
    context = (request.args.get("context") or "homework").strip()
    class_id = request.args.get("class_id", type=int)
    if class_id and not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(
        {
            **query_pdf_assignment_form(context, class_id, scope="teacher"),
            "meta": _teacher_create_meta(),
        }
    )


@spa_api_blueprint.route("/teacher/assignments/create/discussion")
@login_required
@teacher_required
def teacher_discussion_assignment_form_meta():
    class_id = request.args.get("class_id", type=int)
    edit_id = request.args.get("edit", type=int)
    if class_id and not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    try:
        payload = query_discussion_assignment_form(class_id, scope="teacher", edit_id=edit_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    if edit_id and payload.get("edit") and not _authorized_class_or_404(payload["edit"]["class_id"]):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({**payload, "meta": _teacher_create_meta()})


@spa_api_blueprint.route("/teacher/assignments/create/quiz")
@login_required
@teacher_required
def teacher_quiz_assignment_form_meta():
    class_id = request.args.get("class_id", type=int)
    edit_id = request.args.get("edit", type=int)
    if class_id and not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    try:
        payload = query_quiz_assignment_form(class_id, scope="teacher", edit_id=edit_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    if edit_id and payload.get("edit") and not _authorized_class_or_404(payload["edit"]["class_id"]):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({**payload, "meta": _teacher_create_meta()})


@spa_api_blueprint.route("/teacher/assignments/create/group")
@login_required
@teacher_required
def teacher_group_class_picker_meta():
    return jsonify({**query_group_class_picker(scope="teacher"), "meta": _teacher_create_meta()})


@spa_api_blueprint.route("/teacher/assignments/create/group/<int:class_id>")
@login_required
@teacher_required
def teacher_group_type_selector_meta(class_id: int):
    if not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(
        {**query_group_type_selector(class_id, scope="teacher"), "meta": _teacher_create_meta()}
    )


@spa_api_blueprint.route("/teacher/assignments/create/group/<int:class_id>/pdf")
@login_required
@teacher_required
def teacher_group_pdf_form_meta(class_id: int):
    if not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(
        {**query_group_pdf_form(class_id, scope="teacher"), "meta": _teacher_create_meta()}
    )


@spa_api_blueprint.route("/teacher/assignments/create/group/<int:class_id>/quiz")
@login_required
@teacher_required
def teacher_group_quiz_form_meta(class_id: int):
    if not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(
        {**query_group_quiz_form(class_id, scope="teacher"), "meta": _teacher_create_meta()}
    )


@spa_api_blueprint.route("/teacher/assignments/create/group/<int:class_id>/discussion")
@login_required
@teacher_required
def teacher_group_discussion_form_meta(class_id: int):
    if not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(
        {
            **query_group_discussion_form(class_id, scope="teacher"),
            "meta": _teacher_create_meta(),
        }
    )


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/groups")
@login_required
@teacher_required
def teacher_class_groups(class_id: int):
    if not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    payload = query_class_groups(class_id)
    if request.args.get("full") == "1":
        return jsonify({**payload, "meta": {"can_admin_ui": True, "can_create": True}})
    groups = [
        {
            "id": group["id"],
            "name": group["name"],
            "description": group.get("description"),
            "member_count": group.get("member_count", 0),
        }
        for group in payload.get("groups", [])
    ]
    return jsonify({"success": True, "groups": groups})


@spa_api_blueprint.route("/teacher/classes/<int:class_id>/groups", methods=["POST"])
@login_required
@teacher_required
def teacher_class_groups_mutate(class_id: int):
    from management_routes.class_groups_spa_helpers import mutate_class_groups

    if not _authorized_class_or_404(class_id):
        return jsonify({"error": "Forbidden"}), 403
    body = request.get_json(silent=True) or {}
    result = mutate_class_groups(class_id, body)
    status = 200 if result.get("success") else 400
    return jsonify(result), status
