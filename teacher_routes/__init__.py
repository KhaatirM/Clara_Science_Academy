"""
Teacher Routes Package

This package contains all teacher-related routes organized by functional area.
Each module focuses on a specific aspect of teacher functionality.
"""

from flask import Blueprint

# Create the main teacher blueprint
teacher_blueprint = Blueprint('teacher', __name__)

# Import all route modules to register their routes
# Note: settings now imports teacher_blueprint directly, so it doesn't need separate registration
from . import (
    dashboard,  # Keeps its own blueprint for compatibility
    settings,   # Uses teacher_blueprint directly
    assignments, 
    quizzes,
    attendance,
    grading,
    groups,
    communications,
    analytics,
    templates,
    feedback360
)

# Register sub-blueprints with the main teacher blueprint
# (settings is already using teacher_blueprint directly, so it's not registered here)
teacher_blueprint.register_blueprint(dashboard.bp, url_prefix='')
teacher_blueprint.register_blueprint(assignments.bp, url_prefix='')
teacher_blueprint.register_blueprint(quizzes.bp, url_prefix='')
teacher_blueprint.register_blueprint(attendance.bp, url_prefix='')
teacher_blueprint.register_blueprint(grading.bp, url_prefix='')
teacher_blueprint.register_blueprint(groups.bp, url_prefix='')
teacher_blueprint.register_blueprint(feedback360.bp, url_prefix='')  # Register before communications to avoid route conflicts
teacher_blueprint.register_blueprint(communications.bp, url_prefix='')
teacher_blueprint.register_blueprint(analytics.bp, url_prefix='')
teacher_blueprint.register_blueprint(templates.bp, url_prefix='')

