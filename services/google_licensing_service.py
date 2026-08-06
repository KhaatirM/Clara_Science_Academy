"""
Google Enterprise License Manager helpers (assign / revoke Workspace licenses).

Requires domain-wide delegation scope:
  https://www.googleapis.com/auth/apps.licensing
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

from flask import current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

LICENSING_SCOPE = "https://www.googleapis.com/auth/apps.licensing"

# (productId, skuId) pairs commonly used for Education / Workspace.
# Try all known SKUs so older and post-2024 Fundamentals both work.
EDUCATION_LICENSE_SKUS: Tuple[Tuple[str, str], ...] = (
    ("Google-Apps", "Google-Apps-For-Education"),
    ("Google-Apps", "1010070001"),  # Education Fundamentals (newer)
    ("Google-Apps", "1010070004"),  # Gmail Only
    ("101031", "1010310005"),  # Standard
    ("101031", "1010310006"),  # Standard (Staff)
    ("101031", "1010310008"),  # Plus
    ("101031", "1010310009"),  # Plus (Staff)
    ("101031", "1010310002"),  # Plus Legacy
    ("101031", "1010310003"),  # Plus Legacy (Student)
    ("101037", "1010370001"),  # Teaching and Learning Upgrade
)

_licensing_service_cache: dict[tuple[str, ...], Any] = {}


def get_licensing_service(scopes: Optional[Sequence[str]] = None):
    key_json = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON")
    key_file = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE")
    delegated_admin = current_app.config.get("GOOGLE_DIRECTORY_DELEGATED_ADMIN")

    if key_json is not None and isinstance(key_json, str):
        key_json = key_json.strip() or None

    if not delegated_admin:
        current_app.logger.error(
            "Licensing service not configured. Set GOOGLE_DIRECTORY_DELEGATED_ADMIN."
        )
        return None
    if not key_json and not key_file:
        current_app.logger.error(
            "Licensing service not configured. "
            "Set GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON or GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE."
        )
        return None

    effective_scopes = list(scopes) if scopes else [LICENSING_SCOPE]
    cache_key = tuple(sorted(effective_scopes))
    if cache_key in _licensing_service_cache:
        return _licensing_service_cache[cache_key]

    try:
        if key_json:
            info = json.loads(key_json)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=effective_scopes
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                key_file, scopes=effective_scopes
            )
        delegated = creds.with_subject(delegated_admin)
        service = build("licensing", "v1", credentials=delegated, cache_discovery=False)
        _licensing_service_cache[cache_key] = service
        return service
    except Exception as e:
        current_app.logger.error("Failed to build Licensing API client: %s", e)
        return None


def _http_status(exc: HttpError) -> int:
    return int(getattr(getattr(exc, "resp", None), "status", None) or 0)


def get_user_license_assignment(
    user_email: str,
    product_id: str,
    sku_id: str,
) -> Optional[Dict[str, Any]]:
    service = get_licensing_service()
    if not service:
        return None
    email = (user_email or "").strip()
    if not email:
        return None
    try:
        return (
            service.licenseAssignments()
            .get(productId=product_id, skuId=sku_id, userId=email)
            .execute()
        )
    except HttpError as e:
        if _http_status(e) == 404:
            return None
        current_app.logger.warning(
            "Licensing get failed for %s product=%s sku=%s: %s",
            email,
            product_id,
            sku_id,
            e,
        )
        return None
    except Exception as e:
        current_app.logger.warning(
            "Licensing get failed for %s product=%s sku=%s: %s",
            email,
            product_id,
            sku_id,
            e,
        )
        return None


def delete_user_license_assignment(user_email: str, product_id: str, sku_id: str) -> bool:
    """Revoke one product/SKU license. True if deleted or already absent."""
    service = get_licensing_service()
    if not service:
        return False
    email = (user_email or "").strip()
    if not email:
        return False
    try:
        service.licenseAssignments().delete(
            productId=product_id, skuId=sku_id, userId=email
        ).execute()
        current_app.logger.info(
            "Revoked license product=%s sku=%s for %s", product_id, sku_id, email
        )
        return True
    except HttpError as e:
        if _http_status(e) == 404:
            return True
        current_app.logger.error(
            "Licensing delete failed for %s product=%s sku=%s: %s",
            email,
            product_id,
            sku_id,
            e,
        )
        return False
    except Exception as e:
        current_app.logger.error(
            "Licensing delete failed for %s product=%s sku=%s: %s",
            email,
            product_id,
            sku_id,
            e,
        )
        return False


def list_assigned_education_licenses(user_email: str) -> List[Tuple[str, str]]:
    """Return (productId, skuId) pairs currently assigned to the user."""
    email = (user_email or "").strip()
    if not email:
        return []
    found: List[Tuple[str, str]] = []
    for product_id, sku_id in EDUCATION_LICENSE_SKUS:
        if get_user_license_assignment(email, product_id, sku_id):
            found.append((product_id, sku_id))
    return found


def revoke_all_education_licenses(user_email: str) -> Dict[str, Any]:
    """
    Suspend-policy helper: revoke every known Education / Workspace SKU on the user.

    Returns ``{ok, revoked, attempted, errors}``.
    """
    email = (user_email or "").strip()
    if not email:
        return {"ok": False, "revoked": 0, "attempted": 0, "errors": ["empty email"]}

    assigned = list_assigned_education_licenses(email)
    if not assigned:
        # Still attempt delete on Fundamentals SKUs in case get is restricted.
        assigned = list(EDUCATION_LICENSE_SKUS[:2])

    revoked = 0
    errors: List[str] = []
    for product_id, sku_id in assigned:
        if delete_user_license_assignment(email, product_id, sku_id):
            revoked += 1
        else:
            errors.append(f"{product_id}/{sku_id}")

    return {
        "ok": len(errors) == 0,
        "revoked": revoked,
        "attempted": len(assigned),
        "errors": errors,
    }
