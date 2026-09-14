"""Family Portal admin hub API for the React management SPA."""

from __future__ import annotations

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from decorators import get_user_permissions, permissions_required
from management_routes.parents import query_parents_hub
from models import User
from utils.parent_login_letter import parent_login_letter_response

from . import spa_api_blueprint


@spa_api_blueprint.route("/parents")
@login_required
@permissions_required("students:view", "students:edit")
def parents_list():
    perms = get_user_permissions(current_user)
    payload = query_parents_hub()
    return jsonify(
        {
            "items": payload["items"],
            "stats": payload["stats"],
            "meta": {
                "can_provision": "students:edit" in perms or getattr(current_user, "role", None) in (
                    "Director",
                    "School Administrator",
                ),
            },
        }
    )


@spa_api_blueprint.route("/parents/<int:user_id>/login-letter", methods=["POST"])
@login_required
@permissions_required("students:edit")
def parent_login_letter(user_id: int):
    user = User.query.get_or_404(user_id)
    if (user.role or "") != "Parent":
        return jsonify({"success": False, "message": "That account is not a parent login."}), 404

    payload = request.get_json(silent=True) or {}
    reset_password = bool(payload.get("reset_password"))
    try:
        return parent_login_letter_response(user, reset_password=reset_password)
    except Exception as exc:
        current_app.logger.exception("Parent login letter failed for user %s", user_id)
        return jsonify({"success": False, "message": str(exc) or "Could not generate the login letter."}), 500
