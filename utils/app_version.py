"""
Clara Science Academy portal — release version metadata.

The display version reflects how far the product has evolved: we began at v0.0.0
and have shipped thousands of iterative improvements since.
"""

from __future__ import annotations

# Where the portal started (first internal builds).
VERSION_ORIGIN = "0.0.0"

# Current public portal version (2 = mature era; 503 = Family Portal + report card approval).
VERSION_MAJOR = 2
VERSION_MINOR = 503
VERSION_PATCH = 1

APP_VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
APP_VERSION_DISPLAY = f"v {APP_VERSION}"

# Rough count of changelog entries / shipped improvements across project history.
ESTIMATED_UPDATE_COUNT = 2520

RELEASE_LABEL = "June 10, 2026"
PRODUCT_NAME = "Clara Science Academy Portal"


def app_version_context() -> dict:
    """Template context for version badge and modal."""
    return {
        "app_version": APP_VERSION,
        "app_version_display": APP_VERSION_DISPLAY,
        "app_version_origin": VERSION_ORIGIN,
        "app_version_updates_estimate": ESTIMATED_UPDATE_COUNT,
        "app_version_release_label": RELEASE_LABEL,
        "app_version_product_name": PRODUCT_NAME,
    }
