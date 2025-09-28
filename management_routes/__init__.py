"""
Management Routes Package

This package contains all management-related routes organized by functional area.
Each module focuses on a specific aspect of management functionality.
"""

from flask import Blueprint

# Create the main management blueprint
management_blueprint = Blueprint('management', __name__)

# Import all route modules to register their routes
from . import (
    dashboard,
    students,
    teachers,
    classes,
    assignments,
    attendance,
    calendar,
    communications,
    reports,
    administration
)

# Register all blueprints with the main management blueprint
management_blueprint.register_blueprint(dashboard.bp, url_prefix='')
management_blueprint.register_blueprint(students.bp, url_prefix='')
management_blueprint.register_blueprint(teachers.bp, url_prefix='')
management_blueprint.register_blueprint(classes.bp, url_prefix='')
management_blueprint.register_blueprint(assignments.bp, url_prefix='')
management_blueprint.register_blueprint(attendance.bp, url_prefix='')
management_blueprint.register_blueprint(calendar.bp, url_prefix='')
management_blueprint.register_blueprint(communications.bp, url_prefix='')
management_blueprint.register_blueprint(reports.bp, url_prefix='')
management_blueprint.register_blueprint(administration.bp, url_prefix='')



