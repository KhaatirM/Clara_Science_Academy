"""Google Drive browse + import APIs for SPA document uploads."""

from __future__ import annotations

import re
from io import BytesIO

from flask import jsonify, request, send_file
from flask_login import current_user, login_required

from services.google_drive_service import (
    FOLDER_MIME_TYPE,
    DriveAccessError,
    DriveAuthError,
    download_file_bytes,
    export_target_for,
    get_drive_service,
    get_file_metadata,
    is_google_native,
    list_folder_children,
    partition_children,
    resolve_shortcut,
)

from . import spa_api_blueprint

_SAFE_NAME = re.compile(r"[^\w.\- ()]+", re.UNICODE)


def _connect_url() -> str:
    try:
        from utils.user_roles import user_has_teacher_spa_entry, user_can_use_management_spa_shell

        if user_can_use_management_spa_shell(current_user) and not (
            user_has_teacher_spa_entry(current_user)
            and getattr(current_user, "teacher_staff_id", None)
            and request.args.get("scope") == "teacher"
        ):
            # Prefer teacher connect when on teacher shell; otherwise management.
            pass
        if request.path.startswith("/api/spa") and request.args.get("scope") == "teacher":
            return "/teacher/google-account/connect"
        from utils.user_roles import user_has_management_entry_access

        if user_has_management_entry_access(current_user) or user_can_use_management_spa_shell(
            current_user
        ):
            return "/management/google-account/connect"
        if user_has_teacher_spa_entry(current_user):
            return "/teacher/google-account/connect"
    except Exception:
        pass
    return "/settings"


def _settings_path() -> str:
    try:
        from utils.user_roles import (
            user_can_use_management_spa_shell,
            user_has_student_spa_entry,
            user_has_teacher_spa_entry,
        )

        if user_has_student_spa_entry(current_user) and not user_has_teacher_spa_entry(current_user):
            return "/app/student/settings"
        if user_has_teacher_spa_entry(current_user) and not user_can_use_management_spa_shell(
            current_user
        ):
            return "/app/teacher/settings"
        if user_can_use_management_spa_shell(current_user):
            return "/app/settings"
    except Exception:
        pass
    return "/app/settings"


def _safe_filename(name: str | None, *, ext: str | None = None) -> str:
    base = (name or "download").strip() or "download"
    cleaned = _SAFE_NAME.sub("_", base).strip("._") or "download"
    if ext and not cleaned.lower().endswith(f".{ext.lower()}"):
        cleaned = f"{cleaned}.{ext}"
    return cleaned[:200]


def _entry_payload(entry: dict) -> dict:
    mime = entry.get("mimeType") or ""
    is_folder = mime == FOLDER_MIME_TYPE
    return {
        "id": entry.get("id"),
        "name": entry.get("name") or "Untitled",
        "mime_type": mime,
        "is_folder": is_folder,
        "size": int(entry["size"]) if entry.get("size") not in (None, "") else None,
        "modified_time": entry.get("modifiedTime"),
        "icon_link": entry.get("iconLink"),
    }


@spa_api_blueprint.route("/drive/status")
@login_required
def drive_status():
    connected = bool(getattr(current_user, "has_google_token_stored", False))
    return jsonify(
        {
            "connected": connected,
            "connect_url": _connect_url(),
            "settings_path": _settings_path(),
            "message": (
                None
                if connected
                else "Connect Google in Settings to pick files from Drive. "
                "Signing in with Google alone is not enough."
            ),
        }
    )


@spa_api_blueprint.route("/drive/browse")
@login_required
def drive_browse():
    folder_id = (request.args.get("folder_id") or "root").strip() or "root"
    try:
        service = get_drive_service(current_user)
        raw = list_folder_children(service, folder_id)
        resolved = [resolve_shortcut(service, e) for e in raw]
        folders, files = partition_children(resolved)
        folder_name = "My Drive"
        parent_id = None
        if folder_id != "root":
            try:
                meta = get_file_metadata(service, folder_id)
                folder_name = meta.get("name") or folder_name
                parents = meta.get("parents") or []
                parent_id = parents[0] if parents else "root"
            except DriveAccessError:
                parent_id = "root"
        return jsonify(
            {
                "folder_id": folder_id,
                "folder_name": folder_name,
                "parent_id": parent_id,
                "folders": [_entry_payload(f) for f in folders],
                "files": [_entry_payload(f) for f in files],
            }
        )
    except DriveAuthError as exc:
        return jsonify({"error": str(exc), "connected": False, "connect_url": _connect_url()}), 401
    except DriveAccessError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Could not browse Drive: {exc}"}), 500


@spa_api_blueprint.route("/drive/files/<file_id>/content")
@login_required
def drive_file_content(file_id: str):
    try:
        service = get_drive_service(current_user)
        meta = get_file_metadata(service, file_id)
        if meta.get("mimeType") == FOLDER_MIME_TYPE:
            return jsonify({"error": "That item is a folder, not a file."}), 400
        mime = meta.get("mimeType")
        data, content_type = download_file_bytes(service, file_id, mime_type=mime)
        name = meta.get("name") or "download"
        export = export_target_for(mime)
        if export:
            _export_mime, ext = export
            filename = _safe_filename(name, ext=ext)
        elif is_google_native(mime):
            filename = _safe_filename(name, ext="bin")
        else:
            filename = _safe_filename(name)
        return send_file(
            BytesIO(data),
            mimetype=content_type or "application/octet-stream",
            as_attachment=True,
            download_name=filename,
            max_age=0,
        )
    except DriveAuthError as exc:
        return jsonify({"error": str(exc), "connected": False, "connect_url": _connect_url()}), 401
    except DriveAccessError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Could not download Drive file: {exc}"}), 500
