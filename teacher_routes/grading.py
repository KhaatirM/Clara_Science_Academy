"""
Grading routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import (
    db, Class, Assignment, Student, Grade, Submission, Enrollment, AssignmentExtension,
    QuizQuestion, QuizAnswer, QuizOption
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
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    if request.method == 'POST':
        # Handle quiz per-question grading or regular assignment grading
        try:
            grades_saved = 0
            
            # Get enrolled students for this class
            enrollments = Enrollment.query.filter_by(class_id=assignment.class_id, is_active=True).all()
            student_ids = [e.student_id for e in enrollments if e.student_id]
            
            # Check if this is quiz grading with per-question scores
            if assignment.assignment_type == 'quiz' and request.form.get('grading_mode') == 'per_question':
                # Quiz per-question grading
                quiz_questions = QuizQuestion.query.filter_by(assignment_id=assignment_id).order_by(QuizQuestion.order).all()
                total_points = assignment.total_points if assignment.total_points else 100.0
                
                for student_id in student_ids:
                    # Check if grade is voided
                    existing_grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=student_id
                    ).first()
                    
                    if existing_grade and existing_grade.is_voided:
                        continue
                    
                    # Calculate points from per-question grades
                    earned_points = 0.0
                    for question in quiz_questions:
                        # Get points for this question (for text answers, it's from the form; for auto-graded, it's already in QuizAnswer)
                        if question.question_type in ['short_answer', 'essay']:
                            # Get manually graded points
                            points_key = f'points_{student_id}_q{question.id}'
                            question_points = request.form.get(points_key, '0')
                            try:
                                earned_points += float(question_points)
                                # Update QuizAnswer points_earned
                                answer = QuizAnswer.query.filter_by(
                                    student_id=student_id,
                                    question_id=question.id
                                ).first()
                                if answer:
                                    answer.points_earned = float(question_points)
                                    answer.is_correct = (float(question_points) == question.points)
                            except ValueError:
                                pass
                        else:
                            # For auto-graded questions, get points from existing answer
                            answer = QuizAnswer.query.filter_by(
                                student_id=student_id,
                                question_id=question.id
                            ).first()
                            if answer:
                                earned_points += answer.points_earned
                    
                    # Get feedback comment
                    comments = request.form.get(f'comment_{student_id}', '').strip()
                    
                    # Create or update grade
                    grade_data = {
                        'score': earned_points,
                        'points_earned': earned_points,
                        'total_points': total_points,
                        'max_score': total_points,
                        'percentage': round((earned_points / total_points * 100) if total_points > 0 else 0, 2),
                        'feedback': comments,
                        'graded_at': datetime.now().isoformat()
                    }
                    
                    if existing_grade:
                        existing_grade.grade_data = json.dumps(grade_data)
                        existing_grade.graded_at = datetime.now()
                    else:
                        new_grade = Grade(
                            assignment_id=assignment_id,
                            student_id=student_id,
                            grade_data=json.dumps(grade_data),
                            graded_at=datetime.now()
                        )
                        db.session.add(new_grade)
                    
                    grades_saved += 1
            else:
                # Regular assignment grading (existing logic)
                for student_id in student_ids:
                    score = request.form.get(f'score_{student_id}')
                    comments = request.form.get(f'comment_{student_id}', '').strip()
                    
                    # Skip if no score provided
                    if not score or score == '':
                        continue
                    
                    try:
                        points_earned = float(score)
                    except ValueError:
                        continue
                    
                    # Check if grade already exists
                    existing_grade = Grade.query.filter_by(
                        assignment_id=assignment_id,
                        student_id=student_id
                    ).first()
                    
                    # Check if this student's grade is voided (check the database field, not JSON)
                    if existing_grade and existing_grade.is_voided:
                        # Don't update voided grades - preserve the void status
                        continue
                    
                    # Get total points from assignment (default to 100 if not set)
                    total_points = assignment.total_points if assignment.total_points else 100.0
                    
                    # Calculate percentage based on points earned vs total points
                    percentage = (points_earned / total_points * 100) if total_points > 0 else 0
                    
                    grade_data = {
                        'score': points_earned,
                        'points_earned': points_earned,
                        'total_points': total_points,
                        'max_score': total_points,  # Keep for backward compatibility
                        'percentage': round(percentage, 2),
                        'feedback': comments,
                        'graded_at': datetime.now().isoformat()
                    }
                    
                    if existing_grade:
                        # Update existing grade
                        existing_grade.grade_data = json.dumps(grade_data)
                        existing_grade.graded_at = datetime.now()
                    else:
                        # Create new grade
                        new_grade = Grade(
                            assignment_id=assignment_id,
                            student_id=student_id,
                            grade_data=json.dumps(grade_data),
                            graded_at=datetime.now()
                        )
                        db.session.add(new_grade)
                    
                    grades_saved += 1
            
            db.session.commit()
            
            if grades_saved > 0:
                flash(f'{grades_saved} grade(s) saved successfully!', 'success')
            else:
                flash('No grades were updated. Please enter scores to save.', 'warning')
            
            return redirect(url_for('teacher.grading.grade_assignment', assignment_id=assignment_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving grades: {str(e)}")
            flash(f'Error saving grades: {str(e)}', 'danger')
            return redirect(url_for('teacher.grading.grade_assignment', assignment_id=assignment_id))
    
    # GET request - show grading interface
    # Get enrolled students for this class
    enrollments = Enrollment.query.filter_by(
        class_id=assignment.class_id,
        is_active=True
    ).all()
    
    students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    # Get total points from assignment (default to 100 if not set)
    assignment_total_points = assignment.total_points if assignment.total_points else 100.0
    
    # Get existing grades for this assignment and parse the JSON grade_data
    grades = Grade.query.filter_by(assignment_id=assignment_id).all()
    grades_dict = {}
    for grade in grades:
        try:
            # Parse the JSON grade_data
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            # Get points earned and total points from grade_data, fallback to assignment total_points
            points_earned = grade_data.get('points_earned') or grade_data.get('score', 0)
            total_points = grade_data.get('total_points') or grade_data.get('max_score', assignment_total_points)
            percentage = grade_data.get('percentage', 0)
            
            # Recalculate percentage if not present or if using old format
            if not percentage or percentage == points_earned:
                percentage = (points_earned / total_points * 100) if total_points > 0 else 0
            
            # Create a dict with the parsed data plus the grade object attributes
            grades_dict[grade.student_id] = {
                'score': points_earned,
                'points_earned': points_earned,
                'total_points': total_points,
                'comment': grade_data.get('comment', '') or grade_data.get('feedback', ''),
                'percentage': round(percentage, 2),
                'max_score': total_points,  # Keep for backward compatibility
                'is_voided': grade.is_voided or grade_data.get('is_voided', False),
                'graded_at': grade.graded_at,
                'grade_id': grade.id  # Add grade_id for history link
            }
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            # If parsing fails, create a default structure
            print(f"Error parsing grade_data for grade {grade.id}: {e}")
            grades_dict[grade.student_id] = {
                'score': 0,
                'points_earned': 0,
                'total_points': assignment_total_points,
                'comment': '',
                'percentage': 0,
                'max_score': assignment_total_points,
                'is_voided': grade.is_voided,
                'graded_at': grade.graded_at
            }
    
    # Get submissions for this assignment
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    submissions_dict = {submission.student_id: submission for submission in submissions}
    
    # Get active extensions for this assignment
    extensions = AssignmentExtension.query.filter_by(
        assignment_id=assignment_id,
        is_active=True
    ).all()
    extensions_dict = {ext.student_id: ext for ext in extensions}
    
    # For quiz assignments, load questions and student answers
    quiz_questions = None
    quiz_answers_by_student = {}
    if assignment.assignment_type == 'quiz':
        # Load questions with options eagerly
        from sqlalchemy.orm import joinedload
        quiz_questions = QuizQuestion.query.options(joinedload(QuizQuestion.options)).filter_by(assignment_id=assignment_id).order_by(QuizQuestion.order).all()
        
        # Load answers for all students with selected_option relationship
        for student in students:
            answers = QuizAnswer.query.options(
                joinedload(QuizAnswer.question),
                joinedload(QuizAnswer.selected_option)
            ).filter_by(
                student_id=student.id
            ).join(QuizQuestion).filter(
                QuizQuestion.assignment_id == assignment_id
            ).all()
            quiz_answers_by_student[student.id] = {answer.question_id: answer for answer in answers}
    
    # Use specialized quiz grading template if it's a quiz, otherwise use regular template
    template_name = 'teachers/teacher_grade_quiz.html' if assignment.assignment_type == 'quiz' else 'teachers/teacher_grade_assignment.html'
    
    return render_template(template_name, 
                         assignment=assignment,
                         class_obj=assignment.class_info,
                         students=students,
                         grades=grades_dict,
                         submissions=submissions_dict,
                         extensions=extensions_dict,
                         total_points=assignment_total_points,
                         quiz_questions=quiz_questions,
                         quiz_answers_by_student=quiz_answers_by_student)

@bp.route('/grades/statistics/<int:assignment_id>')
@login_required
@teacher_required
def grade_statistics(assignment_id):
    """Display grade statistics dashboard for an assignment with charts."""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to view statistics for this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    # Get all grades for this assignment
    grades = Grade.query.filter_by(assignment_id=assignment_id, is_voided=False).all()
    
    # Calculate statistics
    stats = {
        'total_students': len(grades),
        'graded_count': 0,
        'ungraded_count': 0,
        'average_score': 0,
        'median_score': 0,
        'highest_score': 0,
        'lowest_score': 100,
        'passing_count': 0,
        'failing_count': 0
    }
    
    scores = []
    letter_grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    grade_distribution = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '0-59': 0}
    
    total_points = assignment.total_points if assignment.total_points else 100.0
    
    for grade in grades:
        try:
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            score = grade_data.get('score') or grade_data.get('points_earned')
            
            if score is not None:
                stats['graded_count'] += 1
                score_float = float(score)
                scores.append(score_float)
                
                # Calculate percentage
                percentage = (score_float / total_points * 100) if total_points > 0 else 0
                
                # Update min/max
                if score_float > stats['highest_score']:
                    stats['highest_score'] = score_float
                if score_float < stats['lowest_score']:
                    stats['lowest_score'] = score_float
                
                # Passing/failing (70% threshold)
                if percentage >= 70:
                    stats['passing_count'] += 1
                else:
                    stats['failing_count'] += 1
                
                # Letter grade distribution
                if percentage >= 90:
                    letter_grades['A'] += 1
                    grade_distribution['90-100'] += 1
                elif percentage >= 80:
                    letter_grades['B'] += 1
                    grade_distribution['80-89'] += 1
                elif percentage >= 70:
                    letter_grades['C'] += 1
                    grade_distribution['70-79'] += 1
                elif percentage >= 60:
                    letter_grades['D'] += 1
                    grade_distribution['60-69'] += 1
                else:
                    letter_grades['F'] += 1
                    grade_distribution['0-59'] += 1
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            continue
    
    # Calculate averages
    if scores:
        stats['average_score'] = round(sum(scores) / len(scores), 2)
        sorted_scores = sorted(scores)
        mid = len(sorted_scores) // 2
        stats['median_score'] = round((sorted_scores[mid] + sorted_scores[~mid]) / 2, 2) if len(sorted_scores) > 1 else round(sorted_scores[0], 2)
        stats['average_percentage'] = round((stats['average_score'] / total_points * 100) if total_points > 0 else 0, 2)
    else:
        stats['average_percentage'] = 0
    
    stats['ungraded_count'] = stats['total_students'] - stats['graded_count']
    
    return render_template('teachers/teacher_grade_statistics.html',
                         assignment=assignment,
                         stats=stats,
                         letter_grades=letter_grades,
                         grade_distribution=grade_distribution,
                         total_points=total_points)

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

@bp.route('/grades/history/<int:grade_id>')
@login_required
@teacher_required
def grade_history(grade_id):
    """View grade history/audit trail for a specific grade."""
    from models import GradeHistory, User
    
    grade = Grade.query.get_or_404(grade_id)
    assignment = grade.assignment
    
    # Check authorization
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to view this grade history.", "danger")
        return redirect(url_for('teacher.dashboard.my_assignments'))
    
    # Get all history entries for this grade
    history_entries = GradeHistory.query.filter_by(grade_id=grade_id).order_by(GradeHistory.changed_at.desc()).all()
    
    # Format history entries with user information
    formatted_history = []
    for entry in history_entries:
        try:
            changed_by_user = User.query.get(entry.changed_by)
            previous_data = json.loads(entry.previous_grade_data) if entry.previous_grade_data else None
            new_data = json.loads(entry.new_grade_data) if entry.new_grade_data else None
            
            formatted_history.append({
                'entry': entry,
                'changed_by': changed_by_user.username if changed_by_user else 'Unknown',
                'changed_at': entry.changed_at,
                'previous_data': previous_data,
                'new_data': new_data,
                'reason': entry.change_reason
            })
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Parse current grade data
    try:
        current_grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
    except (json.JSONDecodeError, TypeError):
        current_grade_data = {}
    
    return render_template('teachers/teacher_grade_history.html',
                         grade=grade,
                         assignment=assignment,
                         current_grade_data=current_grade_data,
                         history=formatted_history)

@bp.route('/student-grades')
@login_required
@teacher_required
def student_grades():
    """Display student grades view for the current teacher's classes."""
    flash("Student grades page is being updated. Please check back later.", "info")
    return redirect(url_for('teacher.grading.grades'))

