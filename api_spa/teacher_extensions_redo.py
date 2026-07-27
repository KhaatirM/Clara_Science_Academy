"""Teacher extensions and redo APIs for the React SPA."""

from __future__ import annotations

from flask import jsonify, request
from flask_login import current_user, login_required

from decorators import teacher_required
from extensions import db
from management_routes.extensions_redo_spa_helpers import query_redo_dashboard, query_teacher_extensions_hub
from models import ExtensionRequest, TeacherStaff
from teacher_routes.assignment_utils import (
    apply_extension_request_review,
    bulk_process_extension_reviews,
    notify_extension_request_review,
    teacher_can_review_extension_request,
)
from teacher_routes.assignments import _extension_reviewer_id, _parse_extension_request_ids
from teacher_routes.utils import get_teacher_or_admin, is_admin

from . import spa_api_blueprint


def _teacher_extension_reviewer_id():
    teacher = get_teacher_or_admin()
    return _extension_reviewer_id(teacher)


def _can_review_extension(extension_request: ExtensionRequest) -> bool:
    if is_admin():
        return True
    teacher = get_teacher_or_admin()
    return bool(teacher and teacher_can_review_extension_request(extension_request, teacher))


@spa_api_blueprint.route("/teacher/extensions")
@login_required
@teacher_required
def teacher_extensions_list():
    return jsonify(query_teacher_extensions_hub())


@spa_api_blueprint.route("/teacher/extensions/<int:request_id>/review", methods=["POST"])
@login_required
@teacher_required
def teacher_extensions_review(request_id: int):
    extension_request = ExtensionRequest.query.get_or_404(request_id)
    if not _can_review_extension(extension_request):
        return jsonify({"success": False, "message": "You are not authorized to review this request"}), 403

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
            _teacher_extension_reviewer_id(),
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


@spa_api_blueprint.route("/teacher/extensions/bulk-review", methods=["POST"])
@login_required
@teacher_required
def teacher_extensions_bulk_review():
    payload = request.get_json(silent=True) or {}
    action = (payload.get("action") or request.form.get("action") or "").strip().lower()
    review_notes = (payload.get("review_notes") or request.form.get("review_notes") or "").strip()
    request_ids = payload.get("request_ids")
    if request_ids is None:
        request_ids = _parse_extension_request_ids()
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

    teacher = get_teacher_or_admin()
    processed, failed = bulk_process_extension_reviews(
        request_ids,
        action,
        review_notes,
        _teacher_extension_reviewer_id(),
        teacher=teacher,
        admin=is_admin(),
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


@spa_api_blueprint.route("/teacher/redo-dashboard")
@login_required
@teacher_required
def teacher_redo_dashboard_api():
    payload = query_redo_dashboard()
    payload.setdefault("meta", {})
    payload["meta"]["scope"] = "teacher"
    return jsonify(payload)


@spa_api_blueprint.route("/teacher/redo-requests/<int:request_id>/grant", methods=["POST"])
@login_required
@teacher_required
def teacher_redo_request_grant(request_id: int):
    from api_spa.redo import redo_request_grant

    return redo_request_grant(request_id)


@spa_api_blueprint.route("/teacher/redo-requests/<int:request_id>/reject", methods=["POST"])
@login_required
@teacher_required
def teacher_redo_request_reject(request_id: int):
    from api_spa.redo import redo_request_reject

    return redo_request_reject(request_id)


@spa_api_blueprint.route("/teacher/redos/<int:redo_id>/revoke", methods=["POST"])
@login_required
@teacher_required
def teacher_redo_revoke(redo_id: int):
    from api_spa.redo import redo_revoke

    return redo_revoke(redo_id)
