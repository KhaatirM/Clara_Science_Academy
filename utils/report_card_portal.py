"""Report card visibility for the Family Portal and Director approval workflow."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from extensions import db
from models import ReportCard


def report_card_report_type(report_card: ReportCard) -> str:
    data = json.loads(report_card.grades_details or "{}")
    if isinstance(data, dict):
        return (data.get("report_type") or "official").strip().lower()
    return "official"


def is_official_report_card(report_card: ReportCard) -> bool:
    return report_card_report_type(report_card) == "official"


def get_parent_visible_report_cards(student_id: int) -> list[ReportCard]:
    """Official report cards the Director has approved for Family Portal access."""
    cards = (
        ReportCard.query.filter_by(student_id=student_id, director_approved=True)
        .order_by(ReportCard.generated_at.desc())
        .all()
    )
    return [c for c in cards if is_official_report_card(c)]


def parent_can_download_report_card(parent_user_id: int, report_card_id: int) -> bool:
    from utils.parent_portal import parent_has_access

    rc = ReportCard.query.get(report_card_id)
    if not rc or not rc.director_approved or not is_official_report_card(rc):
        return False
    return parent_has_access(parent_user_id, rc.student_id)


def _revoke_sibling_approvals(report_card: ReportCard) -> None:
    """Unpublish other approved cards for the same student, year, and quarter."""
    siblings = ReportCard.query.filter(
        ReportCard.student_id == report_card.student_id,
        ReportCard.school_year_id == report_card.school_year_id,
        ReportCard.quarter == report_card.quarter,
        ReportCard.id != report_card.id,
        ReportCard.director_approved.is_(True),
    ).all()
    for other in siblings:
        other.director_approved = False
        other.approved_at = None
        other.approved_by_user_id = None


def approve_report_card_for_parents(report_card: ReportCard, director_user_id: int) -> ReportCard:
    if not is_official_report_card(report_card):
        raise ValueError("Only official report cards can be published to the Family Portal.")
    _revoke_sibling_approvals(report_card)
    report_card.director_approved = True
    report_card.approved_at = datetime.utcnow()
    report_card.approved_by_user_id = director_user_id
    db.session.commit()
    return report_card


def revoke_report_card_parent_access(report_card: ReportCard) -> ReportCard:
    report_card.director_approved = False
    report_card.approved_at = None
    report_card.approved_by_user_id = None
    db.session.commit()
    return report_card


def count_pending_parent_approval() -> int:
    """Official report cards awaiting Director approval."""
    pending = 0
    for rc in ReportCard.query.filter_by(director_approved=False).all():
        if is_official_report_card(rc):
            pending += 1
    return pending
