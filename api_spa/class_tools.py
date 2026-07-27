"""Class admin tools API for the React management SPA."""

from __future__ import annotations

from flask import jsonify
from flask_login import login_required

from decorators import permissions_required
from management_routes.class_tools_spa_helpers import CLASS_TOOL_SLUGS, query_class_tool

from . import spa_api_blueprint


@spa_api_blueprint.route("/classes/<int:class_id>/tools/<tool>")
@login_required
@permissions_required("classes:manage")
def class_tool(class_id: int, tool: str):
    if tool not in CLASS_TOOL_SLUGS:
        return jsonify({"success": False, "message": "Unknown tool."}), 404
    try:
        return jsonify(query_class_tool(class_id, tool))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404
