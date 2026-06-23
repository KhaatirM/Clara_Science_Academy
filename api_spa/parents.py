"""Family Portal admin hub API for the React management SPA."""

from __future__ import annotations

from flask import jsonify
from flask_login import current_user, login_required

from decorators import get_user_permissions, permissions_required
from management_routes.parents import query_parents_hub

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
