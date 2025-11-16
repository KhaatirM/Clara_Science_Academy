"""
Analytics and reporting routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import db, Class, Assignment, Student, Grade, Submission, Enrollment, Attendance
from sqlalchemy import func
from datetime import datetime, timedelta
import json

bp = Blueprint('analytics', __name__)

@bp.route('/analytics')
@login_required
@teacher_required
def analytics_hub():
    """Redirect to My Classes - analytics should be accessed from class view."""
    flash("Please select a class first to view its analytics.", "info")
    return redirect(url_for('teacher.dashboard.my_classes'))

@bp.route('/analytics/class/<int:class_id>')
@login_required
@teacher_required
def class_analytics(class_id):
    """View analytics for a specific class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to view analytics for this class.", "danger")
        return redirect(url_for('teacher.analytics.analytics_hub'))
    
    # Get enrolled students
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [e.student for e in enrollments if e.student]
    total_students = len(students)
    
    # Get assignments
    assignments = Assignment.query.filter_by(class_id=class_id).all()
    total_assignments = len(assignments)
    
    # Calculate assignment completion rates (excluding voided assignments)
    completed_count = 0
    total_possible = 0
    
    for assignment in assignments:
        # Count students who should have this assignment (not voided for them)
        assignment_grades = Grade.query.filter_by(assignment_id=assignment.id).all()
        voided_student_ids = set()
        for grade in assignment_grades:
            if grade.is_voided:
                voided_student_ids.add(grade.student_id)
        
        # Count non-voided students for this assignment
        non_voided_students = [s for s in students if s.id not in voided_student_ids]
        total_possible += len(non_voided_students)
        
        # Count submissions from non-voided students only
        for student in non_voided_students:
            if Submission.query.filter_by(
                assignment_id=assignment.id,
                student_id=student.id
            ).first():
                completed_count += 1
    
    completion_rate = (completed_count / total_possible * 100) if total_possible > 0 else 0
    
    # Calculate average grade (excluding voided assignments)
    grades = Grade.query.join(Assignment).filter(Assignment.class_id == class_id).all()
    if grades:
        valid_scores = []
        for g in grades:
            # Check if grade is voided using the model field
            if g.is_voided:
                continue
            try:
                grade_data = json.loads(g.grade_data) if g.grade_data else {}
                if grade_data.get('score') is not None:
                    valid_scores.append(float(grade_data['score']))
            except:
                pass
        avg_grade = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    else:
        avg_grade = 0
    
    # Get attendance data (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_attendance = Attendance.query.filter(
        Attendance.class_id == class_id,
        Attendance.date >= thirty_days_ago.date()
    ).all()
    
    present_count = sum(1 for a in recent_attendance if a.status == 'present')
    attendance_rate = (present_count / len(recent_attendance) * 100) if recent_attendance else 0
    
    # Grade distribution
    grade_ranges = {
        'A (90-100)': 0,
        'B (80-89)': 0,
        'C (70-79)': 0,
        'D (60-69)': 0,
        'F (0-59)': 0
    }
    
    for grade in grades:
        # Skip voided grades
        if grade.is_voided:
            continue
        try:
            grade_data = json.loads(grade.grade_data) if grade.grade_data else {}
            if grade_data.get('score') is not None:
                score = float(grade_data['score'])
                if score >= 90:
                    grade_ranges['A (90-100)'] += 1
                elif score >= 80:
                    grade_ranges['B (80-89)'] += 1
                elif score >= 70:
                    grade_ranges['C (70-79)'] += 1
                elif score >= 60:
                    grade_ranges['D (60-69)'] += 1
                else:
                    grade_ranges['F (0-59)'] += 1
        except:
            pass
    
    # Student performance
    student_stats = []
    for student in students:
        student_grades = Grade.query.join(Assignment).filter(
            Assignment.class_id == class_id,
            Grade.student_id == student.id
        ).all()
        
        valid_scores = []
        if student_grades:
            for g in student_grades:
                # Skip voided grades
                if g.is_voided:
                    continue
                try:
                    grade_data = json.loads(g.grade_data) if g.grade_data else {}
                    if grade_data.get('score') is not None:
                        valid_scores.append(float(grade_data['score']))
                except:
                    pass
        
        avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0
        
        # Count submissions for non-voided assignments only
        submissions = 0
        non_voided_assignment_count = 0
        for assignment in assignments:
            # Check if this assignment is voided for this student
            student_grade = Grade.query.filter_by(
                assignment_id=assignment.id,
                student_id=student.id
            ).first()
            
            if student_grade and student_grade.is_voided:
                continue  # Skip voided assignments
            
            non_voided_assignment_count += 1
            if Submission.query.filter_by(
                assignment_id=assignment.id,
                student_id=student.id
            ).first():
                submissions += 1
        
        student_stats.append({
            'student': student,
            'average': round(avg, 1),
            'submissions': submissions,
            'completion': round((submissions / non_voided_assignment_count * 100) if non_voided_assignment_count > 0 else 0, 1)
        })
    
    # Sort by average grade
    student_stats.sort(key=lambda x: x['average'], reverse=True)
    
    return render_template('teachers/teacher_class_analytics.html',
                         class_item=class_obj,
                         total_students=total_students,
                         total_assignments=total_assignments,
                         completion_rate=round(completion_rate, 1),
                         avg_grade=round(avg_grade, 1),
                         attendance_rate=round(attendance_rate, 1),
                         grade_distribution=grade_ranges,
                         student_stats=student_stats)

