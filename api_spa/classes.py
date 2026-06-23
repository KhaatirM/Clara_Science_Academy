"""Classes API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import permissions_required
from management_routes.class_spa_helpers import (
    assignable_teachers,
    core_setup_create,
    core_setup_preview,
    create_class_from_body,
    google_classroom_action,
    google_classroom_options,
    mutate_class_roster,
    query_class_detail,
    query_class_edit_form,
    query_class_grades,
    query_class_roster,
    query_core_setup_form,
    update_class_from_body,
)
from management_routes.classes import _can_class_admin_ui, query_classes_list
from utils.user_roles import user_has_management_entry_access

from . import spa_api_blueprint


def _class_meta() -> dict:
    return {
        "can_admin_ui": _can_class_admin_ui(current_user),
        "can_create": user_has_management_entry_access(current_user),
    }


@spa_api_blueprint.route("/classes/form-options")
@login_required
@permissions_required("classes:manage")
def classes_form_options():
    active = None
    from models import SchoolYear

    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if active_year:
        active = {"id": active_year.id, "name": active_year.name}
    return jsonify({"teachers": assignable_teachers(), "active_school_year": active, "meta": _class_meta()})


@spa_api_blueprint.route("/classes/core-setup")
@login_required
@permissions_required("classes:manage")
def classes_core_setup_form():
    if not user_has_management_entry_access(current_user):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({**query_core_setup_form(), "meta": _class_meta()})


@spa_api_blueprint.route("/classes/core-setup/preview", methods=["POST"])
@login_required
@permissions_required("classes:manage")
def classes_core_setup_preview():
    if not user_has_management_entry_access(current_user):
        return jsonify({"error": "Forbidden"}), 403
    body = request.get_json(silent=True) or {}
    return jsonify(core_setup_preview(body))


@spa_api_blueprint.route("/classes/core-setup/create", methods=["POST"])
@login_required
@permissions_required("classes:manage")
def classes_core_setup_create():
    if not user_has_management_entry_access(current_user):
        return jsonify({"error": "Forbidden"}), 403
    body = request.get_json(silent=True) or {}
    return jsonify(core_setup_create(body))


@spa_api_blueprint.route("/classes", methods=["POST"])
@login_required
@permissions_required("classes:manage")
def classes_create():
    if not user_has_management_entry_access(current_user):
        return jsonify({"error": "Forbidden"}), 403
    body = request.get_json(silent=True) or {}
    result = create_class_from_body(body)
    status = 200 if result.get("success") else 400
    return jsonify({**result, "meta": _class_meta()}), status


@spa_api_blueprint.route("/classes")
@login_required
@permissions_required("classes:manage")
def classes_list():
    payload = query_classes_list(request.args)
    return jsonify(
        {
            "items": payload["items"],
            "stats": payload["stats"],
            "filters": payload["filters"],
            "school_years": payload["school_years"],
            "meta": {**payload["meta"], **_class_meta()},
        }
    )


@spa_api_blueprint.route("/classes/<int:class_id>")
@login_required
@permissions_required("classes:manage")
def class_detail(class_id: int):
    return jsonify({**query_class_detail(class_id), "meta": _class_meta()})


@spa_api_blueprint.route("/classes/<int:class_id>/edit")
@login_required
@permissions_required("classes:manage")
def class_edit_form(class_id: int):
    return jsonify({**query_class_edit_form(class_id), "meta": _class_meta()})


@spa_api_blueprint.route("/classes/<int:class_id>", methods=["PATCH"])
@login_required
@permissions_required("classes:manage")
def class_update(class_id: int):
    if not _can_class_admin_ui(current_user):
        return jsonify({"success": False, "message": "Forbidden"}), 403
    body = request.get_json(silent=True) or {}
    result = update_class_from_body(class_id, body)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/classes/<int:class_id>/roster")
@login_required
@permissions_required("classes:manage")
def class_roster_get(class_id: int):
    return jsonify({**query_class_roster(class_id), "meta": _class_meta()})


@spa_api_blueprint.route("/classes/<int:class_id>/roster", methods=["POST"])
@login_required
@permissions_required("classes:manage")
def class_roster_post(class_id: int):
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").strip()
    student_ids = [int(x) for x in (body.get("student_ids") or []) if str(x).isdigit()]
    result = mutate_class_roster(class_id, action, student_ids)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/classes/<int:class_id>/grades")
@login_required
@permissions_required("classes:manage")
def class_grades_get(class_id: int):
    view_mode = (request.args.get("view") or "table").strip()
    return jsonify({**query_class_grades(class_id, view_mode), "meta": _class_meta()})


@spa_api_blueprint.route("/classes/<int:class_id>/google-classroom/options")
@login_required
@permissions_required("classes:manage")
def class_google_options(class_id: int):
    return jsonify(google_classroom_options(class_id))


@spa_api_blueprint.route("/classes/<int:class_id>/google-classroom", methods=["POST"])
@login_required
@permissions_required("classes:manage")
def class_google_action(class_id: int):
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").strip()
    google_id = body.get("google_classroom_id")
    result = google_classroom_action(class_id, action, google_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@spa_api_blueprint.route("/classes/<int:class_id>/remove", methods=["POST"])
@login_required
@permissions_required("classes:manage")
def class_remove(class_id: int):
    if not user_has_management_entry_access(current_user):
        return jsonify({"success": False, "message": "Forbidden"}), 403
    from management_routes.classes import remove_class

    return remove_class(class_id)
