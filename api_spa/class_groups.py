"""Class student groups API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import permissions_required
from management_routes.class_groups_spa_helpers import mutate_class_groups, query_class_groups
from management_routes.classes import _can_class_admin_ui
from utils.user_roles import user_has_management_entry_access

from . import spa_api_blueprint


def _class_meta() -> dict:
    return {
        "can_admin_ui": _can_class_admin_ui(current_user),
        "can_create": user_has_management_entry_access(current_user),
    }


@spa_api_blueprint.route("/classes/<int:class_id>/groups")
@login_required
@permissions_required("classes:manage")
def class_groups_get(class_id: int):
    return jsonify({**query_class_groups(class_id), "meta": _class_meta()})


@spa_api_blueprint.route("/classes/<int:class_id>/groups", methods=["POST"])
@login_required
@permissions_required("classes:manage")
def class_groups_post(class_id: int):
    body = request.get_json(silent=True) or {}
    result = mutate_class_groups(class_id, body)
    status = 200 if result.get("success") else 400
    return jsonify(result), status
