"""
Merge two staff User rows into one (same person, duplicate accounts).

Use on Render shell or locally with DATABASE_URL / Flask config set:

  python scripts/merge_duplicate_staff_users.py --keep-id 12 --merge-id 34

Optional:

  --new-username alice.staff   (default: keep user's username)
  --password 'PlaintextPass!'   (default: generate a random password)

Prints the final username and password to stdout. Refuses to merge Student accounts.

If both rows reference different teacher_staff_id values, the script keeps the keep-id
record's link unless keep has none, then it copies merge's — and prints a loud warning.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from utils.user_roles import canonical_role_label, parse_secondary_roles
from models import (
    ActivityLog,
    AdminAuditLog,
    Announcement,
    AnnouncementReadReceipt,
    Assignment,
    BugReport,
    GradeHistory,
    GroupAssignment,
    MaintenanceMode,
    Message,
    MessageGroup,
    MessageGroupMember,
    MessageReaction,
    Notification,
    QuestionBank,
    SchoolDayAttendance,
    StudentAssistant,
    StudentAssistantActionLog,
    SystemConfig,
    User,
)


def _parse_perm_list(raw):
    if not raw:
        return []
    try:
        if isinstance(raw, (list, tuple)):
            perms = list(raw)
        else:
            perms = json.loads(raw)
        if not isinstance(perms, list):
            return []
        return [str(p).strip() for p in perms if isinstance(p, str) and p.strip()]
    except Exception:
        return []


def _union_permissions(a: User, b: User) -> str | None:
    u = set(_parse_perm_list(a.permissions))
    u.update(_parse_perm_list(b.permissions))
    if not u:
        return None
    return json.dumps(sorted(u))


def _merge_secondary_roles(keep: User, merge: User) -> str | None:
    """Union secondary roles using canonical labels so Tech vs School Admin detection matches the web app."""
    primary_canon = canonical_role_label(keep.role)
    extra: set[str] = set()
    for s in parse_secondary_roles(keep.secondary_roles):
        c = canonical_role_label(s)
        if c and c != primary_canon:
            extra.add(c)
    for s in parse_secondary_roles(merge.secondary_roles):
        c = canonical_role_label(s)
        if c and c != primary_canon:
            extra.add(c)
    mr = canonical_role_label(merge.role)
    if mr and mr != primary_canon:
        extra.add(mr)
    extra.discard(primary_canon)
    if not extra:
        return None
    return json.dumps(sorted(extra))


def _dedupe_message_group_members(keep_id: int, merge_id: int) -> None:
    rows = MessageGroupMember.query.filter_by(user_id=merge_id).all()
    for row in rows:
        dup = MessageGroupMember.query.filter_by(group_id=row.group_id, user_id=keep_id).first()
        if dup:
            db.session.delete(row)
        else:
            row.user_id = keep_id


def _dedupe_message_reactions(keep_id: int, merge_id: int) -> None:
    rows = MessageReaction.query.filter_by(user_id=merge_id).all()
    for row in rows:
        dup = MessageReaction.query.filter_by(
            message_id=row.message_id, user_id=keep_id, emoji=row.emoji
        ).first()
        if dup:
            db.session.delete(row)
        else:
            row.user_id = keep_id


def _dedupe_announcement_read_receipts(keep_id: int, merge_id: int) -> None:
    rows = AnnouncementReadReceipt.query.filter_by(user_id=merge_id).all()
    for row in rows:
        dup = AnnouncementReadReceipt.query.filter_by(
            announcement_id=row.announcement_id, user_id=keep_id
        ).first()
        if dup:
            db.session.delete(row)
        else:
            row.user_id = keep_id


def _bulk_update(model, column: str, keep_id: int, merge_id: int) -> None:
    col = getattr(model, column)
    model.query.filter(col == merge_id).update({column: keep_id}, synchronize_session=False)


def run(keep_id: int, merge_id: int, new_username: str | None, plain_password: str | None) -> None:
    if keep_id == merge_id:
        raise SystemExit('keep-id and merge-id must differ')

    keep = db.session.get(User, keep_id)
    merge = db.session.get(User, merge_id)
    if not keep or not merge:
        raise SystemExit('One or both user ids do not exist.')

    if keep.role == 'Student' or merge.role == 'Student':
        raise SystemExit('Refusing to merge: one or both accounts are Students.')

    print(f'KEEP  user {keep.id} username={keep.username!r} role={keep.role!r} teacher_staff_id={keep.teacher_staff_id}')
    print(f'MERGE user {merge.id} username={merge.username!r} role={merge.role!r} teacher_staff_id={merge.teacher_staff_id}')

    if keep.teacher_staff_id and merge.teacher_staff_id and keep.teacher_staff_id != merge.teacher_staff_id:
        print(
            '\n*** WARNING: both users reference different teacher_staff rows. '
            'Keeping keep-id teacher_staff_id. Review TeacherStaff records manually if needed.\n'
        )
    elif not keep.teacher_staff_id and merge.teacher_staff_id:
        keep.teacher_staff_id = merge.teacher_staff_id

    _dedupe_message_group_members(keep.id, merge.id)
    _dedupe_message_reactions(keep.id, merge.id)
    _dedupe_announcement_read_receipts(keep.id, merge.id)

    pairs = [
        (Assignment, 'created_by'),
        (Assignment, 'assistant_approval_reviewed_by_user_id'),
        (GroupAssignment, 'created_by'),
        (GroupAssignment, 'assistant_approval_reviewed_by_user_id'),
        (GradeHistory, 'changed_by'),
        (AdminAuditLog, 'user_id'),
        (Announcement, 'sender_id'),
        (Notification, 'user_id'),
        (MaintenanceMode, 'initiated_by'),
        (ActivityLog, 'user_id'),
        (Message, 'sender_id'),
        (Message, 'recipient_id'),
        (MessageGroup, 'created_by'),
        (StudentAssistant, 'assigned_by_user_id'),
        (StudentAssistantActionLog, 'assistant_user_id'),
        (BugReport, 'user_id'),
        (BugReport, 'resolved_by'),
        (SchoolDayAttendance, 'recorded_by'),
        (SystemConfig, 'updated_by'),
        (QuestionBank, 'created_by'),
    ]
    for model, col in pairs:
        _bulk_update(model, col, keep.id, merge.id)

    keep.permissions = _union_permissions(keep, merge)
    keep.secondary_roles = _merge_secondary_roles(keep, merge)

    if not keep.email and merge.email:
        keep.email = merge.email
    if not keep.google_workspace_email and merge.google_workspace_email:
        keep.google_workspace_email = merge.google_workspace_email
    if not keep._google_refresh_token and merge._google_refresh_token:
        keep._google_refresh_token = merge._google_refresh_token

    keep.login_count = max(keep.login_count or 0, merge.login_count or 0)
    keep.is_temporary_password = bool(keep.is_temporary_password or merge.is_temporary_password)

    if new_username and new_username.strip() and new_username.strip() != keep.username:
        taken = User.query.filter(User.username == new_username.strip(), User.id != keep.id).first()
        if taken:
            raise SystemExit(f'Username {new_username!r} is already taken.')
        keep.username = new_username.strip()

    pwd = plain_password if plain_password else secrets.token_urlsafe(16)
    keep.password_hash = generate_password_hash(pwd)

    # Retire duplicate TeacherStaff row (same person had two profiles / two logins)
    kt = keep.teacher_staff_id
    mt = merge.teacher_staff_id
    if kt and mt and mt != kt:
        from utils.merge_teacher_staff_cleanup import consolidate_duplicate_teacher_staff_rows

        consolidate_duplicate_teacher_staff_rows(mt, kt)

    db.session.delete(merge)
    db.session.commit()

    print('\n--- Done ---')
    print(f'Consolidated user id: {keep.id}')
    print(f'Username: {keep.username}')
    print(f'Password: {pwd}')
    print(f'Primary role (column ``role``): {keep.role!r}')
    print(f'secondary_roles (JSON): {keep.secondary_roles!r}')
    from utils.user_roles import staff_must_choose_dashboard

    print(
        'Dashboard picker / Switch dashboard expected:',
        staff_must_choose_dashboard(keep),
        '(needs Tech or IT Support plus School Administrator or Director)',
    )
    print('Store this password securely; it will not be shown again.')


def main():
    p = argparse.ArgumentParser(description='Merge two staff User rows into keep-id.')
    p.add_argument('--keep-id', type=int, required=True)
    p.add_argument('--merge-id', type=int, required=True)
    p.add_argument('--new-username', default=None)
    p.add_argument('--password', default=None, help='New plaintext password for consolidated account')
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        run(args.keep_id, args.merge_id, args.new_username, args.password)


if __name__ == '__main__':
    main()
