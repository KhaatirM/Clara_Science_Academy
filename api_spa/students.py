"""Students list API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import permissions_required
from management_routes.students import _can_student_admin_ui, query_students_list, serialize_student_detail

from . import spa_api_blueprint


@spa_api_blueprint.route("/students")
@login_required
@permissions_required("students:view", "students:edit")
def students_list():
    payload = query_students_list(request.args)
    return jsonify(
        {
            "items": payload["items"],
            "stats": payload["stats"],
            "pagination": payload["pagination"],
            "filters": payload["filters"],
            "meta": {
                "can_admin_ui": _can_student_admin_ui(current_user),
            },
        }
    )


@spa_api_blueprint.route("/students/<int:student_id>")
@login_required
@permissions_required("students:view", "students:edit")
def student_detail(student_id: int):
    try:
        return jsonify(serialize_student_detail(student_id))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404
