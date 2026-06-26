"""Management settings API for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import management_required
from management_routes.settings_spa_helpers import query_settings_hub

from . import spa_api_blueprint


@spa_api_blueprint.route("/settings/hub")
@login_required
@management_required
def settings_hub():
    return jsonify(query_settings_hub(user=current_user))


@spa_api_blueprint.route("/settings/theme", methods=["POST"])
@login_required
@management_required
def settings_update_theme():
    from authroutes import update_theme

    return update_theme()
