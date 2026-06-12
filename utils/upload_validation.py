"""Shared upload extension and MIME validation."""

from __future__ import annotations

from typing import BinaryIO, Optional, Tuple

ALLOWED_EXTENSIONS = frozenset({
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'md',
})

# Browser-reported MIME types we accept per extension (when Content-Type is present).
EXTENSION_MIME_TYPES: dict[str, frozenset[str]] = {
    'txt': frozenset({'text/plain'}),
    'pdf': frozenset({'application/pdf'}),
    'png': frozenset({'image/png'}),
    'jpg': frozenset({'image/jpeg'}),
    'jpeg': frozenset({'image/jpeg'}),
    'gif': frozenset({'image/gif'}),
    'webp': frozenset({'image/webp'}),
    'doc': frozenset({'application/msword'}),
    'docx': frozenset({
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/zip',
    }),
    'xls': frozenset({'application/vnd.ms-excel'}),
    'xlsx': frozenset({
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip',
    }),
    'ppt': frozenset({'application/vnd.ms-powerpoint'}),
    'pptx': frozenset({
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/zip',
    }),
    'md': frozenset({'text/plain', 'text/markdown', 'text/x-markdown'}),
}

_GENERIC_MIMES = frozenset({'', 'application/octet-stream', 'binary/octet-stream'})


def allowed_file(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _file_extension(filename: str) -> str:
    return filename.rsplit('.', 1)[1].lower()


def _read_header(stream: BinaryIO, n: int = 12) -> bytes:
    pos = stream.tell()
    try:
        head = stream.read(n)
        stream.seek(pos)
        return head or b''
    except Exception:
        try:
            stream.seek(pos)
        except Exception:
            pass
        return b''


def _magic_matches(ext: str, header: bytes) -> bool:
    if ext == 'pdf':
        return header.startswith(b'%PDF')
    if ext in ('png',):
        return header.startswith(b'\x89PNG\r\n\x1a\n')
    if ext in ('jpg', 'jpeg'):
        return header.startswith(b'\xff\xd8\xff')
    if ext == 'gif':
        return header.startswith(b'GIF87a') or header.startswith(b'GIF89a')
    if ext == 'webp':
        return len(header) >= 12 and header[:4] == b'RIFF' and header[8:12] == b'WEBP'
    # Office docs and plain text: extension + MIME check only
    return True


def validate_upload_file(file_storage, *, filename: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate an uploaded file's extension, optional Content-Type, and magic bytes
    for common formats. Returns (ok, error_message).
    """
    name = (filename or getattr(file_storage, 'filename', None) or '').strip()
    if not name:
        return False, 'No file selected.'
    if not allowed_file(name):
        return False, f'File type not allowed. Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}'

    ext = _file_extension(name)
    claimed = ''
    if file_storage is not None:
        claimed = (getattr(file_storage, 'content_type', None) or '').split(';')[0].strip().lower()
    allowed_mimes = EXTENSION_MIME_TYPES.get(ext, frozenset())
    if claimed and claimed not in _GENERIC_MIMES and allowed_mimes and claimed not in allowed_mimes:
        return False, f'File content type "{claimed}" is not allowed for .{ext} uploads.'

    if file_storage is not None and hasattr(file_storage, 'read'):
        header = _read_header(file_storage)
        if header and not _magic_matches(ext, header):
            return False, f'File content does not match the .{ext} extension.'

    return True, ''
