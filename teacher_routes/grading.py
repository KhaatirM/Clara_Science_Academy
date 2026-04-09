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
from utils.grade_helpers import get_points_earned

bp = Blueprint('grading', __name__)


def _apply_assignment_adjustments(assignment, entered_points, submission_record=None, notes_type='On-Time'):
    """
    Apply assignment-level grading rules (extra credit + late penalty) to a raw score.
    Returns dict with final points and metadata for grade_data.
    """
    total_points = float(assignment.total_points or 100.0)
    raw_points = max(0.0, float(entered_points))

    extra_credit_points = 0.0
    if getattr(assignment, 'allow_extra_credit', False):
        overage = max(0.0, raw_points - total_points)
        max_extra = max(0.0, float(getattr(assignment, 'max_extra_credit_points', 0.0) or 0.0))
        extra_credit_points = min(overage, max_extra)
        points_before_penalty = min(raw_points, total_points) + extra_credit_points
    else:
        points_before_penalty = min(raw_points, total_points)

    late_penalty_applied = 0.0
    days_late = 0
    if getattr(assignment, 'late_penalty_enabled', False):
        per_day_pct = max(0.0, float(getattr(assignment, 'late_penalty_per_day', 0.0) or 0.0))
        if per_day_pct > 0:
            due_date = getattr(assignment, 'due_date', None)
            submitted_at = getattr(submission_record, 'submitted_at', None) if submission_record else None
            if due_date and submitted_at and submitted_at > due_date:
                delta_days = (submitted_at - due_date).days
                days_late = delta_days if delta_days > 0 else 1
            elif str(notes_type or '').strip().lower() == 'late':
                days_late = 1
            if days_late > 0:
                max_days = int(getattr(assignment, 'late_penalty_max_days', 0) or 0)
                if max_days > 0:
                    days_late = min(days_late, max_days)
                late_penalty_applied = (days_late * per_day_pct / 100.0) * total_points
                late_penalty_applied = min(late_penalty_applied, points_before_penalty)

    final_points = max(0.0, points_before_penalty - late_penalty_applied)
    percentage = (final_points / total_points * 100.0) if total_points > 0 else 0.0
    max_score = total_points + (float(getattr(assignment, 'max_extra_credit_points', 0.0) or 0.0) if getattr(assignment, 'allow_extra_credit', False) else 0.0)

    return {
        'raw_points': round(raw_points, 2),
        'points_earned': round(final_points, 2),
        'extra_credit_points': round(extra_credit_points, 2),
        'late_penalty_applied': round(late_penalty_applied, 2),
        'days_late': int(days_late),
        'percentage': round(percentage, 2),
        'total_points': round(total_points, 2),
        'max_score': round(max_score, 2),
    }

