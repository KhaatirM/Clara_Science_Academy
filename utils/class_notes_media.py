"""Helpers for class notes media (extensions, video duration)."""

from __future__ import annotations

import struct
from typing import Optional

NOTES_MAX_VIDEO_SECONDS = 10 * 60  # 10 minutes

NOTES_DOC_EXTENSIONS = frozenset({
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'md',
})
NOTES_IMAGE_EXTENSIONS = frozenset({'png', 'jpg', 'jpeg', 'gif', 'webp'})
NOTES_VIDEO_EXTENSIONS = frozenset({'mp4', 'webm', 'mov'})
NOTES_ALLOWED_EXTENSIONS = NOTES_DOC_EXTENSIONS | NOTES_IMAGE_EXTENSIONS | NOTES_VIDEO_EXTENSIONS

NOTES_EXTENSION_MIME_TYPES: dict[str, frozenset[str]] = {
    'pdf': frozenset({'application/pdf'}),
    'doc': frozenset({'application/msword'}),
    'docx': frozenset({
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/zip',
    }),
    'ppt': frozenset({'application/vnd.ms-powerpoint'}),
    'pptx': frozenset({
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/zip',
    }),
    'xls': frozenset({'application/vnd.ms-excel'}),
    'xlsx': frozenset({
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip',
    }),
    'txt': frozenset({'text/plain'}),
    'md': frozenset({'text/plain', 'text/markdown', 'text/x-markdown'}),
    'png': frozenset({'image/png'}),
    'jpg': frozenset({'image/jpeg'}),
    'jpeg': frozenset({'image/jpeg'}),
    'gif': frozenset({'image/gif'}),
    'webp': frozenset({'image/webp'}),
    'mp4': frozenset({'video/mp4', 'application/mp4', 'video/quicktime'}),
    'webm': frozenset({'video/webm'}),
    'mov': frozenset({'video/quicktime', 'video/mp4'}),
}


def notes_media_kind(ext: str) -> str:
    e = (ext or '').lower()
    if e in NOTES_VIDEO_EXTENSIONS:
        return 'video'
    if e in NOTES_IMAGE_EXTENSIONS:
        return 'image'
    if e in NOTES_DOC_EXTENSIONS:
        return 'document'
    return 'other'


def notes_media_kind_for_drive(mime_type: str | None, name: str | None) -> str:
    """Classify a Drive file, preferring its MIME type and falling back to the name."""
    mime = (mime_type or '').lower()
    if mime.startswith('video/'):
        return 'video'
    if mime.startswith('image/'):
        return 'image'
    if mime == 'application/pdf' or mime.startswith('text/'):
        return 'document'
    if mime.startswith('application/vnd.google-apps.'):
        # Docs, Slides, Sheets and Drawings all export to a document format.
        return 'document' if mime != 'application/vnd.google-apps.folder' else 'other'
    if mime.startswith('application/vnd.openxmlformats') or mime.startswith('application/vnd.ms-'):
        return 'document'
    if name and '.' in name:
        return notes_media_kind(name.rsplit('.', 1)[-1])
    return 'other'


def _read_mp4_duration_seconds(path: str) -> Optional[float]:
    """Best-effort MP4/MOV duration from the mvhd atom (no ffmpeg required)."""
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except OSError:
        return None
    if len(data) < 16:
        return None

    # Find 'mvhd' atom
    idx = data.find(b'mvhd')
    if idx < 4:
        return None
    # Atom size is 4 bytes before type
    try:
        version = data[idx + 4]
        if version == 0:
            # timescale at +16, duration at +20 (both uint32)
            timescale = struct.unpack('>I', data[idx + 16 : idx + 20])[0]
            duration = struct.unpack('>I', data[idx + 20 : idx + 24])[0]
        elif version == 1:
            timescale = struct.unpack('>I', data[idx + 28 : idx + 32])[0]
            duration = struct.unpack('>Q', data[idx + 32 : idx + 40])[0]
        else:
            return None
        if not timescale:
            return None
        return float(duration) / float(timescale)
    except (struct.error, IndexError, ZeroDivisionError):
        return None


def probe_video_duration_seconds(path: str, ext: str) -> Optional[float]:
    e = (ext or '').lower()
    if e in ('mp4', 'mov'):
        return _read_mp4_duration_seconds(path)
    return None


def validate_notes_extension(filename: str) -> tuple[bool, str | None, str]:
    if not filename or '.' not in filename:
        return False, 'Choose a file to upload.', ''
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext not in NOTES_ALLOWED_EXTENSIONS:
        return (
            False,
            'Upload a document, slide deck, image, or short video (PDF, Office, images, MP4/WebM/MOV).',
            ext,
        )
    return True, None, ext
