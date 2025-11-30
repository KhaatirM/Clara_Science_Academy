"""
Assignment management routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from decorators import management_required
from models import db, Assignment, Submission, Enrollment, Student, Grade, AssignmentExtension
from datetime import datetime
import os

bp = Blueprint('assignments', __name__)

@bp.route('/assignments')
@login_required
@management_required
def assignments_list():
    """Display all assignments."""
    assignments = Assignment.query.order_by(Assignment.due_date.desc()).all()
    return render_template('management_assignments.html', assignments=assignments)

@bp.route('/assignment/<int:assignment_id>/submissions')
@login_required
@management_required
def view_assignment_submissions(assignment_id):
    """View all submissions for an assignment (management access)"""
    # Import the teacher route function and reuse it
    from teacher_routes.assignments import view_assignment_submissions as teacher_view_submissions
    return teacher_view_submissions(assignment_id)

@bp.route('/assignment/<int:assignment_id>/submission/<int:submission_id>/download')
@login_required
@management_required
def download_submission(assignment_id, submission_id):
    """Download a student submission file (management access)"""
    # Import the teacher route function and reuse it
    from teacher_routes.assignments import download_submission as teacher_download_submission
    return teacher_download_submission(assignment_id, submission_id)



