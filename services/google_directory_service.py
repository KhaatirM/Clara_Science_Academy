"""
Google Directory Service Module

This module provides helper functions to interact with the Google Admin SDK
Directory API using a Service Account with domain-wide delegation.

Expected config keys (Flask `current_app.config`):
- GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON: raw service account key JSON string (preferred on PaaS e.g. Render)
- GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE: path to service account JSON key file (fallback)
- GOOGLE_DIRECTORY_DELEGATED_ADMIN: admin user email to impersonate (e.g., admin@clarascienceacademy.org)
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from flask import current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def _http_error_message_text(exc: HttpError) -> str:
    parts = [str(exc)]
    content = getattr(exc, "content", None)
    if content:
        if isinstance(content, bytes):
            parts.append(content.decode("utf-8", errors="replace"))
        else:
            parts.append(str(content))
    details = getattr(exc, "error_details", None)
    if details:
        parts.append(str(details))
    return " ".join(parts)


def _is_protected_workspace_admin_403(exc: HttpError) -> bool:
    """Google returns 403 with 'Not Authorized' for privileged users (e.g. admins) we cannot move or re-group."""
    status = getattr(getattr(exc, "resp", None), "status", None)
    if status != 403:
        return False
    return "not authorized" in _http_error_message_text(exc).lower()


def _log_skip_protected_admin(user_email: str) -> None:
    current_app.logger.info("[INFO] Skipping protected/admin user: %s", user_email)


DIRECTORY_SCOPES_FULL = [
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.group.member",
    # Required for orgunits.get / orgunits.insert (ensure_ou_exists, OU moves).
    "https://www.googleapis.com/auth/admin.directory.orgunit",
]

# Use with Directory API orgunits.*; avoids threading customer id through callers.
DIRECTORY_CUSTOMER_ID = "my_customer"

# Synthetic OU returned for path "/" so callers never treat the domain root as missing.
_GOOGLE_OU_ROOT_MOCK: Dict[str, Any] = {
    "orgUnitPath": "/",
    "name": "",
}


def _root_ou_resource() -> Dict[str, Any]:
    """Copy so callers cannot mutate the module-level template."""
    return dict(_GOOGLE_OU_ROOT_MOCK)

DIRECTORY_SCOPES_READONLY = [
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
]


def get_directory_service(scopes: Optional[Sequence[str]] = None):
    """
    Builds and returns a Google Directory service object authenticated using
    domain-wide delegation (service account impersonating an admin).

    Args:
        scopes: Optional list of OAuth scopes. If omitted, uses the full set
            required for user + OU + group management.
    """
    key_json = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON")
    key_file = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE")
    delegated_admin = current_app.config.get("GOOGLE_DIRECTORY_DELEGATED_ADMIN")

    if key_json is not None and isinstance(key_json, str):
        key_json = key_json.strip() or None

    if not delegated_admin:
        current_app.logger.error(
            "Directory service not configured. Set GOOGLE_DIRECTORY_DELEGATED_ADMIN."
        )
        return None
    if not key_json and not key_file:
        current_app.logger.error(
            "Directory service not configured. "
            "Set GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON (preferred) or GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE."
        )
        return None

    try:
        effective_scopes = list(scopes) if scopes else DIRECTORY_SCOPES_FULL
        if key_json:
            info = json.loads(key_json)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=effective_scopes
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                key_file, scopes=effective_scopes
            )
        delegated_creds = creds.with_subject(delegated_admin)
        service = build("admin", "directory_v1", credentials=delegated_creds, cache_discovery=False)
        return service
    except Exception as e:
        current_app.logger.error(f"Failed to build Directory service: {e}")
        return None


def create_google_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a Google Workspace user account.

    Args:
        user_data: Directory API user resource body.
            Must include at minimum: primaryEmail, name.givenName, name.familyName, password

    Returns:
        Created user resource dict, or None on failure.
    """
    service = get_directory_service()
    if not service:
        return None

    try:
        created = service.users().insert(body=user_data).execute()
        current_app.logger.info(f"Created Google user {created.get('primaryEmail')}")
        return created
    except HttpError as e:
        current_app.logger.error(f"Directory API error creating user: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Failed to create Google user: {e}")
        return None


