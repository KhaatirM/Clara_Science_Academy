"""Extract readable text from syllabus uploads and structure an on-page outline."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SYLLABUS_ALLOWED_EXTENSIONS = frozenset({'pdf', 'txt', 'md', 'docx', 'doc'})


def _ext(path: str | Path) -> str:
    return Path(path).suffix.lower().lstrip('.')


def extract_text_from_file(path: str | Path) -> str:
    """Best-effort text extraction for syllabus documents."""
    path = Path(path)
    ext = _ext(path)
    if ext == 'pdf':
        return _extract_pdf(path)
    if ext in ('txt', 'md'):
        return path.read_text(encoding='utf-8', errors='replace')
    if ext == 'docx':
        return _extract_docx(path)
    if ext == 'doc':
        # Legacy .doc is not reliably parseable without extra deps.
        raise ValueError('Please upload a PDF, DOCX, TXT, or Markdown file (.doc is not supported).')
    raise ValueError(f'Unsupported syllabus file type: .{ext}')


def _extract_pdf(path: Path) -> str:
    """Pull text from a PDF using whichever extractor is installed.

    Prefers pdfplumber for layout, then the maintained ``pypdf`` package, then
    the legacy ``PyPDF2`` import name still used by older installs.
    """
    errors: list[str] = []

    try:
        import pdfplumber

        chunks: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                if text.strip():
                    chunks.append(text)
        if chunks:
            return '\n\n'.join(chunks)
        # Empty extract is still "success" — fall through to another reader.
    except Exception as exc:
        errors.append(f'pdfplumber: {exc}')

    for importer in (_import_pypdf, _import_pypdf2):
        try:
            PdfReader = importer()
            reader = PdfReader(str(path))
            chunks = []
            for page in reader.pages:
                text = page.extract_text() or ''
                if text.strip():
                    chunks.append(text)
            return '\n\n'.join(chunks)
        except Exception as exc:
            errors.append(str(exc))

    detail = '; '.join(errors) if errors else 'no PDF library available'
    raise ValueError(f'Could not read PDF text: {detail}')


def _import_pypdf():
    from pypdf import PdfReader

    return PdfReader


def _import_pypdf2():
    from PyPDF2 import PdfReader

    return PdfReader


def _extract_docx(path: Path) -> str:
    try:
        import docx  # python-docx

        document = docx.Document(str(path))
        return '\n'.join(p.text for p in document.paragraphs if (p.text or '').strip())
    except ImportError:
        # Minimal OOXML fallback: unzip and strip XML tags from document.xml
        import zipfile
        import xml.etree.ElementTree as ET

        try:
            with zipfile.ZipFile(path) as zf:
                xml_bytes = zf.read('word/document.xml')
            root = ET.fromstring(xml_bytes)
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            texts = [node.text for node in root.findall('.//w:t', ns) if node.text]
            return '\n'.join(texts)
        except Exception as exc:
            raise ValueError(f'Could not read DOCX text: {exc}') from exc
    except Exception as exc:
        raise ValueError(f'Could not read DOCX text: {exc}') from exc


_HEADING_NUMBERED = re.compile(
    r'^(?:'
    r'(?:section|unit|chapter|part|week|module)\s+\d+[\.:)\-]?\s*'
    r'|\d+(?:\.\d+)*[\.:)\-]\s+'
    r'|[IVXLC]+\.[\s]+'
    r'|[A-Z]\.[\s]+'
    r')',
    re.IGNORECASE,
)
_ALL_CAPS = re.compile(r'^[A-Z0-9][A-Z0-9\s\-/,&:()]{2,80}$')
_MD_HEADING = re.compile(r'^(#{1,3})\s+(.+)$')
_BULLET = re.compile(r'^[\-\*\u2022•]\s+(.+)$')
_NUMBERED_ITEM = re.compile(r'^\d+[\.)]\s+(.+)$')


def build_outline_from_text(text: str, *, source_name: str | None = None) -> dict[str, Any]:
    """
    Turn extracted syllabus text into a hierarchical outline.

    Returns:
      {
        "title": str,
        "sections": [
          {"title": str, "level": 1|2|3, "blocks": [{"type": "paragraph"|"bullet", "text": str}]}
        ]
      }
    """
    raw = (text or '').replace('\r\n', '\n').replace('\r', '\n')
    lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in raw.split('\n')]
    lines = [ln for ln in lines if ln]

    title = source_name or 'Syllabus'
    if lines:
        # Prefer first short non-bullet line as document title.
        for ln in lines[:8]:
            if _BULLET.match(ln) or _NUMBERED_ITEM.match(ln):
                continue
            if len(ln) <= 90:
                title = ln.lstrip('#').strip() or title
                break

    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def start_section(sec_title: str, level: int = 1) -> None:
        nonlocal current
        current = {'title': sec_title, 'level': level, 'blocks': []}
        sections.append(current)

    def ensure_section() -> dict[str, Any]:
        nonlocal current
        if current is None:
            start_section('Overview', 1)
        assert current is not None
        return current

    for ln in lines:
        md = _MD_HEADING.match(ln)
        if md:
            start_section(md.group(2).strip(), min(3, len(md.group(1))))
            continue

        if _HEADING_NUMBERED.match(ln) or (_ALL_CAPS.match(ln) and len(ln.split()) <= 12):
            # Avoid treating the document title as a section twice.
            if sections and sections[0]['title'] == ln and not sections[0]['blocks']:
                continue
            if ln == title and not sections:
                continue
            level = 2 if re.match(r'^\d+\.\d+', ln) or re.match(r'^[A-Z]\.', ln) else 1
            start_section(ln, level)
            continue

        bullet = _BULLET.match(ln) or _NUMBERED_ITEM.match(ln)
        if bullet:
            ensure_section()['blocks'].append({'type': 'bullet', 'text': bullet.group(1).strip()})
            continue

        # Merge short continuation lines into the previous paragraph when sensible.
        sec = ensure_section()
        if (
            sec['blocks']
            and sec['blocks'][-1]['type'] == 'paragraph'
            and len(ln) < 120
            and not ln.endswith('.')
            and not sec['blocks'][-1]['text'].endswith(('.', ':', ';'))
        ):
            sec['blocks'][-1]['text'] = f"{sec['blocks'][-1]['text']} {ln}".strip()
        else:
            sec['blocks'].append({'type': 'paragraph', 'text': ln})

    if not sections:
        sections = [
            {
                'title': 'Syllabus',
                'level': 1,
                'blocks': [{'type': 'paragraph', 'text': raw.strip() or 'No extractable text found.'}],
            }
        ]

    return {'title': title, 'sections': sections}


def outline_to_json(outline: dict[str, Any]) -> str:
    return json.dumps(outline, ensure_ascii=False)


def outline_from_json(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get('sections'), list):
            return data
    except Exception:
        return None
    return None