@bp.route('/grade/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_assignment(assignment_id):
    """Grade an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization for this assignment's class
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to grade this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
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
                    sub = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
                    adjusted = _apply_assignment_adjustments(
                        assignment=assignment,
                        entered_points=earned_points,
                        submission_record=sub,
                        notes_type='On-Time'
                    )
                    
                    # Create or update grade
                    grade_data = {
                        'score': adjusted['points_earned'],
                        'points_earned': adjusted['points_earned'],
                        'raw_points': adjusted['raw_points'],
                        'extra_credit_points': adjusted['extra_credit_points'],
                        'late_penalty_applied': adjusted['late_penalty_applied'],
                        'days_late': adjusted['days_late'],
                        'total_points': adjusted['total_points'],
                        'max_score': adjusted['max_score'],
                        'percentage': adjusted['percentage'],
                        'feedback': comments,
                        'graded_at': datetime.now().isoformat()
                    }
                    
                    if existing_grade:
                        existing_grade.grade_data = json.dumps(grade_data)
                        existing_grade.graded_at = datetime.now()
                        existing_grade.extra_credit_points = adjusted['extra_credit_points']
                        existing_grade.late_penalty_applied = adjusted['late_penalty_applied']
                    else:
                        new_grade = Grade(
                            assignment_id=assignment_id,
                            student_id=student_id,
                            grade_data=json.dumps(grade_data),
                            graded_at=datetime.now(),
                            extra_credit_points=adjusted['extra_credit_points'],
                            late_penalty_applied=adjusted['late_penalty_applied']
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
                    
                    sub = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
                    adjusted = _apply_assignment_adjustments(
                        assignment=assignment,
                        entered_points=points_earned,
                        submission_record=sub,
                        notes_type='On-Time'
                    )
                    grade_data = {
                        'score': adjusted['points_earned'],
                        'points_earned': adjusted['points_earned'],
                        'raw_points': adjusted['raw_points'],
                        'extra_credit_points': adjusted['extra_credit_points'],
                        'late_penalty_applied': adjusted['late_penalty_applied'],
                        'days_late': adjusted['days_late'],
                        'total_points': adjusted['total_points'],
                        'max_score': adjusted['max_score'],  # Keep for backward compatibility
                        'percentage': adjusted['percentage'],
                        'feedback': comments,
                        'graded_at': datetime.now().isoformat()
                    }
                    
                    if existing_grade:
                        # Update existing grade
                        existing_grade.grade_data = json.dumps(grade_data)
                        existing_grade.graded_at = datetime.now()
                        existing_grade.extra_credit_points = adjusted['extra_credit_points']
                        existing_grade.late_penalty_applied = adjusted['late_penalty_applied']
                    else:
                        # Create new grade
                        new_grade = Grade(
                            assignment_id=assignment_id,
                            student_id=student_id,
                            grade_data=json.dumps(grade_data),
                            graded_at=datetime.now(),
                            extra_credit_points=adjusted['extra_credit_points'],
                            late_penalty_applied=adjusted['late_penalty_applied']
                        )
                        db.session.add(new_grade)
                    
                    # If grade entered and no submission exists, auto-create in_person submission
                    sub = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
                    if not sub:
                        teacher_staff = get_teacher_or_admin()
                        sub = Submission(
                            student_id=student_id,
                            assignment_id=assignment_id,
                            submission_type='in_person',
                            submission_notes='Auto-marked: grade entered',
                            marked_by=teacher_staff.id if teacher_staff else None,
                            marked_at=datetime.now(),
                            submitted_at=datetime.now(),
                            file_path=None,
                        )
                        db.session.add(sub)
                    
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
            # Get points earned from grade_data (use helper to handle 0 correctly)
            points_earned = get_points_earned(grade_data)
            if points_earned is None:
                points_earned = 0
            # Always use assignment's total_points as source of truth, not stored value
            total_points = assignment_total_points
            # Always recalculate percentage using assignment's actual total_points
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
    has_open_ended_questions = False
    
    if assignment.assignment_type == 'quiz':
        # Load questions with options eagerly
        from sqlalchemy.orm import joinedload
        quiz_questions = QuizQuestion.query.options(
            joinedload(QuizQuestion.options),
            joinedload(QuizQuestion.section)
        ).filter_by(assignment_id=assignment_id).order_by(QuizQuestion.order).all()
        
        # Check if quiz has open-ended questions (short_answer or essay) that need manual grading
        has_open_ended_questions = any(q.question_type in ['short_answer', 'essay'] for q in quiz_questions)
        
        # If quiz has no open-ended questions, all questions are auto-graded
        # Show a message and redirect back to assignment view
        if not has_open_ended_questions:
            flash('This quiz contains only auto-graded questions (Multiple Choice/True-False). All grades are automatically calculated when students submit their quizzes. No manual grading is required.', 'info')
            return redirect(url_for('teacher.assignments.view_assignment', assignment_id=assignment_id))
        
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
    
    # For discussion assignments, get threads and posts
    discussion_threads_by_student = {}
    discussion_posts_by_student = {}
    min_initial_posts = 1
    min_replies = 2
    
    if assignment.assignment_type == 'discussion':
        from models import DiscussionThread, DiscussionPost
        import re
        
        # Extract participation requirements from assignment description
        if assignment.description:
            initial_posts_match = re.search(r'Minimum (\d+) initial post', assignment.description)
            if initial_posts_match:
                min_initial_posts = int(initial_posts_match.group(1))
            replies_match = re.search(r'Minimum (\d+) reply/replies', assignment.description)
            if replies_match:
                min_replies = int(replies_match.group(1))
        
        # Get all threads and posts for this assignment
        all_threads = DiscussionThread.query.filter_by(assignment_id=assignment_id).all()
        all_posts = DiscussionPost.query.filter(
            DiscussionPost.thread_id.in_([t.id for t in all_threads])
        ).all()
        
        # Organize by student
        for student in students:
            # Count threads created by this student
            student_threads = [t for t in all_threads if t.student_id == student.id]
            discussion_threads_by_student[student.id] = student_threads
            
            # Count replies by this student
            student_posts = [p for p in all_posts if p.student_id == student.id]
            discussion_posts_by_student[student.id] = student_posts
    
    # Use specialized template based on assignment type
    if assignment.assignment_type == 'discussion':
        template_name = 'management/grade_discussion_assignment.html'
    elif assignment.assignment_type == 'quiz' and has_open_ended_questions:
        template_name = 'teachers/teacher_grade_quiz.html'
    else:
        template_name = 'teachers/teacher_grade_assignment.html'
    
    return render_template(template_name, 
                         assignment=assignment,
                         class_obj=assignment.class_info,
                         students=students,
                         grades=grades_dict,
                         submissions=submissions_dict,
                         extensions=extensions_dict,
                         role_prefix='teacher',
                         total_points=assignment_total_points,
                         quiz_questions=quiz_questions,
                         quiz_answers_by_student=quiz_answers_by_student,
                         discussion_threads_by_student=discussion_threads_by_student,
                         discussion_posts_by_student=discussion_posts_by_student,
                         min_initial_posts=min_initial_posts,
                         min_replies=min_replies)


@bp.route('/grade/assignment/<int:assignment_id>/student/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def save_student_grade(assignment_id, student_id):
    """Save a single student's grade via AJAX (for Speed Grader)."""
    assignment = Assignment.query.get_or_404(assignment_id)
    student = Student.query.get_or_404(student_id)

    if not is_authorized_for_class(assignment.class_info):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    # Verify student is in this class
    enrollment = Enrollment.query.filter_by(
        class_id=assignment.class_id, student_id=student_id, is_active=True
    ).first()
    if not enrollment:
        return jsonify({'success': False, 'error': 'Student not in class'}), 400

    try:
        score_val = request.form.get('score', request.json.get('score') if request.is_json else None)
        score_raw = str(score_val).strip() if score_val is not None else ''
        comment = request.form.get('comment', request.json.get('comment', '')) or ''
        submission_type = request.form.get('submission_type', request.json.get('submission_type', '')) or ''
        notes_type = request.form.get('submission_notes_type', request.json.get('submission_notes_type', 'On-Time')) or 'On-Time'
        notes_other = request.form.get('submission_notes', request.json.get('submission_notes', '')) or ''
        submission_notes = notes_other if notes_type == 'Other' else notes_type

        total_points = assignment.total_points if assignment.total_points else 100.0

        # Handle submission status
        teacher_staff = get_teacher_or_admin()
        if submission_type:
            sub = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
            if submission_type in ['in_person', 'online']:
                if sub:
                    sub.submission_type = submission_type
                    sub.submission_notes = submission_notes
                    sub.marked_by = teacher_staff.id if teacher_staff else None
                    sub.marked_at = datetime.utcnow()
                else:
                    sub = Submission(
                        student_id=student_id, assignment_id=assignment_id,
                        submission_type=submission_type, submission_notes=submission_notes,
                        marked_by=teacher_staff.id if teacher_staff else None,
                        marked_at=datetime.utcnow(), submitted_at=datetime.utcnow(),
                        file_path=None
                    )
                    db.session.add(sub)
            elif submission_type == 'not_submitted' and sub:
                db.session.delete(sub)

        existing_grade = Grade.query.filter_by(assignment_id=assignment_id, student_id=student_id).first()
        if existing_grade and existing_grade.is_voided:
            return jsonify({'success': True, 'message': 'Grade voided, not updated'})

        # Empty score = not entered: remove grade row so 0 can stay distinct from blank
        if score_raw == '':
            if existing_grade:
                db.session.delete(existing_grade)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Cleared'})

        try:
            points_earned = float(score_raw)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid score'}), 400

        sub_for_adjustments = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
        adjusted = _apply_assignment_adjustments(
            assignment=assignment,
            entered_points=points_earned,
            submission_record=sub_for_adjustments,
            notes_type=notes_type
        )
        grade_data = {
            'score': adjusted['points_earned'], 'points_earned': adjusted['points_earned'],
            'raw_points': adjusted['raw_points'],
            'extra_credit_points': adjusted['extra_credit_points'],
            'late_penalty_applied': adjusted['late_penalty_applied'],
            'days_late': adjusted['days_late'],
            'total_points': adjusted['total_points'], 'max_score': adjusted['max_score'],
            'percentage': adjusted['percentage'], 'feedback': comment, 'comment': comment,
            'graded_at': datetime.utcnow().isoformat()
        }

        if existing_grade:
            existing_grade.grade_data = json.dumps(grade_data)
            existing_grade.graded_at = datetime.utcnow()
            existing_grade.extra_credit_points = adjusted['extra_credit_points']
            existing_grade.late_penalty_applied = adjusted['late_penalty_applied']
        else:
            new_grade = Grade(
                assignment_id=assignment_id, student_id=student_id,
                grade_data=json.dumps(grade_data),
                graded_at=datetime.utcnow(),
                extra_credit_points=adjusted['extra_credit_points'],
                late_penalty_applied=adjusted['late_penalty_applied']
            )
            db.session.add(new_grade)
            sub = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
            if not sub and adjusted['points_earned'] > 0:
                sub = Submission(
                    student_id=student_id, assignment_id=assignment_id,
                    submission_type='in_person', submission_notes='Auto-marked: grade entered',
                    marked_by=teacher_staff.id if teacher_staff else None,
                    marked_at=datetime.utcnow(), submitted_at=datetime.utcnow(), file_path=None
                )
                db.session.add(sub)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Saved'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/grades/statistics/<int:assignment_id>')
@login_required
@teacher_required
def grade_statistics(assignment_id):
    """Display grade statistics dashboard for an assignment with charts."""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check authorization
    if not is_authorized_for_class(assignment.class_info):
        flash("You are not authorized to view statistics for this assignment.", "danger")
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
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
    letter_grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
    grade_distribution = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '0-59': 0}
    
    total_points = assignment.total_points if assignment.total_points else 100.0
    
    for grade in grades:
        try:
            grade_data = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
            score = get_points_earned(grade_data)
            
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
                    letter_grades['E'] += 1
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
    """Legacy URL: grade management lives under Assignments & Grades."""
    return redirect(url_for('teacher.dashboard.assignments_and_grades'))

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
        return redirect(url_for('teacher.dashboard.assignments_and_grades'))
    
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
    return redirect(url_for('teacher.dashboard.assignments_and_grades'))

