"""Invalidate academic-concern and pending-grade caches after grade mutations."""

from __future__ import annotations


def notify_grades_changed() -> None:
    """Clear staff alert caches after grades are saved/cleared."""
    try:
        from utils.at_risk_alerts import invalidate_at_risk_alerts_cache

        invalidate_at_risk_alerts_cache()
    except Exception:
        pass
    try:
        from utils.pending_grade_alerts import invalidate_pending_grade_alerts_cache

        invalidate_pending_grade_alerts_cache()
    except Exception:
        pass
