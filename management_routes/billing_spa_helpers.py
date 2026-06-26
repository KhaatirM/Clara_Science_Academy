"""Billing & financials hub data for the management React SPA."""

from __future__ import annotations

from typing import Any

from utils.student_roster import active_roster_students_query
from utils.user_roles import canonical_role_label


def query_billing_hub(*, user) -> dict[str, Any]:
    """Return placeholder billing metrics until billing models exist."""
    student_count = active_roster_students_query(require_active_enrollment=False).count()
    role = canonical_role_label(getattr(user, "role", None))

    return {
        "role_canonical": role,
        "is_director": role == "Director",
        "metrics": {
            "total_revenue": 0.0,
            "total_payments": 0.0,
            "outstanding_balance": 0.0,
            "student_count": student_count,
            "active_invoices": 0,
            "pending_invoices": 0,
        },
        "invoices": [],
        "pending_invoices": [],
        "coming_soon": True,
        "urls": {
            "home": "/management",
        },
    }
