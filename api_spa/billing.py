"""Billing & financials API for the React management SPA."""

from __future__ import annotations

from flask import jsonify
from flask_login import current_user, login_required

from decorators import permissions_required
from management_routes.billing_spa_helpers import query_billing_hub

from . import spa_api_blueprint


@spa_api_blueprint.route("/billing/hub")
@login_required
@permissions_required("billing:manage")
def billing_hub():
    return jsonify(query_billing_hub(user=current_user))


@spa_api_blueprint.route("/billing/add-invoice", methods=["POST"])
@login_required
@permissions_required("billing:manage")
def billing_add_invoice():
    return jsonify(
        {
            "success": True,
            "message": "Invoice creation functionality will be implemented soon!",
        }
    )


@spa_api_blueprint.route("/billing/record-payment", methods=["POST"])
@login_required
@permissions_required("billing:manage")
def billing_record_payment():
    return jsonify(
        {
            "success": True,
            "message": "Payment recording functionality will be implemented soon!",
        }
    )
