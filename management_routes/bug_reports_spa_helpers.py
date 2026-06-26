"""Bug reports data for the management React SPA (nested under Settings)."""

from __future__ import annotations

from typing import Any

from models import BugReport, User


def _serialize_bug_report(report: BugReport) -> dict[str, Any]:
    reporter = User.query.get(report.user_id) if report.user_id else None
    return {
        "id": report.id,
        "title": report.title,
        "description": report.description,
        "contact_email": report.contact_email,
        "severity": report.severity,
        "status": report.status,
        "page_url": report.page_url,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "reporter_username": reporter.username if reporter else None,
    }


def query_bug_reports(*, user) -> dict[str, Any]:
    role = getattr(user, "role", None)
    can_manage = role in ("Tech", "IT Support")
    if can_manage:
        reports = BugReport.query.order_by(BugReport.created_at.desc()).all()
    else:
        reports = (
            BugReport.query.filter_by(user_id=user.id).order_by(BugReport.created_at.desc()).all()
        )

    open_count = sum(1 for report in reports if report.status == "open")
    in_progress_count = sum(1 for report in reports if report.status == "in_progress")
    resolved_count = sum(1 for report in reports if report.status in ("resolved", "closed"))

    return {
        "can_manage": can_manage,
        "summary": {
            "total": len(reports),
            "open": open_count,
            "in_progress": in_progress_count,
            "resolved": resolved_count,
        },
        "reports": [_serialize_bug_report(report) for report in reports],
    }
