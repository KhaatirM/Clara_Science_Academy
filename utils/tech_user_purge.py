"""
Remove all database rows that reference a User (and optionally their TeacherStaff profile)
so Tech hard-delete can drop accounts completely.

Uses schema reflection to catch every foreign key to ``user.id`` / ``teacher_staff.id``,
plus targeted cleanup for messaging trees.
"""

from __future__ import annotations

from typing import FrozenSet

from sqlalchemy import MetaData, delete, update
from sqlalchemy import or_

from models import db


def _table_names_case_insensitive(meta: MetaData, name: str) -> str | None:
    """Resolve reflected table name (SQLite lowercases unquoted identifiers)."""
    keys = {k.lower(): k for k in meta.tables.keys()}
    return keys.get(name.lower())


def reflect_purge_references_to_table(
    referred_table: str,
    pk_value: int,
    *,
    skip_tables: FrozenSet[str] | None = None,
    max_rounds: int = 100,
) -> int:
    """
    Null out nullable FKs and delete rows with NOT NULL FKs pointing at ``referred_table.id``.
    Repeats until no rows change (handles simple dependency chains).
    Returns approximate number of row operations performed.
    """
    skip_tables = skip_tables or frozenset()
    meta = MetaData()
    meta.reflect(bind=db.engine)
    ref_key = _table_names_case_insensitive(meta, referred_table)
    if not ref_key:
        return 0
    ref_table_name = meta.tables[ref_key].name

    ops = 0
    for _ in range(max_rounds):
        changed = False
        for table in reversed(meta.sorted_tables):
            if table.name in skip_tables:
                continue
            if table.name == ref_table_name:
                continue
            for fk in table.foreign_keys:
                if fk.column.table.name != ref_table_name:
                    continue
                col = fk.parent
                if fk.column.key != "id":
                    continue
                if col.nullable:
                    res = db.session.execute(update(table).where(col == pk_value).values({col.key: None}))
                else:
                    res = db.session.execute(delete(table).where(col == pk_value))
                rc = res.rowcount
                if rc is not None and rc > 0:
                    changed = True
                    ops += int(rc)
        db.session.flush()
        if not changed:
            break
    return ops


def _message_thread_ids_for_user(user_id: int) -> set[int]:
    from models import Message

    ids: set[int] = set()
    changed = True
    seed = {
        m.id
        for m in Message.query.filter(
            or_(Message.sender_id == user_id, Message.recipient_id == user_id)
        ).all()
    }
    ids |= seed
    while changed:
        changed = False
        for mid in list(ids):
            m = db.session.get(Message, mid)
            if m and m.parent_message_id and m.parent_message_id not in ids:
                ids.add(m.parent_message_id)
                changed = True
        for c in Message.query.filter(Message.parent_message_id.in_(ids)).all():
            if c.id not in ids:
                ids.add(c.id)
                changed = True
    return ids


def _delete_messages_for_ids(message_ids: set[int]) -> None:
    from models import Message, MessageAttachment, MessageReaction, Notification

    while message_ids:
        leaf = None
        for mid in list(message_ids):
            has_child = Message.query.filter(
                Message.parent_message_id == mid,
                Message.id.in_(message_ids),
            ).first()
            if not has_child:
                leaf = mid
                break
        if leaf is None:
            break
        MessageAttachment.query.filter_by(message_id=leaf).delete(synchronize_session=False)
        MessageReaction.query.filter_by(message_id=leaf).delete(synchronize_session=False)
        Notification.query.filter_by(message_id=leaf).update(
            {Notification.message_id: None}, synchronize_session=False
        )
        row = db.session.get(Message, leaf)
        if row:
            db.session.delete(row)
        message_ids.discard(leaf)
        db.session.flush()


def _purge_message_groups_created_by_user(user_id: int) -> None:
    from models import Message, MessageAttachment, MessageGroup, MessageGroupMember, MessageReaction, Notification

    for g in MessageGroup.query.filter_by(created_by=user_id).all():
        for m in Message.query.filter_by(group_id=g.id).all():
            MessageAttachment.query.filter_by(message_id=m.id).delete(synchronize_session=False)
            MessageReaction.query.filter_by(message_id=m.id).delete(synchronize_session=False)
            Notification.query.filter_by(message_id=m.id).update(
                {Notification.message_id: None}, synchronize_session=False
            )
            db.session.delete(m)
        MessageGroupMember.query.filter_by(group_id=g.id).delete(synchronize_session=False)
        db.session.delete(g)
    db.session.flush()


def purge_user_dependencies(user_id: int) -> None:
    """
    Remove every row pointing at this user id, then allow ``User`` row deletion.

    Steps:
    1. Group chats created by the user (messages + memberships).
    2. Direct / threaded messages (sender/recipient/participants).
    3. Student assistant **action logs** (``assistant_user_id``) and **roster** rows
       (``StudentAssistant`` is keyed by ``student_id``, not user id).
    4. Schema-driven sweep for any remaining FK to ``user`` (logs, grades history, comms, etc.).
    """
    from models import (
        MessageGroupMember,
        MessageReaction,
        Notification,
        StudentAssistant,
        StudentAssistantActionLog,
        User,
    )

    skip_reflect: FrozenSet[str] = frozenset({"user", "message"})

    _purge_message_groups_created_by_user(user_id)

    MessageReaction.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    MessageGroupMember.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    Notification.query.filter_by(user_id=user_id).delete(synchronize_session=False)

    StudentAssistantActionLog.query.filter_by(assistant_user_id=user_id).delete(
        synchronize_session=False
    )
    urow = db.session.get(User, user_id)
    if urow and urow.student_id:
        StudentAssistant.query.filter_by(student_id=urow.student_id).delete(
            synchronize_session=False
        )

    mids = _message_thread_ids_for_user(user_id)
    _delete_messages_for_ids(mids)

    reflect_purge_references_to_table("user", user_id, skip_tables=skip_reflect)

    db.session.flush()


def purge_linked_teacher_staff(teacher_staff_id: int) -> None:
    """
    After the User row is gone, remove the staff profile and any rows referencing it.
    Raises ``IntegrityError`` if the profile is still required (e.g. assigned as a class teacher).
    """
    reflect_purge_references_to_table("teacher_staff", teacher_staff_id, skip_tables=frozenset({"user"}))
    db.session.flush()
    ts = db.session.get(TeacherStaff, teacher_staff_id)
    if not ts:
        return
    db.session.delete(ts)
    db.session.flush()
