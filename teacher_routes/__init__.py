"""
Teacher Routes Package

This package contains all teacher-related routes organized by functional area.
Each module focuses on a specific aspect of teacher functionality.
"""

from flask import Blueprint

# Create the main teacher blueprint
teacher_blueprint = Blueprint('teacher', __name__)

# Import all route modules to register their routes
from . import (
    dashboard,
    assignments, 
    quizzes,
    attendance,
    grading,
    groups,
    communications,
    analytics,
    templates,
    settings
)

# Register all blueprints with the main teacher blueprint
teacher_blueprint.register_blueprint(dashboard.bp, url_prefix='')
teacher_blueprint.register_blueprint(assignments.bp, url_prefix='')
teacher_blueprint.register_blueprint(quizzes.bp, url_prefix='')
teacher_blueprint.register_blueprint(attendance.bp, url_prefix='')
teacher_blueprint.register_blueprint(grading.bp, url_prefix='')
teacher_blueprint.register_blueprint(groups.bp, url_prefix='')
teacher_blueprint.register_blueprint(communications.bp, url_prefix='')
teacher_blueprint.register_blueprint(analytics.bp, url_prefix='')
teacher_blueprint.register_blueprint(templates.bp, url_prefix='')
teacher_blueprint.register_blueprint(settings.bp, url_prefix='')

