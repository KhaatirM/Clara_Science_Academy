"""Google Workspace initial passwords — never hardcode shared secrets in source."""

from __future__ import annotations

import os

from utils.temporary_passwords import generate_temporary_password


def new_google_workspace_initial_password() -> str:
    """Random initial password for a newly provisioned Workspace account."""
    return generate_temporary_password(14)


def google_workspace_initial_password_for_sync(*, require_env: bool = False) -> str:
    """
    Password for bulk/sync scripts that create Workspace users.

    When ``require_env`` is True, ``GOOGLE_WORKSPACE_INITIAL_PASSWORD`` must be set.
    Otherwise a one-off random password is generated (admin reset / credential handoff).
    """
    pw = (os.environ.get("GOOGLE_WORKSPACE_INITIAL_PASSWORD") or "").strip()
    if pw:
        return pw
    if require_env:
        raise RuntimeError(
            "Set GOOGLE_WORKSPACE_INITIAL_PASSWORD in the environment for this operation."
        )
    return new_google_workspace_initial_password()


def legacy_google_passwords_for_audit() -> list[str]:
    """Optional env list of known legacy shared passwords to flag during audits."""
    raw = (os.environ.get("AUDIT_LEGACY_GOOGLE_PASSWORDS") or "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]
