"""Serve the built React SPA from static/spa."""

from __future__ import annotations

import os

from flask import Blueprint, abort, current_app, send_from_directory

spa_blueprint = Blueprint("spa", __name__)

_SPA_ROOT = "static/spa"


def _spa_dir() -> str:
    return os.path.join(current_app.root_path, _SPA_ROOT)


def _spa_enabled() -> bool:
    return bool(current_app.config.get("REACT_SPA_ENABLED"))


@spa_blueprint.route("/app/assets/<path:filename>")
def spa_assets(filename: str):
    if not _spa_enabled():
        abort(404)
    assets_dir = os.path.join(_spa_dir(), "assets")
    if not os.path.isdir(assets_dir):
        abort(503)
    return send_from_directory(assets_dir, filename)


@spa_blueprint.route("/app")
@spa_blueprint.route("/app/")
@spa_blueprint.route("/app/<path:path>")
def spa_index(path: str = ""):
    if not _spa_enabled():
        abort(404)
    index_path = os.path.join(_spa_dir(), "index.html")
    if not os.path.isfile(index_path):
        abort(
            503,
            "React app not built. Run: cd frontend && npm install && npm run build",
        )
    return send_from_directory(_spa_dir(), "index.html")
