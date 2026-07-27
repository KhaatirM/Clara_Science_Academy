"""Class syllabus JSON API for management, teacher, and student SPAs."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from management_routes.class_syllabus_spa_helpers import (
    delete_class_syllabus,
    download_class_syllabus,
    get_class_syllabus_payload,
    upload_class_syllabus,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/classes/<int:class_id>/syllabus")
@login_required
def spa_class_syllabus_get(class_id: int):
    payload, error, status = get_class_syllabus_payload(class_id)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload)


@spa_api_blueprint.route("/classes/<int:class_id>/syllabus", methods=["POST"])
@login_required
def spa_class_syllabus_upload(class_id: int):
    file_storage = request.files.get('file') or request.files.get('syllabus')
    payload, error, status = upload_class_syllabus(class_id, file_storage)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload), status


@spa_api_blueprint.route("/classes/<int:class_id>/syllabus", methods=["DELETE"])
@login_required
def spa_class_syllabus_delete(class_id: int):
    payload, error, status = delete_class_syllabus(class_id)
    if error:
        return jsonify({"error": error}), status
    return jsonify(payload), status


@spa_api_blueprint.route("/classes/<int:class_id>/syllabus/download")
@login_required
def spa_class_syllabus_download(class_id: int):
    result, error, status = download_class_syllabus(class_id)
    if error:
        return jsonify({"error": error}), status
    return result
