"""
Reflection Journals routes for teachers - standalone module removed from communications.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin
from models import (db, Class, Student, Enrollment, ReflectionJournal, GroupAssignment, 
                    StudentGroup)
from datetime import datetime
import json

bp = Blueprint('reflection_journals', __name__)

# Redirect old URL pattern to new one for backwards compatibility
@bp.route('/journals/class/<int:class_id>')
@login_required
@teacher_required
def redirect_old_journals(class_id):
    """Redirect old URL pattern to new one."""
    return redirect(url_for('teacher.reflection_journals.class_reflection_journals', class_id=class_id))

@bp.route('/class/<int:class_id>/reflection-journals')
@login_required
@teacher_required
def class_reflection_journals(class_id):
    """View reflection journals for a specific class."""
    teacher = get_teacher_or_admin()
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this class.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_id))
    
    # Get all reflection journals for this class
    journals = ReflectionJournal.query.join(GroupAssignment).filter(
        GroupAssignment.class_id == class_id
    ).order_by(ReflectionJournal.submitted_at.desc()).all()
    
    # Get students in the class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student]
    
    # Calculate statistics
    total_journals = len(journals)
    unique_students = list(set([j.student_id for j in journals]))
    unique_students_count = len(unique_students)
    
    # Calculate average ratings
    avg_collaboration = 0
    avg_learning = 0
    if journals:
        avg_collaboration = sum(j.collaboration_rating for j in journals) / len(journals)
        avg_learning = sum(j.learning_rating for j in journals) / len(journals)
    
    return render_template('teachers/teacher_class_reflection_journals.html',
                         class_obj=class_obj,
                         reflection_journals=journals,
                         journals=journals,  # For backwards compatibility
                         students=students,
                         total_journals=total_journals,
                         unique_students=unique_students,
                         unique_students_count=unique_students_count,
                         avg_collaboration=round(avg_collaboration, 1),
                         avg_learning=round(avg_learning, 1))

@bp.route('/reflection-journal/<int:journal_id>')
@login_required
@teacher_required
def view_reflection_journal(journal_id):
    """View a specific reflection journal."""
    teacher = get_teacher_or_admin()
    journal = ReflectionJournal.query.get_or_404(journal_id)
    class_obj = Class.query.get_or_404(journal.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this reflection journal.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    return render_template('teachers/teacher_view_reflection_journal.html',
                         journal=journal,
                         class_obj=class_obj)

@bp.route('/reflection-journal/<int:journal_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_reflection_journal(journal_id):
    """Delete a reflection journal."""
    teacher = get_teacher_or_admin()
    journal = ReflectionJournal.query.get_or_404(journal_id)
    class_obj = Class.query.get_or_404(journal.group_assignment.class_id)
    
    if not is_admin() and class_obj.teacher_id != teacher.id:
        flash('You do not have access to this reflection journal.', 'danger')
        return redirect(url_for('teacher.dashboard.view_class', class_id=class_obj.id))
    
    try:
        db.session.delete(journal)
        db.session.commit()
        flash('Reflection journal deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting reflection journal: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.reflection_journals.class_reflection_journals', class_id=class_obj.id))

