"""Assignments & grades API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import permissions_required, user_can_manage_assignments_and_grades
from management_routes.assignments_spa_helpers import (
    query_assignments_class,
    query_assignments_hub,
)
from management_routes.assignment_create_spa_helpers import (
    query_create_assignment_meta,
    query_discussion_assignment_form,
    query_pdf_assignment_form,
    query_quiz_assignment_form,
)
from management_routes.group_create_spa_helpers import (
    query_group_class_picker,
    query_group_pdf_form,
    query_group_quiz_form,
    query_group_type_selector,
)
from management_routes.assignment_workspace_spa_helpers import (
    query_group_assignment_grade,
    query_group_assignment_view,
    query_individual_assignment_grade,
    query_individual_assignment_view,
)

from . import spa_api_blueprint


def _assignments_meta() -> dict:
    return {"can_manage": user_can_manage_assignments_and_grades(current_user)}


@spa_api_blueprint.route("/assignments/create")
@login_required
@permissions_required("assignments_grades:manage")
def create_assignment_meta():
    class_id = request.args.get("class_id", type=int)
    return jsonify({**query_create_assignment_meta(class_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/create/pdf")
@login_required
@permissions_required("assignments_grades:manage")
def pdf_assignment_form_meta():
    context = (request.args.get("context") or "homework").strip()
    class_id = request.args.get("class_id", type=int)
    return jsonify({**query_pdf_assignment_form(context, class_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/create/discussion")
@login_required
@permissions_required("assignments_grades:manage")
def discussion_assignment_form_meta():
    class_id = request.args.get("class_id", type=int)
    return jsonify({**query_discussion_assignment_form(class_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/create/quiz")
@login_required
@permissions_required("assignments_grades:manage")
def quiz_assignment_form_meta():
    class_id = request.args.get("class_id", type=int)
    return jsonify({**query_quiz_assignment_form(class_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/create/group")
@login_required
@permissions_required("assignments_grades:manage")
def group_class_picker_meta():
    return jsonify({**query_group_class_picker(), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/create/group/<int:class_id>")
@login_required
@permissions_required("assignments_grades:manage")
def group_type_selector_meta(class_id: int):
    return jsonify({**query_group_type_selector(class_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/create/group/<int:class_id>/pdf")
@login_required
@permissions_required("assignments_grades:manage")
def group_pdf_form_meta(class_id: int):
    return jsonify({**query_group_pdf_form(class_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/create/group/<int:class_id>/quiz")
@login_required
@permissions_required("assignments_grades:manage")
def group_quiz_form_meta(class_id: int):
    return jsonify({**query_group_quiz_form(class_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/hub")
@login_required
@permissions_required("assignments_grades:manage")
def assignments_hub():
    payload = query_assignments_hub(request.args)
    return jsonify({**payload, "meta": {**payload["meta"], **_assignments_meta()}})


@spa_api_blueprint.route("/assignments/class/<int:class_id>")
@login_required
@permissions_required("assignments_grades:manage")
def assignments_class(class_id: int):
    view_mode = (request.args.get("view") or "grades").strip()
    sort_by = (request.args.get("sort") or "due_date").strip()
    sort_order = (request.args.get("order") or "desc").strip()
    return jsonify(
        {
            **query_assignments_class(class_id, view_mode, sort_by, sort_order),
            "meta": _assignments_meta(),
        }
    )


@spa_api_blueprint.route("/assignments/individual/<int:assignment_id>/view")
@login_required
@permissions_required("assignments_grades:manage")
def individual_assignment_view(assignment_id: int):
    return jsonify({**query_individual_assignment_view(assignment_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/individual/<int:assignment_id>/grade")
@login_required
@permissions_required("assignments_grades:manage")
def individual_assignment_grade(assignment_id: int):
    return jsonify({**query_individual_assignment_grade(assignment_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/group/<int:assignment_id>/view")
@login_required
@permissions_required("assignments_grades:manage")
def group_assignment_view(assignment_id: int):
    return jsonify({**query_group_assignment_view(assignment_id), "meta": _assignments_meta()})


@spa_api_blueprint.route("/assignments/group/<int:assignment_id>/grade")
@login_required
@permissions_required("assignments_grades:manage")
def group_assignment_grade(assignment_id: int):
    return jsonify({**query_group_assignment_grade(assignment_id), "meta": _assignments_meta()})
