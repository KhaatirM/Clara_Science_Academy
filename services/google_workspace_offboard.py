"""
Workspace offboarding: move OU → suspend → queue license revocation after 24 hours.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from flask import current_app

from extensions import db
from models import GoogleWorkspaceOffboardJob
from services.google_directory_service import move_user_to_ou, suspend_user
from services.google_ou_policy import STAFF_OU_BASE, STAFF_OU_TERMINATED_REMOVED

LICENSE_REMOVAL_DELAY = timedelta(hours=24)
TERMINATED_STAFF_OU = f"{STAFF_OU_BASE}/{STAFF_OU_TERMINATED_REMOVED}"


def enqueue_workspace_license_removal(
    email: str,
    *,
    kind: str,
    related_id: Optional[int] = None,
    commit: bool = False,
) -> Optional[GoogleWorkspaceOffboardJob]:
    """
    Schedule license revocation 24h after now (caller should already have suspended).

    Idempotent for a pending job on the same email.
    """
    addr = (email or "").strip().lower()
    if not addr or "@" not in addr:
        return None

    existing = (
        GoogleWorkspaceOffboardJob.query.filter_by(email=addr, status="pending")
        .order_by(GoogleWorkspaceOffboardJob.id.desc())
        .first()
    )
    if existing:
        return existing

    now = datetime.utcnow()
    job = GoogleWorkspaceOffboardJob(
        email=addr,
        kind=(kind or "unknown")[:20],
        related_id=related_id,
        suspended_at=now,
        license_remove_after=now + LICENSE_REMOVAL_DELAY,
        status="pending",
    )
    db.session.add(job)
    if commit:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.warning(
                "enqueue_workspace_license_removal commit failed for %s: %s", addr, e
            )
            return None
    return job


def suspend_and_queue_license_removal(
    email: str,
    *,
    kind: str,
    related_id: Optional[int] = None,
    commit_queue: bool = False,
) -> bool:
    """Suspend Directory user, then enqueue 24h license removal."""
    addr = (email or "").strip()
    if not addr:
        return False
    try:
        ok = suspend_user(addr)
    except Exception as e:
        current_app.logger.warning("suspend failed for %s: %s", addr, e)
        return False
    if ok:
        enqueue_workspace_license_removal(
            addr, kind=kind, related_id=related_id, commit=commit_queue
        )
    return bool(ok)


def offboard_staff_workspace_account(
    email: str,
    *,
    staff_id: Optional[int] = None,
    commit_queue: bool = False,
) -> bool:
    """
    Move staff to /Staff/Terminated & Removed, suspend, queue license removal.
    """
    addr = (email or "").strip()
    if not addr:
        return False
    try:
        move_user_to_ou(addr, TERMINATED_STAFF_OU)
    except Exception as e:
        current_app.logger.warning(
            "OU move to Terminated & Removed failed for %s: %s", addr, e
        )
    return suspend_and_queue_license_removal(
        addr, kind="staff", related_id=staff_id, commit_queue=commit_queue
    )


def process_due_license_removals(*, limit: int = 100) -> dict:
    """
    Cron helper: revoke licenses for jobs past ``license_remove_after``.
    """
    from services.google_licensing_service import revoke_all_education_licenses

    now = datetime.utcnow()
    q = (
        GoogleWorkspaceOffboardJob.query.filter(
            GoogleWorkspaceOffboardJob.status == "pending",
            GoogleWorkspaceOffboardJob.license_remove_after <= now,
        )
        .order_by(GoogleWorkspaceOffboardJob.license_remove_after.asc())
        .limit(max(1, int(limit)))
    )
    jobs = q.all()
    done = 0
    failed = 0
    skipped = 0

    for job in jobs:
        try:
            result = revoke_all_education_licenses(job.email)
            if result.get("ok") or result.get("revoked", 0) > 0:
                job.status = "done"
                job.license_removed_at = datetime.utcnow()
                job.last_error = None
                done += 1
            elif result.get("attempted", 0) == 0:
                job.status = "skipped"
                job.last_error = "no licensing client or empty email"
                skipped += 1
            else:
                job.status = "failed"
                job.last_error = ", ".join(result.get("errors") or ["revoke failed"])
                failed += 1
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            failed += 1
            try:
                job = db.session.get(GoogleWorkspaceOffboardJob, job.id)
                if job:
                    job.status = "failed"
                    job.last_error = str(e)[:500]
                    db.session.commit()
            except Exception:
                db.session.rollback()
            current_app.logger.exception(
                "process_due_license_removals failed for job %s (%s)",
                getattr(job, "id", None),
                getattr(job, "email", None),
            )

    return {
        "ok": True,
        "processed": len(jobs),
        "done": done,
        "failed": failed,
        "skipped": skipped,
    }