def get_google_user(user_email: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a Google Workspace user resource.
    Useful for reading current orgUnitPath / suspended state.
    """
    service = get_directory_service()
    if not service:
        return None

    try:
        return service.users().get(userKey=user_email).execute()
    except HttpError as e:
        current_app.logger.error(f"Directory API error fetching user {user_email}: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Failed to fetch Google user {user_email}: {e}")
        return None


def _normalize_org_unit_path(path: str) -> str:
    """Return a canonical org unit path: leading slash, collapse accidental double slashes."""
    s = (path or "").strip().replace("\\", "/")
    while "//" in s:
        s = s.replace("//", "/")
    parts = [p for p in s.split("/") if p]
    if not parts:
        return "/"
    return "/" + "/".join(parts)


def _lookup_org_unit(service, org_unit_path: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Resolve an OU by path for create-vs-skip decisions.

    Returns:
        ("found", resource) if the OU exists.
        ("missing", None) if the API reports 404 (safe to attempt insert).
        ("error", None) on any other failure — callers must NOT insert (avoids 400 conflicts).
    """
    path = _normalize_org_unit_path(org_unit_path)
    if path == "/":
        # Root cannot be fetched via orgunits.get; treat as present so nothing tries to create it.
        return ("found", _root_ou_resource())
    try:
        resource = (
            service.orgunits()
            .get(customerId=DIRECTORY_CUSTOMER_ID, orgUnitPath=path)
            .execute()
        )
        return ("found", resource)
    except HttpError as e:
        status = int(getattr(getattr(e, "resp", None), "status", None) or 0)
        if status == 404:
            return ("missing", None)
        current_app.logger.error(f"Directory API error fetching OU {path}: {e}")
        return ("error", None)
    except Exception as e:
        current_app.logger.error(f"Failed to fetch OU {path}: {e}")
        return ("error", None)


def get_google_ou(org_unit_path: str) -> Optional[Dict[str, Any]]:
    """
    Fetch an organizational unit by full path (e.g. /Students/Elementary/Class of 2035).
    For path "/", returns a synthetic root OU object (API has no separate root resource).
    Returns None if the OU does not exist (404) or on configuration/API errors.
    """
    service = get_directory_service()
    if not service:
        return None
    return _get_google_ou_with_service(service, org_unit_path)


def _get_google_ou_with_service(service, org_unit_path: str) -> Optional[Dict[str, Any]]:
    status, resource = _lookup_org_unit(service, org_unit_path)
    if status == "found":
        return resource
    return None


def ensure_ou_exists(path: str, service: Any = None) -> bool:
    """
    Ensure every segment of the OU path exists, creating missing units via orgunits.insert.

    Returns False if a required unit could not be created (e.g. 403 Forbidden) or on
    other insert failures. Logs a warning for 403 without raising.
    """
    svc = service or get_directory_service()
    if not svc:
        return False

    norm = _normalize_org_unit_path(path)
    if norm == "/":
        return True

    parts = [p for p in norm.split("/") if p]
    parent_path = "/"
    for segment in parts:
        if parent_path == "/":
            current_path = "/" + segment
        else:
            current_path = parent_path + "/" + segment

        status, _ = _lookup_org_unit(svc, current_path)
        if status == "found":
            parent_path = current_path
            continue
        if status == "error":
            current_app.logger.error(
                f"Could not verify OU {current_path!r} before create; skipping insert to avoid Invalid OU / conflict errors."
            )
            return False

        # Top-level OUs under domain root: parentOrgUnitPath must be exactly "/".
        parent_for_insert = "/" if parent_path == "/" else parent_path
        try:
            svc.orgunits().insert(
                customerId=DIRECTORY_CUSTOMER_ID,
                body={"name": segment, "parentOrgUnitPath": parent_for_insert},
            ).execute()
            current_app.logger.info(f"Created organizational unit {current_path}")
        except HttpError as e:
            err_status = int(getattr(getattr(e, "resp", None), "status", None) or 0)
            if err_status == 403:
                current_app.logger.warning(
                    f"Could not create OU {current_path} under {parent_path!r} (403 Forbidden). "
                    "An admin may need to create this level in the Admin console; user move may fail until then."
                )
                return False
            if err_status == 400 and segment in ("Students", "Staff"):
                retry_status, _ = _lookup_org_unit(svc, current_path)
                if retry_status == "found":
                    current_app.logger.info(
                        f"OU {current_path!r} already exists (recovered after 400 on create); continuing."
                    )
                    parent_path = current_path
                    continue
            if err_status == 409:
                retry_status, _ = _lookup_org_unit(svc, current_path)
                if retry_status == "found":
                    parent_path = current_path
                    continue
            current_app.logger.error(f"Failed to create OU {current_path}: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Failed to create OU {current_path}: {e}")
            return False

        parent_path = current_path

    return True


def move_user_to_ou(user_email: str, ou_path: str) -> Optional[bool]:
    """
    Move an existing user to a different Organizational Unit.
    Ensures the target path exists (creating intermediate OUs when permitted) before moving.

    Returns:
        True if the user was moved, False on failure, None if skipped (403 Not Authorized for admin/privileged users).
    """
    service = get_directory_service()
    if not service:
        return False

    target = _normalize_org_unit_path(ou_path)
    if not ensure_ou_exists(target, service=service):
        current_app.logger.error(
            f"Could not ensure OU exists for move: {target!r} (user {user_email})"
        )
        return False

    try:
        service.users().update(userKey=user_email, body={"orgUnitPath": target}).execute()
        current_app.logger.info(f"Moved {user_email} to OU {target}")
        return True
    except HttpError as e:
        if _is_protected_workspace_admin_403(e):
            _log_skip_protected_admin(user_email)
            return None
        current_app.logger.error(f"Directory API error moving OU for {user_email}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to move {user_email} to OU {ou_path}: {e}")
        return False


def sync_group_members(group_email: str, member_emails: Iterable[str]) -> bool:
    """
    Ensure a Google Group contains exactly the desired member emails (best-effort).
    """
    service = get_directory_service()
    if not service:
        return False

    desired = {m.strip().lower() for m in (member_emails or []) if m and str(m).strip()}
    try:
        current_members: List[str] = []
        page_token = None
        while True:
            resp = service.members().list(groupKey=group_email, pageToken=page_token).execute()
            for m in resp.get("members", []) or []:
                email = (m.get("email") or "").strip().lower()
                if email:
                    current_members.append(email)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        current = set(current_members)

        # Add missing
        for email in sorted(desired - current):
            try:
                service.members().insert(
                    groupKey=group_email,
                    body={"email": email, "role": "MEMBER"},
                ).execute()
                current_app.logger.info(f"Added {email} to group {group_email}")
            except HttpError as e:
                current_app.logger.error(f"Directory API error adding {email} to {group_email}: {e}")

        # Remove extras
        for email in sorted(current - desired):
            try:
                service.members().delete(groupKey=group_email, memberKey=email).execute()
                current_app.logger.info(f"Removed {email} from group {group_email}")
            except HttpError as e:
                current_app.logger.error(f"Directory API error removing {email} from {group_email}: {e}")

        return True
    except HttpError as e:
        current_app.logger.error(f"Directory API error syncing group {group_email}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to sync group {group_email}: {e}")
        return False


def sync_user_groups(user_email: str, group_emails_list: Iterable[str]) -> Optional[bool]:
    """
    Ensure user is a member of exactly the provided groups (best-effort).

    Notes:
    - Adds the user to any missing groups in `group_emails_list`
    - Removes the user from any current groups not in `group_emails_list`

    Returns:
        True on success, False on failure, None if skipped (403 Not Authorized for admin/privileged users).
    """
    service = get_directory_service()
    if not service:
        return False

    desired = {g.strip().lower() for g in (group_emails_list or []) if g and str(g).strip()}
    try:
        # List groups the user currently belongs to
        current_groups: List[str] = []
        page_token = None
        while True:
            try:
                resp = service.groups().list(userKey=user_email, pageToken=page_token).execute()
            except HttpError as e:
                if _is_protected_workspace_admin_403(e):
                    _log_skip_protected_admin(user_email)
                    return None
                current_app.logger.error(f"Directory API error listing groups for {user_email}: {e}")
                return False
            for g in resp.get("groups", []) or []:
                email = (g.get("email") or "").strip().lower()
                if email:
                    current_groups.append(email)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        current = set(current_groups)

        # Add missing memberships
        for group_email in sorted(desired - current):
            try:
                service.members().insert(
                    groupKey=group_email,
                    body={"email": user_email, "role": "MEMBER"},
                ).execute()
                current_app.logger.info(f"Added {user_email} to group {group_email}")
            except HttpError as e:
                if _is_protected_workspace_admin_403(e):
                    _log_skip_protected_admin(user_email)
                    return None
                current_app.logger.error(f"Directory API error adding {user_email} to {group_email}: {e}")

        # Remove extra memberships
        for group_email in sorted(current - desired):
            try:
                service.members().delete(groupKey=group_email, memberKey=user_email).execute()
                current_app.logger.info(f"Removed {user_email} from group {group_email}")
            except HttpError as e:
                if _is_protected_workspace_admin_403(e):
                    _log_skip_protected_admin(user_email)
                    return None
                current_app.logger.error(
                    f"Directory API error removing {user_email} from {group_email}: {e}"
                )

        return True
    except HttpError as e:
        if _is_protected_workspace_admin_403(e):
            _log_skip_protected_admin(user_email)
            return None
        current_app.logger.error(f"Directory API error syncing groups for {user_email}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to sync groups for {user_email}: {e}")
        return False


def ensure_user_in_group(user_email: str, group_email: str) -> bool:
    """
    Ensure a user is a member of a group (add-only; does not remove from other groups).
    Returns True if already a member or successfully added.
    """
    service = get_directory_service()
    if not service:
        return False

    user_email = (user_email or "").strip()
    group_email = (group_email or "").strip()
    if not user_email or not group_email:
        return False

    try:
        # Try to fetch membership first (fast path).
        try:
            service.members().get(groupKey=group_email, memberKey=user_email).execute()
            return True
        except HttpError as e:
            # If not found, we'll insert. Other errors will bubble to outer handler.
            if getattr(e, "status_code", None) != 404:
                raise

        service.members().insert(
            groupKey=group_email,
            body={"email": user_email, "role": "MEMBER"},
        ).execute()
        current_app.logger.info(f"Ensured {user_email} is in group {group_email}")
        return True
    except HttpError as e:
        current_app.logger.error(f"Directory API error ensuring {user_email} in {group_email}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed ensuring {user_email} in {group_email}: {e}")
        return False


def get_google_group(group_email: str) -> Optional[Dict[str, Any]]:
    """Fetch a Google Group resource by email."""
    service = get_directory_service()
    if not service:
        return None
    group_email = (group_email or "").strip()
    if not group_email:
        return None
    try:
        return service.groups().get(groupKey=group_email).execute()
    except HttpError as e:
        current_app.logger.error(f"Directory API error fetching group {group_email}: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Failed to fetch Google group {group_email}: {e}")
        return None


def create_google_group(group_email: str, name: str, description: str = "") -> Optional[Dict[str, Any]]:
    """
    Create a Google Group (best-effort).
    """
    service = get_directory_service()
    if not service:
        return None
    group_email = (group_email or "").strip()
    name = (name or "").strip()
    if not group_email or not name:
        return None
    try:
        body = {"email": group_email, "name": name}
        if description:
            body["description"] = description
        created = service.groups().insert(body=body).execute()
        current_app.logger.info(f"Created Google group {group_email}")
        return created
    except HttpError as e:
        current_app.logger.error(f"Directory API error creating group {group_email}: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Failed to create Google group {group_email}: {e}")
        return None


def suspend_user(user_email: str) -> bool:
    """
    Suspend (disable login for) an existing Google Workspace user.
    """
    service = get_directory_service()
    if not service:
        return False

    try:
        service.users().update(userKey=user_email, body={"suspended": True}).execute()
        current_app.logger.info(f"Suspended Google user {user_email}")
        return True
    except HttpError as e:
        current_app.logger.error(f"Directory API error suspending {user_email}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to suspend {user_email}: {e}")
        return False


def delete_google_user(user_email: str) -> bool:
    """
    Delete a Google Workspace user (irreversible).
    Intended for test cleanup or controlled deprovisioning workflows.
    """
    service = get_directory_service()
    if not service:
        return False

    try:
        service.users().delete(userKey=user_email).execute()
        current_app.logger.info(f"Deleted Google user {user_email}")
        return True
    except HttpError as e:
        current_app.logger.error(f"Directory API error deleting {user_email}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to delete {user_email}: {e}")
        return False

