"""Attendance CSV template helper shared by teacher + management SPA APIs."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

from flask import Response
from models import Class, Enrollment


def build_attendance_csv_template_response(class_id: int) -> Response:
    class_obj = Class.query.get_or_404(class_id)
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [e.student for e in enrollments if e.student is not None]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Date (MM/DD/YYYY)",
            "Student ID",
            "Student Name",
            "Status",
            "Notes (Optional)",
        ]
    )
    example_date = date.today().strftime("%m/%d/%Y")
    for student in students[:3]:
        writer.writerow(
            [
                example_date,
                student.student_id or "N/A",
                f"{student.first_name} {student.last_name}",
                "Present",
                "Example note - optional",
            ]
        )
    output.seek(0)
    safe_name = (class_obj.name or "class").replace(" ", "_")
    filename = f"attendance_template_{safe_name}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
