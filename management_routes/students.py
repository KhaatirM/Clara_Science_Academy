"""
Student management routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import management_required
from models import db, Student, Class, Enrollment

bp = Blueprint('students', __name__)

@bp.route('/students')
@login_required
@management_required
def students_list():
    """Display all students."""
    students = Student.query.all()
    return render_template('user_management.html', students=students)

# Placeholder for student management routes
# This module will contain all student management functionality
# from the original managementroutes.py file



