"""
School administration routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import management_required
from models import db, SchoolYear, AcademicPeriod

bp = Blueprint('administration', __name__)

@bp.route('/school-years')
@login_required
@management_required
def school_years():
    """School years management."""
    school_years = SchoolYear.query.all()
    return render_template('management_school_years.html', school_years=school_years)

@bp.route('/settings')
@login_required
@management_required
def settings():
    """Management settings."""
    return render_template('management_settings.html')

# Placeholder for administration routes
# This module will contain all administration functionality
# from the original managementroutes.py file



