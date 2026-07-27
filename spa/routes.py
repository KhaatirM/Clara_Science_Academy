"""Serve the built React SPA from static/spa."""

from __future__ import annotations

import os

from flask import Blueprint, abort, current_app, make_response, redirect, send_from_directory

spa_blueprint = Blueprint("spa", __name__)

_SPA_ROOT = "static/spa"


def _spa_dir() -> str:
    return os.path.join(current_app.root_path, _SPA_ROOT)


def _spa_enabled() -> bool:
    return bool(current_app.config.get("REACT_SPA_ENABLED"))


def _spa_index_path() -> str:
    return os.path.join(_spa_dir(), "index.html")


@spa_blueprint.route("/app/assets/<path:filename>")
def spa_assets(filename: str):
    if not _spa_enabled():
        abort(404)
    assets_dir = os.path.join(_spa_dir(), "assets")
    if not os.path.isdir(assets_dir):
        abort(404)
    response = make_response(send_from_directory(assets_dir, filename))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@spa_blueprint.route("/app")
@spa_blueprint.route("/app/")
@spa_blueprint.route("/app/<path:path>")
def spa_index(path: str = ""):
    if not _spa_enabled():
        abort(404)
    if not os.path.isfile(_spa_index_path()):
        # Flag on but deploy skipped npm build — fall back instead of 503.
        current_app.logger.error(
            "REACT_SPA_ENABLED but static/spa/index.html missing; "
            "run bash scripts/build_spa.sh in the Render Build Command"
        )
        return redirect("/dashboard")
    response = make_response(send_from_directory(_spa_dir(), "index.html"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
