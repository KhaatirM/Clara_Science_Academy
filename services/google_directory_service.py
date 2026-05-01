"""
Google Directory Service Module

This module provides helper functions to interact with the Google Admin SDK
Directory API using a Service Account with domain-wide delegation.

Expected config keys (Flask `current_app.config`):
- GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE: path to service account JSON key file
- GOOGLE_DIRECTORY_DELEGATED_ADMIN: admin user email to impersonate (e.g., admin@clarascienceacademy.org)
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence

from flask import current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


DIRECTORY_SCOPES_FULL = [
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.group.member",
    "https://www.googleapis.com/auth/admin.directory.orgunit",
]

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
    key_file = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE")
    key_json = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON")
    delegated_admin = current_app.config.get("GOOGLE_DIRECTORY_DELEGATED_ADMIN")

    if (not key_file and not key_json) or not delegated_admin:
        current_app.logger.error(
            "Directory service not configured. "
            "Set GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON (preferred) or GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE, "
            "and GOOGLE_DIRECTORY_DELEGATED_ADMIN."
        )
        return None

    try:
        effective_scopes = list(scopes) if scopes else DIRECTORY_SCOPES_FULL
        if key_json:
            info = json.loads(key_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=effective_scopes)
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


def move_user_to_ou(user_email: str, ou_path: str) -> bool:
    """
    Move an existing user to a different Organizational Unit.
    """
    service = get_directory_service()
    if not service:
        return False

    try:
        service.users().update(userKey=user_email, body={"orgUnitPath": ou_path}).execute()
        current_app.logger.info(f"Moved {user_email} to OU {ou_path}")
        return True
    except HttpError as e:
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


def sync_user_groups(user_email: str, group_emails_list: Iterable[str]) -> bool:
    """
    Ensure user is a member of exactly the provided groups (best-effort).

    Notes:
    - Adds the user to any missing groups in `group_emails_list`
    - Removes the user from any current groups not in `group_emails_list`
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
            resp = service.groups().list(userKey=user_email, pageToken=page_token).execute()
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
                current_app.logger.error(f"Directory API error adding {user_email} to {group_email}: {e}")

        # Remove extra memberships
        for group_email in sorted(current - desired):
            try:
                service.members().delete(groupKey=group_email, memberKey=user_email).execute()
                current_app.logger.info(f"Removed {user_email} from group {group_email}")
            except HttpError as e:
                current_app.logger.error(
                    f"Directory API error removing {user_email} from {group_email}: {e}"
                )

        return True
    except HttpError as e:
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

