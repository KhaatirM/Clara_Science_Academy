"""
Grading routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (
    db, Class, Assignment, Student, Grade, Submission, Enrollment
)
import json
from datetime import datetime

bp = Blueprint('grading', __name__)

@bp.route('/grade/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_assignment(assignment_id):
    """Grade an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to grade this assignment.", "danger")
        return redirect(url_for('teacher.my_assignments'))
    
    if request.method == 'POST':
        # Handle grading submission
        student_id = request.form.get('student_id', type=int)
        points_earned = request.form.get('points_earned', type=float)
        feedback = request.form.get('feedback', '')
        
        if not student_id or points_earned is None:
            flash("Missing required grading information.", "danger")
            return redirect(url_for('teacher.grading.grade_assignment', assignment_id=assignment_id))
        
        try:
            # Check if grade already exists
            existing_grade = Grade.query.filter_by(
                assignment_id=assignment_id,
                student_id=student_id
            ).first()
            
            grade_data = {
                'score': points_earned,
                'max_score': assignment.points,
                'percentage': (points_earned / assignment.points) * 100 if assignment.points > 0 else 0,
                'feedback': feedback,
                'graded_at': datetime.now().isoformat()
            }
            
            if existing_grade:
                # Update existing grade
                existing_grade.points_earned = points_earned
                existing_grade.grade_data = json.dumps(grade_data)
                existing_grade.graded_at = datetime.now()
                existing_grade.graded_by = current_user.id
            else:
                # Create new grade
                new_grade = Grade(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    points_earned=points_earned,
                    grade_data=json.dumps(grade_data),
                    graded_at=datetime.now(),
                    graded_by=current_user.id
                )
                db.session.add(new_grade)
            
            db.session.commit()
            flash('Grade saved successfully!', 'success')
            return redirect(url_for('teacher.grading.grade_assignment', assignment_id=assignment_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving grade: {str(e)}")
            flash(f'Error saving grade: {str(e)}', 'danger')
            return redirect(url_for('teacher.grading.grade_assignment', assignment_id=assignment_id))
    
    # GET request - show grading interface
    # Get enrolled students for this class
    enrollments = Enrollment.query.filter_by(
        class_id=assignment.class_id,
        is_active=True
    ).all()
    
    students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    # Get existing grades for this assignment
    grades = Grade.query.filter_by(assignment_id=assignment_id).all()
    grades_dict = {grade.student_id: grade for grade in grades}
    
    # Get submissions for this assignment
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    submissions_dict = {submission.student_id: submission for submission in submissions}
    
    return render_template('teachers/teacher_grade_assignment.html', 
                         assignment=assignment,
                         class_obj=assignment.class_info,
                         students=students,
                         grades=grades_dict,
                         submissions=submissions_dict)

@bp.route('/grades')
@login_required
@teacher_required
def my_grades():
    """Display all grades for the current teacher's assignments."""
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Directors and School Administrators see all grades, teachers only see grades for their classes
    if is_admin():
        grades = Grade.query.order_by(Grade.graded_at.desc()).all()
    else:
        # Check if teacher object exists
        if teacher is None:
            # If user is a Teacher but has no teacher_staff_id, show empty grades list
            grades = []
        else:
            # Get classes for this teacher
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
            class_ids = [c.id for c in classes]
            
            # Get assignments for these classes
            assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
            assignment_ids = [a.id for a in assignments]
            
            # Get grades for these assignments
            grades = Grade.query.filter(Grade.assignment_id.in_(assignment_ids)).order_by(Grade.graded_at.desc()).all()
    
    return render_template('teachers/teacher_grades.html', grades=grades, teacher=teacher)

@bp.route('/student-grades')
@login_required
@teacher_required
def student_grades():
    """Display student grades view for the current teacher's classes."""
    flash("Student grades page is being updated. Please check back later.", "info")
    return redirect(url_for('teacher.grading.grades'))

