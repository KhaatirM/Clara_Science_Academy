"""Cryptographically secure temporary passwords for new portal accounts."""

from __future__ import annotations

import secrets
import string

# Alphabet avoids ambiguous characters (0/O, 1/l/I) for easier handoff to users.
_TEMP_ALPHABET = string.ascii_letters + string.digits
_TEMP_ALPHABET = _TEMP_ALPHABET.replace("0", "").replace("O", "").replace("o", "")
_TEMP_ALPHABET = _TEMP_ALPHABET.replace("1", "").replace("l", "").replace("I", "")


def generate_temporary_password(length: int = 12) -> str:
    """Return a random temporary password suitable for first-time login."""
    if length < 8:
        length = 8
    return "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(length))
