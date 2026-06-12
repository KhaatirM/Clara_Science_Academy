"""Password reuse and similarity checks for forced and voluntary changes."""

from __future__ import annotations

import difflib

from werkzeug.security import check_password_hash


SIMILARITY_RATIO_THRESHOLD = 0.72


def passwords_are_too_similar(old_password: str, new_password: str, *, threshold: float = SIMILARITY_RATIO_THRESHOLD) -> bool:
    """Return True when ``new_password`` is substantially similar to ``old_password``."""
    if not old_password or not new_password:
        return False

    old_l = old_password.lower().strip()
    new_l = new_password.lower().strip()
    if not old_l or not new_l:
        return False

    if old_l == new_l:
        return True

    shorter, longer = (old_l, new_l) if len(old_l) <= len(new_l) else (new_l, old_l)
    if len(shorter) >= 4 and shorter in longer:
        return True

    if difflib.SequenceMatcher(None, old_l, new_l).ratio() >= threshold:
        return True

    return False


def validate_new_password_against_old(
    new_password: str,
    *,
    password_hash: str,
    old_plaintext: str | None = None,
) -> tuple[bool, str]:
    """
    Reject exact reuse (via hash) and passwords that are too similar to a known old plaintext.
    """
    if check_password_hash(password_hash, new_password):
        return False, 'Your new password cannot be the same as your current or temporary password.'

    if old_plaintext and passwords_are_too_similar(old_plaintext, new_password):
        return (
            False,
            'Your new password is too similar to your previous password. Choose a more distinct password.',
        )

    return True, ''
