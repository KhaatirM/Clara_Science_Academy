"""Class notes JSON API for management, teacher, and student SPAs."""

from __future__ import annotations

import io

from flask import jsonify, request, send_file
from flask_login import login_required

from management_routes.class_notes_drive_helpers import (
    download_drive_item,
    link_drive_folder,
    sync_drive_link_by_id,
    unlink_drive_folder,
)
from management_routes.class_notes_spa_helpers import (
    create_class_notes_folder,
    delete_class_notes_folder,
    delete_class_notes_item,
    download_class_notes_item,
    get_class_notes_folder_items_payload,
    get_class_notes_payload,
    update_class_notes_folder,
    upload_class_notes_item,
    upload_class_notes_items_bulk,
)

from . import spa_api_blueprint


@spa_api_blueprint.route('/classes/<int:class_id>/notes')
@login_required
def spa_class_notes_get(class_id: int):
    payload, error, status = get_class_notes_payload(class_id)
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload)


@spa_api_blueprint.route('/classes/<int:class_id>/notes/folders/<folder_id>/items')
@login_required
def spa_class_notes_folder_items(class_id: int, folder_id: str):
    if folder_id == 'root':
        resolved_folder_id = None
    else:
        try:
            resolved_folder_id = int(folder_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid folder id.'}), 400
    payload, error, status = get_class_notes_folder_items_payload(class_id, resolved_folder_id)
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload)


@spa_api_blueprint.route('/classes/<int:class_id>/notes/folders', methods=['POST'])
@login_required
def spa_class_notes_folder_create(class_id: int):
    body = request.get_json(silent=True) or {}
    parent_raw = body.get('parent_id')
    parent_id = None
    if parent_raw not in (None, '', 'null', 'undefined'):
        try:
            parent_id = int(parent_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid parent folder id.'}), 400
    payload, error, status = create_class_notes_folder(
        class_id,
        name=str(body.get('name') or ''),
        description=body.get('description'),
        parent_id=parent_id,
    )
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload), status


@spa_api_blueprint.route('/classes/<int:class_id>/notes/folders/<int:folder_id>', methods=['PATCH'])
@login_required
def spa_class_notes_folder_update(class_id: int, folder_id: int):
    body = request.get_json(silent=True) or {}
    kwargs: dict = {
        'name': body.get('name'),
        'description': body.get('description'),
    }
    if 'parent_id' in body:
        parent_raw = body.get('parent_id')
        if parent_raw in (None, '', 'null', 'undefined'):
            kwargs['parent_id'] = None
        else:
            try:
                kwargs['parent_id'] = int(parent_raw)
            except (TypeError, ValueError):
                return jsonify({'error': 'Invalid parent folder id.'}), 400
    payload, error, status = update_class_notes_folder(class_id, folder_id, **kwargs)
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload), status


@spa_api_blueprint.route('/classes/<int:class_id>/notes/folders/<int:folder_id>', methods=['DELETE'])
@login_required
def spa_class_notes_folder_delete(class_id: int, folder_id: int):
    payload, error, status = delete_class_notes_folder(class_id, folder_id)
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload), status


@spa_api_blueprint.route('/classes/<int:class_id>/notes/items', methods=['POST'])
@login_required
def spa_class_notes_item_upload(class_id: int):
    file_storage = request.files.get('file') or request.files.get('notes')
    folder_raw = request.form.get('folder_id')
    folder_id = None
    if folder_raw not in (None, '', 'null', 'undefined'):
        try:
            folder_id = int(folder_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid folder id.'}), 400

    duration = None
    duration_raw = request.form.get('duration_seconds')
    if duration_raw not in (None, '', 'null'):
        try:
            duration = float(duration_raw)
        except (TypeError, ValueError):
            duration = None

    payload, error, status = upload_class_notes_item(
        class_id,
        file_storage,
        folder_id=folder_id,
        title=request.form.get('title'),
        duration_seconds=duration,
    )
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload), status


@spa_api_blueprint.route('/classes/<int:class_id>/notes/items/bulk', methods=['POST'])
@login_required
def spa_class_notes_items_bulk(class_id: int):
    files = request.files.getlist('files') or request.files.getlist('file')
    folder_raw = request.form.get('folder_id')
    folder_id = None
    if folder_raw not in (None, '', 'null', 'undefined'):
        try:
            folder_id = int(folder_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid folder id.'}), 400
    payload, error, status = upload_class_notes_items_bulk(
        class_id, files, folder_id=folder_id
    )
    if error:
        return jsonify({'error': error, **(payload or {})}), status
    return jsonify(payload), status


@spa_api_blueprint.route('/classes/<int:class_id>/notes/items/<int:item_id>', methods=['DELETE'])
@login_required
def spa_class_notes_item_delete(class_id: int, item_id: int):
    payload, error, status = delete_class_notes_item(class_id, item_id)
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload), status


@spa_api_blueprint.route('/classes/<int:class_id>/notes/items/<int:item_id>/download')
@login_required
def spa_class_notes_item_download(class_id: int, item_id: int):
    result, error, status = download_class_notes_item(class_id, item_id)
    if error:
        return jsonify({'error': error}), status
    return result


@spa_api_blueprint.route('/classes/<int:class_id>/notes/drive/link', methods=['POST'])
@login_required
def spa_class_notes_drive_link(class_id: int):
    body = request.get_json(silent=True) or {}
    folder_raw = body.get('folder_id')
    folder_id = None
    if folder_raw not in (None, '', 'null', 'undefined'):
        try:
            folder_id = int(folder_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid folder id.'}), 400

    payload, error, status = link_drive_folder(
        class_id,
        folder_url=str(body.get('folder_url') or body.get('url') or ''),
        folder_id=folder_id,
        include_subfolders=bool(body.get('include_subfolders', True)),
    )
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload), status


@spa_api_blueprint.route(
    '/classes/<int:class_id>/notes/drive/links/<int:link_id>/sync', methods=['POST']
)
@login_required
def spa_class_notes_drive_sync(class_id: int, link_id: int):
    payload, error, status = sync_drive_link_by_id(class_id, link_id)
    if error:
        return jsonify({'error': error}), status
    if not (payload or {}).get('success'):
        return jsonify(payload), status
    return jsonify(payload), status


@spa_api_blueprint.route(
    '/classes/<int:class_id>/notes/drive/links/<int:link_id>', methods=['DELETE']
)
@login_required
def spa_class_notes_drive_unlink(class_id: int, link_id: int):
    payload, error, status = unlink_drive_folder(class_id, link_id)
    if error:
        return jsonify({'error': error}), status
    return jsonify(payload), status


@spa_api_blueprint.route('/classes/<int:class_id>/notes/drive/items/<int:item_id>/download')
@login_required
def spa_class_notes_drive_item_download(class_id: int, item_id: int):
    result, error, status = download_drive_item(class_id, item_id)
    if error:
        return jsonify({'error': error}), status
    return send_file(
        io.BytesIO(result['data']),
        mimetype=result['content_type'],
        as_attachment=not result['inline'],
        download_name=result['download_name'],
    )
