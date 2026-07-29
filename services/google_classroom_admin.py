"""
School-managed Google Classroom via service account + domain-wide delegation.

Creates courses as the delegated Workspace user (botadmin / Directory admin),
adds teachers and students with courses.teachers/students.create (direct enroll —
no invitation accept for same-domain Education users), and deletes courses when
a school year is archived.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

from flask import current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


CLASSROOM_SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses",
    "https://www.googleapis.com/auth/classroom.rosters",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]

# Request Directory + Classroom together. Admin Console authorizes both; requesting only
# the newer Classroom scopes alone can still yield unauthorized_client until DWD fully
# propagates for that scope subset.
CLASSROOM_DWD_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.group.member",
    "https://www.googleapis.com/auth/admin.directory.orgunit",
    *CLASSROOM_SCOPES,
]

_classroom_service_cache: dict[tuple[str, str], Any] = {}


def _http_status(exc: HttpError) -> int | None:
    return getattr(getattr(exc, "resp", None), "status", None) or getattr(exc, "status_code", None)


def _http_text(exc: HttpError) -> str:
    parts = [str(exc)]
    content = getattr(exc, "content", None)
    if content:
        if isinstance(content, bytes):
            parts.append(content.decode("utf-8", errors="replace"))
        else:
            parts.append(str(content))
    return " ".join(parts).lower()


def _already_exists(exc: HttpError) -> bool:
    status = _http_status(exc)
    if status == 409:
        return True
    text = _http_text(exc)
    return "already exists" in text or "already a member" in text or "already enrolled" in text


def _not_found(exc: HttpError) -> bool:
    return _http_status(exc) == 404


def _sa_identity_from_config() -> tuple[str | None, str | None]:
    """Return (client_email, client_id) from the Directory SA JSON/file — safe to log."""
    key_json = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON")
    key_file = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE")
    if key_json is not None and isinstance(key_json, str):
        key_json = key_json.strip() or None
    try:
        if key_json:
            info = json.loads(key_json)
        elif key_file:
            with open(key_file, encoding="utf-8") as fh:
                info = json.load(fh)
        else:
            return None, None
        return (
            (info.get("client_email") or None),
            (str(info.get("client_id")) if info.get("client_id") is not None else None),
        )
    except Exception:
        return None, None


def classroom_owner_email() -> str | None:
    """Workspace user that owns school-managed courses (defaults to Directory admin)."""
    email = (
        current_app.config.get("GOOGLE_CLASSROOM_DELEGATED_USER")
        or current_app.config.get("GOOGLE_DIRECTORY_DELEGATED_ADMIN")
        or ""
    ).strip()
    return email or None


def get_classroom_admin_service(scopes: Optional[Sequence[str]] = None):
    """
    Classroom API client impersonating the school botadmin / delegated admin.
    Reuses the same service-account key as Directory (domain-wide delegation).
    """
    key_json = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON")
    key_file = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE")
    subject = classroom_owner_email()

    if key_json is not None and isinstance(key_json, str):
        key_json = key_json.strip() or None

    if not subject:
        current_app.logger.error(
            "Classroom admin not configured. Set GOOGLE_CLASSROOM_DELEGATED_USER "
            "or GOOGLE_DIRECTORY_DELEGATED_ADMIN."
        )
        return None
    if not key_json and not key_file:
        current_app.logger.error(
            "Classroom admin not configured. Set GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON "
            "or GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE."
        )
        return None

    effective_scopes = list(scopes) if scopes else list(CLASSROOM_DWD_SCOPES)
    cache_key = (subject.lower(), ",".join(sorted(effective_scopes)))
    if cache_key in _classroom_service_cache:
        return _classroom_service_cache[cache_key]

    sa_email, sa_client_id = _sa_identity_from_config()
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
        delegated = creds.with_subject(subject)

        # Force token exchange now so auth failures show clear diagnostics.
        try:
            from google.auth.transport.requests import Request as GoogleAuthRequest

            delegated.refresh(GoogleAuthRequest())
        except Exception as refresh_exc:
            current_app.logger.error(
                "Classroom DWD token refresh failed (subject=%s sa=%s client_id=%s scopes=%s): %s",
                subject,
                sa_email,
                sa_client_id,
                effective_scopes,
                refresh_exc,
            )
            raise

        service = build("classroom", "v1", credentials=delegated, cache_discovery=False)
        _classroom_service_cache[cache_key] = service
        current_app.logger.info(
            "Classroom admin service ready (subject=%s sa=%s client_id=%s)",
            subject,
            sa_email,
            sa_client_id,
        )
        return service
    except Exception as exc:
        current_app.logger.error(
            "Failed to build Classroom admin service (subject=%s sa=%s client_id=%s): %s",
            subject,
            sa_email,
            sa_client_id,
            exc,
        )
        return None


def _probe_dwd_token(label: str, scopes: Sequence[str], subject: str) -> str:
    """Attempt a JWT access-token refresh; return OK / FAIL:reason for logs."""
    key_json = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_JSON")
    key_file = current_app.config.get("GOOGLE_DIRECTORY_SERVICE_ACCOUNT_FILE")
    if key_json is not None and isinstance(key_json, str):
        key_json = key_json.strip() or None
    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest

        if key_json:
            info = json.loads(key_json)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=list(scopes)
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                key_file, scopes=list(scopes)
            )
        creds.with_subject(subject).refresh(GoogleAuthRequest())
        return f"{label}=OK"
    except Exception as exc:
        return f"{label}=FAIL:{exc}"


def log_classroom_dwd_diagnostics() -> None:
    """Compare Directory vs Classroom DWD token exchange (helps unauthorized_client)."""
    subject = classroom_owner_email() or "?"
    sa_email, sa_client_id = _sa_identity_from_config()
    directory_scopes = [
        "https://www.googleapis.com/auth/admin.directory.user",
        "https://www.googleapis.com/auth/admin.directory.group",
        "https://www.googleapis.com/auth/admin.directory.group.member",
        "https://www.googleapis.com/auth/admin.directory.orgunit",
    ]
    results = [
        _probe_dwd_token("directory", directory_scopes, subject),
        _probe_dwd_token("classroom_only", CLASSROOM_SCOPES, subject),
        _probe_dwd_token("classroom_dwd", CLASSROOM_DWD_SCOPES, subject),
        # Narrowest Classroom scope — if this fails, Admin DWD Classroom grant is broken.
        _probe_dwd_token(
            "courses_only",
            ["https://www.googleapis.com/auth/classroom.courses"],
            subject,
        ),
    ]
    current_app.logger.error(
        "Classroom DWD probe (subject=%s sa=%s client_id=%s): %s",
        subject,
        sa_email,
        sa_client_id,
        " | ".join(results),
    )


def create_course_as_admin(
    *,
    name: str,
    section: str | None = None,
    description: str | None = None,
    room: str | None = None,
) -> dict[str, Any] | None:
    """Create an ACTIVE course owned by the delegated botadmin user."""
    # Drop cached client so scope/config changes take effect without process recycle.
    _classroom_service_cache.clear()
    service = get_classroom_admin_service()
    owner = classroom_owner_email()
    if not service or not owner:
        log_classroom_dwd_diagnostics()
        return None
    body: dict[str, Any] = {
        "name": (name or "Class").strip()[:100] or "Class",
        "ownerId": owner,
        "courseState": "ACTIVE",
    }
    if section:
        body["section"] = str(section)[:100]
    if description:
        body["description"] = str(description)[:1000]
        body["descriptionHeading"] = (name or "Class")[:100]
    if room:
        body["room"] = str(room)[:100]
    try:
        course = service.courses().create(body=body).execute()
        current_app.logger.info(
            "Created school-managed Google Classroom %s (%s)",
            course.get("id"),
            course.get("name"),
        )
        return course
    except Exception as exc:
        sa_email, sa_client_id = _sa_identity_from_config()
        current_app.logger.error(
            "Failed to create school-managed Classroom (owner=%s sa=%s client_id=%s): %s",
            owner,
            sa_email,
            sa_client_id,
            exc,
        )
        log_classroom_dwd_diagnostics()
        return None


def get_course(course_id: str) -> dict[str, Any] | None:
    service = get_classroom_admin_service()
    if not service or not course_id:
        return None
    try:
        return service.courses().get(id=course_id).execute()
    except HttpError as exc:
        if _not_found(exc):
            return None
        current_app.logger.error("Failed to get Classroom %s: %s", course_id, exc)
        return None
    except Exception as exc:
        current_app.logger.error("Failed to get Classroom %s: %s", course_id, exc)
        return None


def delete_course(course_id: str) -> bool:
    """Permanently delete a Google Classroom course. True if deleted or already gone."""
    service = get_classroom_admin_service()
    if not service or not course_id:
        return False
    try:
        service.courses().delete(id=course_id).execute()
        current_app.logger.info("Deleted Google Classroom %s", course_id)
        return True
    except HttpError as exc:
        if _not_found(exc):
            return True
        # Some courses must be archived before delete.
        try:
            service.courses().patch(
                id=course_id,
                updateMask="courseState",
                body={"courseState": "ARCHIVED"},
            ).execute()
            service.courses().delete(id=course_id).execute()
            current_app.logger.info("Archived then deleted Google Classroom %s", course_id)
            return True
        except Exception as exc2:
            current_app.logger.error(
                "Failed to delete Google Classroom %s: %s / %s", course_id, exc, exc2
            )
            return False
    except Exception as exc:
        current_app.logger.error("Failed to delete Google Classroom %s: %s", course_id, exc)
        return False


def add_teacher_direct(course_id: str, teacher_email: str) -> bool:
    """
    Add a teacher to the course directly (no invitation) for same-domain Education users
    when called as a domain admin via DWD.
    """
    service = get_classroom_admin_service()
    email = (teacher_email or "").strip()
    if not service or not course_id or not email:
        return False
    owner = (classroom_owner_email() or "").lower()
    if email.lower() == owner:
        return True
    try:
        service.courses().teachers().create(
            courseId=course_id,
            body={"userId": email},
        ).execute()
        current_app.logger.info("Added teacher %s to Classroom %s", email, course_id)
        return True
    except HttpError as exc:
        if _already_exists(exc):
            return True
        current_app.logger.error(
            "Failed to add teacher %s to Classroom %s: %s", email, course_id, exc
        )
        return False
    except Exception as exc:
        current_app.logger.error(
            "Failed to add teacher %s to Classroom %s: %s", email, course_id, exc
        )
        return False


def add_student_direct(course_id: str, student_email: str) -> bool:
    """Add a student directly (no invitation accept) for same-domain Education users."""
    service = get_classroom_admin_service()
    email = (student_email or "").strip()
    if not service or not course_id or not email:
        return False
    try:
        service.courses().students().create(
            courseId=course_id,
            body={"userId": email},
        ).execute()
        current_app.logger.info("Added student %s to Classroom %s", email, course_id)
        return True
    except HttpError as exc:
        if _already_exists(exc):
            return True
        current_app.logger.error(
            "Failed to add student %s to Classroom %s: %s", email, course_id, exc
        )
        return False
    except Exception as exc:
        current_app.logger.error(
            "Failed to add student %s to Classroom %s: %s", email, course_id, exc
        )
        return False


def remove_student(course_id: str, student_email: str) -> bool:
    service = get_classroom_admin_service()
    email = (student_email or "").strip()
    if not service or not course_id or not email:
        return False
    try:
        service.courses().students().delete(courseId=course_id, userId=email).execute()
        return True
    except HttpError as exc:
        if _not_found(exc):
            return True
        current_app.logger.warning(
            "Failed to remove student %s from Classroom %s: %s", email, course_id, exc
        )
        return False
    except Exception as exc:
        current_app.logger.warning(
            "Failed to remove student %s from Classroom %s: %s", email, course_id, exc
        )
        return False


def remove_teacher(course_id: str, teacher_email: str) -> bool:
    service = get_classroom_admin_service()
    email = (teacher_email or "").strip()
    if not service or not course_id or not email:
        return False
    owner = (classroom_owner_email() or "").lower()
    if email.lower() == owner:
        return True
    try:
        service.courses().teachers().delete(courseId=course_id, userId=email).execute()
        return True
    except HttpError as exc:
        if _not_found(exc):
            return True
        current_app.logger.warning(
            "Failed to remove teacher %s from Classroom %s: %s", email, course_id, exc
        )
        return False
    except Exception as exc:
        current_app.logger.warning(
            "Failed to remove teacher %s from Classroom %s: %s", email, course_id, exc
        )
        return False


def list_course_student_emails(course_id: str) -> set[str]:
    service = get_classroom_admin_service()
    if not service or not course_id:
        return set()
    emails: set[str] = set()
    page_token = None
    try:
        while True:
            kwargs: dict[str, Any] = {"courseId": course_id, "pageSize": 100}
            if page_token:
                kwargs["pageToken"] = page_token
            result = service.courses().students().list(**kwargs).execute()
            for row in result.get("students") or []:
                profile = row.get("profile") or {}
                email = (profile.get("emailAddress") or row.get("userId") or "").strip()
                if email and "@" in email:
                    emails.add(email.lower())
            page_token = result.get("nextPageToken")
            if not page_token:
                break
    except Exception as exc:
        current_app.logger.warning("Failed listing students for Classroom %s: %s", course_id, exc)
    return emails


def list_course_teacher_emails(course_id: str) -> set[str]:
    service = get_classroom_admin_service()
    if not service or not course_id:
        return set()
    emails: set[str] = set()
    page_token = None
    try:
        while True:
            kwargs: dict[str, Any] = {"courseId": course_id, "pageSize": 100}
            if page_token:
                kwargs["pageToken"] = page_token
            result = service.courses().teachers().list(**kwargs).execute()
            for row in result.get("teachers") or []:
                profile = row.get("profile") or {}
                email = (profile.get("emailAddress") or row.get("userId") or "").strip()
                if email and "@" in email:
                    emails.add(email.lower())
            page_token = result.get("nextPageToken")
            if not page_token:
                break
    except Exception as exc:
        current_app.logger.warning("Failed listing teachers for Classroom %s: %s", course_id, exc)
    return emails
