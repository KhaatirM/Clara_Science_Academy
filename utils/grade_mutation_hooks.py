"""Invalidate academic-concern caches after grade mutations."""

from __future__ import annotations


def notify_grades_changed() -> None:
    """Clear at-risk alert caches for all viewers after grades are saved/cleared."""
    try:
        from utils.at_risk_alerts import invalidate_at_risk_alerts_cache

        invalidate_at_risk_alerts_cache()
    except Exception:
        pass
