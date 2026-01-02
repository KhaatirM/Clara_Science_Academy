"""
Dashboard routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import (
    db, Student, TeacherStaff, Class, Assignment, Grade, Submission, Notification, Enrollment, Attendance
)
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import json
from .utils import update_assignment_statuses

bp = Blueprint('dashboard', __name__)


# ============================================================
# Route: /dashboard
# Function: management_dashboard
# ============================================================

@bp.route('/dashboard')
@login_required
@management_required
def management_dashboard():
    from datetime import datetime, timedelta
    from sqlalchemy import or_, and_
    import json
    from flask import current_app, flash
    
    try:
        # Basic stats
        stats = {
            'students': Student.query.count(),
            'teachers': TeacherStaff.query.count(),
            'classes': Class.query.count(),
            'assignments': Assignment.query.count()
        }
        
        # Calculate monthly stats
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # New students this month (using ID as proxy since no created_at field)
        # This is a simplified approach - in a real system, you'd want a created_at field
        total_students = Student.query.count()
        # For now, we'll use a placeholder since we can't track creation dates
        # In a real implementation, you'd add a created_at field to the Student model
        new_students = 0
        
        # Alternative: Track new enrollments this month
        try:
            new_enrollments = Enrollment.query.filter(Enrollment.enrolled_at >= month_start).count()
        except (AttributeError, Exception) as e:
            current_app.logger.warning(f"Error getting new enrollments: {e}")
            new_enrollments = 0
    
        # Assignments due this week
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        due_assignments = Assignment.query.filter(
            Assignment.due_date >= week_start,
            Assignment.due_date < week_end
        ).count()
        
        # Calculate attendance rate (simplified)
        try:
            total_attendance_records = Attendance.query.count()
            present_records = Attendance.query.filter_by(status='Present').count()
            attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
        except Exception as e:
            current_app.logger.warning(f"Error calculating attendance rate: {e}")
            attendance_rate = 0
        
        # Calculate average grade (simplified)
        grades = Grade.query.all()
        if grades:
            total_score = 0
            valid_grades = 0
            for grade in grades:
                try:
                    grade_data = json.loads(grade.grade_data)
                    if 'score' in grade_data and isinstance(grade_data['score'], (int, float)):
                        total_score += grade_data['score']
                        valid_grades += 1
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue
            
            average_grade = round(total_score / valid_grades, 1) if valid_grades > 0 else 0
        else:
            average_grade = 0
        
        monthly_stats = {
            'new_students': new_enrollments,  # Using new enrollments as proxy for new students
            'attendance_rate': attendance_rate,
            'average_grade': average_grade
        }
        
        weekly_stats = {
            'due_assignments': due_assignments
        }
        
        # --- AT-RISK STUDENT ALERTS ---
        at_risk_alerts = []  # Initialize here to ensure it's always defined
        at_risk_grades = []  # Initialize here to ensure it's always defined
        try:
            students_to_check = Student.query.all() # Management sees all students
            student_ids = [s.id for s in students_to_check]

            # Get ALL non-voided grades for our students (not just overdue ones)
            at_risk_grades = db.session.query(Grade).join(Assignment).join(Student)\
                .filter(Student.id.in_(student_ids))\
                .filter(Grade.is_voided == False)\
                .all()

            seen_student_ids = set()
            for grade in at_risk_grades:
                try:
                    grade_data = json.loads(grade.grade_data)
                    score = grade_data.get('score')
                    is_overdue = grade.assignment.due_date < datetime.utcnow()
                    
                    # Only alert for truly at-risk: missing (overdue with no score) OR failing (score <= 69)
                    # Don't include passing overdue assignments (70+) - they're not at-risk
                    is_at_risk = False
                    alert_reason = None
                    
                    if score is None and is_overdue:
                        # Missing assignment that's overdue
                        is_at_risk = True
                        alert_reason = "overdue"
                    elif score is not None and score <= 69:
                        # Failing assignment
                        is_at_risk = True
                        if is_overdue:
                            alert_reason = "overdue and failing"
                        else:
                            alert_reason = "failing"
                    
                    if is_at_risk:
                        if grade.student.id not in seen_student_ids:
                            at_risk_alerts.append({
                                'student_name': f"{grade.student.first_name} {grade.student.last_name}",
                                'student_user_id': grade.student.id,  # Use student ID instead of user_id
                                'class_name': grade.assignment.class_info.name,
                                'assignment_name': grade.assignment.title,
                                'alert_reason': alert_reason,
                                'score': score,
                                'due_date': grade.assignment.due_date
                            })
                            seen_student_ids.add(grade.student.id)
                except (json.JSONDecodeError, TypeError) as e:
                    current_app.logger.warning(f"Error processing grade {grade.id}: {e}")
                    continue
        except Exception as e:
            current_app.logger.warning(f"Error in alert processing: {e}")
            at_risk_alerts = []  # Ensure it's still a list even if there's an error
        # --- END ALERTS ---
        
        # --- Debugging Print Statements ---
        print(f"--- Debug Dashboard Alerts ---")
        print(f"Checking alerts for user: {current_user.username}, Role: {current_user.role}")
        print(f"Raw at-risk grades query result count: {len(at_risk_grades)}")
        print(f"Formatted alerts list being sent to template: {at_risk_alerts}")
        print(f"--- End Debug ---")
        # --- End Debugging ---
        
        return render_template('management/role_dashboard.html', 
                             stats=stats,
                             monthly_stats=monthly_stats,
                             weekly_stats=weekly_stats,
                             section='home',
                             active_tab='home',
                             at_risk_alerts=at_risk_alerts)
    except Exception as e:
        current_app.logger.error(f"Error in management_dashboard: {e}")
        import traceback
        error_trace = traceback.format_exc()
        current_app.logger.error(error_trace)
        flash(f"Error loading dashboard: {str(e)}", 'danger')
        # Return minimal dashboard with error
        return render_template('management/role_dashboard.html', 
                             stats={'students': 0, 'teachers': 0, 'classes': 0, 'assignments': 0},
                             monthly_stats={},
                             weekly_stats={},
                             section='home',
                             active_tab='home',
                             at_risk_alerts=[])
        current_app.logger.error(f"Error in management_dashboard: {e}")
        import traceback
        error_trace = traceback.format_exc()
        current_app.logger.error(error_trace)
        flash(f"Error loading dashboard: {str(e)}", 'danger')
        # Return minimal dashboard with error
        return render_template('management/role_dashboard.html', 
                             stats={'students': 0, 'teachers': 0, 'classes': 0, 'assignments': 0},
                             monthly_stats={},
                             weekly_stats={},
                             section='home',
                             active_tab='home',
                             at_risk_alerts=[])

# Routes for managing students, teachers, classes etc.
# Example: Add Student


# ============================================================
# Route: /redo-dashboard
# Function: redo_dashboard
# ============================================================

@bp.route('/redo-dashboard')
@login_required
def redo_dashboard():
    """Dashboard showing all active redo opportunities"""
    from datetime import datetime
    
    # Authorization check
    if current_user.role == 'Teacher':
        if not current_user.teacher_staff_id:
            flash('Teacher record not found.', 'danger')
            return redirect(url_for('teacher.teacher_dashboard'))
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        # Get redos for teacher's classes only
        redos = AssignmentRedo.query.join(Assignment).join(Class).filter(
            Class.teacher_id == teacher.id
        ).order_by(AssignmentRedo.redo_deadline.asc()).all()
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Directors and School Administrators see all redos
        redos = AssignmentRedo.query.order_by(AssignmentRedo.redo_deadline.asc()).all()
        classes = Class.query.all()
    
    # Calculate statistics
    active_redos = len([r for r in redos if not r.is_used and not r.final_grade])
    completed_redos = len([r for r in redos if r.final_grade])
    now = datetime.utcnow()
    overdue_redos = len([r for r in redos if not r.is_used and r.redo_deadline < now])
    
    # Calculate average improvement
    improvements = []
    for redo in redos:
        if redo.original_grade and redo.final_grade:
            improvement = redo.final_grade - redo.original_grade
            if improvement > 0:
                improvements.append(improvement)
    
    improvement_rate = round(sum(improvements) / len(improvements), 1) if improvements else 0
    
    return render_template('management/redo_dashboard.html',
                         redos=redos,
                         classes=classes,
                         active_redos=active_redos,
                         completed_redos=completed_redos,
                         improvement_rate=improvement_rate,
                         overdue_redos=overdue_redos,
                         now=now)


