"""
Teacher Routes Package

This package contains all teacher-related routes organized by functional area.
Each module focuses on a specific aspect of teacher functionality.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from decorators import teacher_required

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
    feedback360,
    reflection_journals,
    conflict_resolution
)
from .utils import get_teacher_or_admin, is_authorized_for_class
from models import Class

# Register sub-blueprints with the main teacher blueprint
# (settings is already using teacher_blueprint directly, so it's not registered here)
teacher_blueprint.register_blueprint(dashboard.bp, url_prefix='')
teacher_blueprint.register_blueprint(assignments.bp, url_prefix='')
teacher_blueprint.register_blueprint(quizzes.bp, url_prefix='')
teacher_blueprint.register_blueprint(attendance.bp, url_prefix='')
teacher_blueprint.register_blueprint(grading.bp, url_prefix='')
teacher_blueprint.register_blueprint(groups.bp, url_prefix='')
teacher_blueprint.register_blueprint(feedback360.bp, url_prefix='')  # Register before communications to avoid route conflicts
teacher_blueprint.register_blueprint(reflection_journals.bp, url_prefix='')  # Register before communications to avoid route conflicts
teacher_blueprint.register_blueprint(conflict_resolution.bp, url_prefix='')  # Register before communications to avoid route conflicts
teacher_blueprint.register_blueprint(communications.bp, url_prefix='')
teacher_blueprint.register_blueprint(analytics.bp, url_prefix='')
teacher_blueprint.register_blueprint(templates.bp, url_prefix='')

# Add route directly to main blueprint for backward compatibility with templates
@teacher_blueprint.route('/group-assignment/type-selector/<int:class_id>')
@login_required
@teacher_required
def group_assignment_type_selector(class_id):
    """Group assignment type selector page."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.dashboard.my_classes'))
    
    return render_template('shared/group_assignment_type_selector.html', 
                         class_obj=class_obj)

# Add route alias for assignment_type_selector for backward compatibility
@teacher_blueprint.route('/assignment/type-selector', endpoint='assignment_type_selector')
@login_required
@teacher_required
def assignment_type_selector():
    """Assignment type selector route - delegates to assignments module"""
    from .assignments import assignment_type_selector as assignment_type_selector_func
    return assignment_type_selector_func()

# Add route alias for create_quiz_assignment for backward compatibility
@teacher_blueprint.route('/assignment/create/quiz', methods=['GET', 'POST'], endpoint='create_quiz_assignment')
@login_required
@teacher_required
def create_quiz_assignment():
    """Create quiz assignment route - delegates to quizzes module"""
    from .quizzes import create_quiz_assignment as create_quiz_func
    return create_quiz_func()

# Add route alias for create_discussion_assignment for backward compatibility
@teacher_blueprint.route('/assignment/create/discussion', methods=['GET', 'POST'], endpoint='create_discussion_assignment')
@login_required
@teacher_required
def create_discussion_assignment():
    """Create discussion assignment route - delegates to quizzes module"""
    from .quizzes import create_discussion_assignment as create_discussion_func
    return create_discussion_func()

# Add route aliases for extension requests
@teacher_blueprint.route('/extension-requests', endpoint='view_extension_requests')
@login_required
@teacher_required
def view_extension_requests():
    """View extension requests route - delegates to assignments module"""
    from .assignments import view_extension_requests as view_extension_requests_func
    return view_extension_requests_func()

@teacher_blueprint.route('/extension-request/<int:request_id>/review', methods=['POST'], endpoint='review_extension_request')
@login_required
@teacher_required
def review_extension_request(request_id):
    """Review extension request route - delegates to assignments module"""
    from .assignments import review_extension_request as review_extension_request_func
    return review_extension_request_func(request_id)

@teacher_blueprint.route('/redo-dashboard', endpoint='redo_dashboard')
@login_required
@teacher_required
def teacher_redo_dashboard():
    """Redo dashboard route for teachers - delegates to management dashboard function"""
    from management_routes.dashboard import redo_dashboard as redo_dashboard_func
    return redo_dashboard_func()
