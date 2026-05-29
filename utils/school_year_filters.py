"""Shared school-year filter state for management list views."""

from flask import request

from models import SchoolYear


def get_school_year_filter_context():
    """
    School year dropdown state for filter UIs.

    - Defaults selection to the active year when one exists.
    - When the year is closed (no active year), selection stays empty until the user picks one.
    """
    active = SchoolYear.query.filter_by(is_active=True).first()
    selected = request.args.get('school_year_id', type=int)
    if selected is None and active:
        selected = active.id
    years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    return {
        'school_years': years,
        'selected_school_year_id': selected,
        'active_school_year': active,
    }
