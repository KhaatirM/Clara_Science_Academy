"""WeasyPrint PDF generation for bell schedule grids."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from flask import current_app, make_response, render_template


def render_bell_schedule_pdf(
    *,
    title: str,
    subtitle: str,
    day_columns: list[dict[str, Any]],
    unmapped: list[dict[str, Any]] | None = None,
    filename: str = 'schedule.pdf',
):
    """Return a Flask PDF response for a bell schedule grid."""
    from weasyprint import HTML

    html_content = render_template(
        'shared/bell_schedule_pdf.html',
        title=title,
        subtitle=subtitle or '',
        day_columns=day_columns or [],
        unmapped=unmapped or [],
    )
    pdf_buffer = BytesIO()
    HTML(string=html_content, base_url=current_app.root_path).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
