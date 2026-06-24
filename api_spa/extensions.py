"""Extension requests API for the React management SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import permissions_required
from extensions import db
from management_routes.assignments import _management_extension_reviewer_id, _parse_bulk_extension_request_ids
from management_routes.extensions_redo_spa_helpers import query_extensions_hub
from models import ExtensionRequest
from teacher_routes.assignment_utils import (
    apply_extension_request_review,
    bulk_process_extension_reviews,
    notify_extension_request_review,
)

from . import spa_api_blueprint


@spa_api_blueprint.route("/extensions")
@login_required
@permissions_required("assignments_grades:manage")
def extensions_list():
    return jsonify(query_extensions_hub())


@spa_api_blueprint.route("/extensions/<int:request_id>/review", methods=["POST"])
@login_required
@permissions_required("assignments_grades:manage")
def extensions_review(request_id: int):
    extension_request = ExtensionRequest.query.get_or_404(request_id)
    payload = request.get_json(silent=True) or {}
    action = (payload.get("action") or request.form.get("action") or "").strip().lower()
    review_notes = (payload.get("review_notes") or request.form.get("review_notes") or "").strip()

    if action not in ("approve", "reject"):
        return jsonify({"success": False, "message": "Invalid action"}), 400

    try:
        message = apply_extension_request_review(
            extension_request,
            action,
            review_notes,
            _management_extension_reviewer_id(),
        )
        db.session.commit()
        try:
            notify_extension_request_review(extension_request, action, review_notes)
        except Exception as notify_err:
            from flask import current_app

            current_app.logger.warning(f"Could not create extension notification: {notify_err}")
        return jsonify({"success": True, "message": message})
    except ValueError as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        from flask import current_app

        current_app.logger.error(f"Error reviewing extension request: {e}")
        return jsonify({"success": False, "message": f"Error processing request: {e}"}), 500


@spa_api_blueprint.route("/extensions/bulk-review", methods=["POST"])
@login_required
@permissions_required("assignments_grades:manage")
def extensions_bulk_review():
    payload = request.get_json(silent=True) or {}
    action = (payload.get("action") or request.form.get("action") or "").strip().lower()
    review_notes = (payload.get("review_notes") or request.form.get("review_notes") or "").strip()
    request_ids = payload.get("request_ids")
    if request_ids is None:
        request_ids = _parse_bulk_extension_request_ids()
    else:
        try:
            request_ids = [int(x) for x in request_ids if str(x).strip()]
        except (TypeError, ValueError):
            request_ids = None

    if action not in ("approve", "reject"):
        return jsonify({"success": False, "message": "Invalid action"}), 400
    if request_ids is None:
        return jsonify({"success": False, "message": "Invalid request ids"}), 400
    if not request_ids:
        return jsonify({"success": False, "message": "No requests selected"}), 400

    processed, failed = bulk_process_extension_reviews(
        request_ids,
        action,
        review_notes,
        _management_extension_reviewer_id(),
        teacher=None,
        admin=True,
    )

    if not processed:
        return jsonify(
            {
                "success": False,
                "message": "No requests could be processed.",
                "processed_count": 0,
                "failed": failed,
            }
        ), 400

    try:
        db.session.commit()
        for ext_req in processed:
            try:
                notify_extension_request_review(ext_req, action, review_notes)
            except Exception as notify_err:
                from flask import current_app

                current_app.logger.warning(f"Could not create extension notification: {notify_err}")
    except Exception as e:
        db.session.rollback()
        from flask import current_app

        current_app.logger.error(f"Error bulk reviewing extension requests: {e}")
        return jsonify({"success": False, "message": f"Error processing requests: {e}"}), 500

    verb = "approved" if action == "approve" else "rejected"
    message = f"{len(processed)} extension request(s) {verb}."
    if failed:
        message += f" {len(failed)} could not be processed."

    return jsonify(
        {
            "success": True,
            "message": message,
            "processed_count": len(processed),
            "failed": failed,
        }
    )
