"""
Dashboard routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import (
    db, Student, TeacherStaff, Class, Assignment, Grade, Submission, Notification, Enrollment, Attendance, AssignmentRedo, AssignmentReopening,
    User, ExtensionRequest
)
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
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
        # Check if enrolled_at column exists before using it
        new_enrollments = 0
        try:
            # Check if Enrollment model has enrolled_at attribute
            if hasattr(Enrollment, 'enrolled_at'):
                new_enrollments = Enrollment.query.filter(Enrollment.enrolled_at >= month_start).count()
            else:
                # Fallback: count all active enrollments if enrolled_at doesn't exist
                new_enrollments = Enrollment.query.filter(Enrollment.is_active == True).count()
        except Exception as e:
            # Handle any database errors gracefully
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
            
            # Get group assignments and group grades
            from models import GroupAssignment, GroupGrade, StudentGroup, StudentGroupMember, Enrollment
            group_assignments = GroupAssignment.query.all()
            
            # Get group grades for all students
            group_grades = []
            if group_assignments:
                group_assignment_ids = [ga.id for ga in group_assignments]
                # Get all groups
                groups = StudentGroup.query.all()
                group_ids = [g.id for g in groups]
                
                # Get group members for our students
                if group_ids and student_ids:
                    group_members = StudentGroupMember.query.filter(
                        StudentGroupMember.group_id.in_(group_ids),
                        StudentGroupMember.student_id.in_(student_ids)
                    ).all()
                    
                    # Get group grades for these groups
                    if group_members:
                        member_group_ids = [gm.group_id for gm in group_members]
                        group_grades = GroupGrade.query.filter(
                            GroupGrade.group_assignment_id.in_(group_assignment_ids)
                        ).join(StudentGroup).filter(
                            StudentGroup.id.in_(member_group_ids)
                        ).all()
            
            # Check for missing assignments (assignments with no grade record)
            missing_assignments = []
            # Get all active assignments
            all_assignments = Assignment.query.filter(
                Assignment.status == 'Active',
                Assignment.due_date.isnot(None)
            ).all()
            
            # For each assignment, check if each enrolled student has a grade
            for assignment in all_assignments:
                if assignment.due_date < datetime.utcnow():  # Only check overdue assignments
                    # Get students enrolled in this class
                    class_enrollments = Enrollment.query.filter_by(
                        class_id=assignment.class_id,
                        is_active=True
                    ).all()
                    class_student_ids = [e.student_id for e in class_enrollments if e.student_id in student_ids]
                    
                    for student_id in class_student_ids:
                        # Check if grade exists
                        existing_grade = Grade.query.filter_by(
                            student_id=student_id,
                            assignment_id=assignment.id
                        ).first()
                        
                        if not existing_grade:
                            # Missing assignment - no grade record exists
                            student = Student.query.get(student_id)
                            if student:
                                missing_assignments.append({
                                    'student_id': student_id,
                                    'student_name': f"{student.first_name} {student.last_name}",
                                    'assignment': assignment,
                                    'class_name': assignment.class_info.name if assignment.class_info else 'Unknown Class',
                                    'assignment_name': assignment.title,
                                    'assignment_type': assignment.assignment_type,
                                    'due_date': assignment.due_date
                                })

            seen_student_ids = set()
            
            # Process individual assignment grades
            for grade in at_risk_grades:
                try:
                    # Check if grade has required relationships
                    if not grade.assignment or not grade.student:
                        continue
                    
                    # Check if assignment has due_date
                    if not grade.assignment.due_date:
                        continue
                    
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
                            # Safely get class name
                            class_name = grade.assignment.class_info.name if grade.assignment.class_info else 'Unknown Class'
                            
                            at_risk_alerts.append({
                                'student_name': f"{grade.student.first_name} {grade.student.last_name}",
                                'student_user_id': grade.student.id,  # Use student ID instead of user_id
                                'class_name': class_name,
                                'assignment_name': grade.assignment.title,
                                'assignment_type': grade.assignment.assignment_type,
                                'alert_reason': alert_reason,
                                'score': score,
                                'due_date': grade.assignment.due_date
                            })
                            seen_student_ids.add(grade.student.id)
                except (json.JSONDecodeError, TypeError, AttributeError) as e:
                    current_app.logger.warning(f"Error processing grade {grade.id}: {e}")
                    continue
            
            # Process group assignment grades
            for group_grade in group_grades:
                try:
                    if not group_grade.group_assignment or not group_grade.group:
                        continue
                        
                    grade_data = json.loads(group_grade.grade_data) if group_grade.grade_data else {}
                    score = grade_data.get('score') if grade_data else None
                    is_overdue = group_grade.group_assignment.due_date < datetime.utcnow()
                    
                    is_at_risk = False
                    alert_reason = None
                    
                    if score is None and is_overdue:
                        is_at_risk = True
                        alert_reason = "overdue"
                    elif score is not None and score <= 69:
                        is_at_risk = True
                        if is_overdue:
                            alert_reason = "overdue and failing"
                        else:
                            alert_reason = "failing"
                    
                    if is_at_risk:
                        # Get all students in this group
                        group_members = StudentGroupMember.query.filter_by(
                            group_id=group_grade.group_id
                        ).all()
                        
                        for member in group_members:
                            if member.student_id not in seen_student_ids:
                                student = Student.query.get(member.student_id)
                                if student:
                                    at_risk_alerts.append({
                                        'student_name': f"{student.first_name} {student.last_name}",
                                        'student_user_id': student.id,
                                        'class_name': group_grade.group_assignment.class_info.name if group_grade.group_assignment.class_info else 'Unknown Class',
                                        'assignment_name': group_grade.group_assignment.title,
                                        'assignment_type': f"group_{group_grade.group_assignment.assignment_type}",
                                        'alert_reason': alert_reason,
                                        'score': score,
                                        'due_date': group_grade.group_assignment.due_date
                                    })
                                    seen_student_ids.add(student.id)
                except (json.JSONDecodeError, TypeError, AttributeError) as e:
                    current_app.logger.warning(f"Error processing group grade {group_grade.id}: {e}")
                    continue
            
            # Process missing assignments (no grade record exists)
            for missing in missing_assignments:
                if missing['student_id'] not in seen_student_ids:
                    at_risk_alerts.append({
                        'student_name': missing['student_name'],
                        'student_user_id': missing['student_id'],
                        'class_name': missing['class_name'],
                        'assignment_name': missing['assignment_name'],
                        'assignment_type': missing['assignment_type'],
                        'alert_reason': 'overdue',
                        'score': None,
                        'due_date': missing['due_date']
                    })
                    seen_student_ids.add(missing['student_id'])
        except Exception as e:
            current_app.logger.warning(f"Error in alert processing: {e}")
            at_risk_alerts = []  # Ensure it's still a list even if there's an error
        # --- END ALERTS ---
        
        # --- Notifications & Recent Activity (only last 7 days, limited count) ---
        activity_cutoff = now - timedelta(days=7)
        notifications = Notification.query.filter(
            Notification.user_id == current_user.id,
            Notification.timestamp >= activity_cutoff
        ).order_by(Notification.timestamp.desc()).limit(5).all()

        recent_activity = []
        # Extension requests (requested or reviewed in last 7 days)
        for ext in ExtensionRequest.query.filter(
            or_(ExtensionRequest.requested_at >= activity_cutoff, and_(ExtensionRequest.reviewed_at.isnot(None), ExtensionRequest.reviewed_at >= activity_cutoff))
        ).order_by(ExtensionRequest.requested_at.desc()).limit(5).all():
            try:
                if ext.reviewed_at:
                    recent_activity.append({
                        'type': 'extension_request',
                        'title': f'Extension {ext.status.lower()} for {ext.assignment.title}',
                        'description': f'{ext.student.first_name} {ext.student.last_name} – {ext.status}',
                        'timestamp': ext.reviewed_at,
                        'link': url_for('management.view_extension_requests')
                    })
                else:
                    recent_activity.append({
                        'type': 'extension_request',
                        'title': f'New extension request: {ext.assignment.title}',
                        'description': f'{ext.student.first_name} {ext.student.last_name} requested extension',
                        'timestamp': ext.requested_at,
                        'link': url_for('management.view_extension_requests')
                    })
            except (AttributeError, TypeError):
                continue
        # Recent grades (school-wide, last 7 days)
        for grade in Grade.query.join(Assignment).filter(Grade.graded_at >= activity_cutoff).order_by(Grade.graded_at.desc()).limit(5).all():
            try:
                if not grade.assignment or not grade.student:
                    continue
                recent_activity.append({
                    'type': 'grade',
                    'title': f'Grade entered for {grade.assignment.title}',
                    'description': f'{grade.student.first_name} {grade.student.last_name}',
                    'timestamp': grade.graded_at or datetime.utcnow(),
                    'link': url_for('management.grade_assignment', assignment_id=grade.assignment_id)
                })
            except (AttributeError, TypeError):
                continue
        # Recent submissions (last 7 days)
        for sub in Submission.query.join(Assignment).filter(Submission.submitted_at >= activity_cutoff).order_by(Submission.submitted_at.desc()).limit(5).all():
            try:
                if not sub.assignment or not sub.student:
                    continue
                recent_activity.append({
                    'type': 'submission',
                    'title': f'Submission for {sub.assignment.title}',
                    'description': f'{sub.student.first_name} {sub.student.last_name} submitted',
                    'timestamp': sub.submitted_at or datetime.utcnow(),
                    'link': url_for('management.grade_assignment', assignment_id=sub.assignment_id)
                })
            except (AttributeError, TypeError):
                continue
        # Recent assignments created (last 7 days)
        for assignment in Assignment.query.filter(Assignment.created_at >= activity_cutoff).order_by(Assignment.created_at.desc()).limit(5).all():
            try:
                class_name = assignment.class_info.name if assignment.class_info else 'Unknown'
                recent_activity.append({
                    'type': 'assignment',
                    'title': f'New assignment: {assignment.title}',
                    'description': f'Created for {class_name}',
                    'timestamp': assignment.created_at or datetime.utcnow(),
                    'link': url_for('management.view_assignment', assignment_id=assignment.id)
                })
            except (AttributeError, TypeError):
                continue
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activity = recent_activity[:5]

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
                             at_risk_alerts=at_risk_alerts,
                             notifications=notifications,
                             recent_activity=recent_activity)
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
                             at_risk_alerts=[],
                             notifications=[],
                             recent_activity=[])

# Routes for managing students, teachers, classes etc.
# Example: Add Student


# ============================================================
# Route: /redo-dashboard
# Function: redo_dashboard
# ============================================================

@bp.route('/redo-dashboard')
@login_required
def redo_dashboard():
    """Dashboard showing all active redo opportunities and reopenings"""
    from datetime import datetime
    from models import AssignmentRedo, AssignmentReopening, Assignment, Class, TeacherStaff
    from sqlalchemy.orm import joinedload
    
    # Authorization check
    if current_user.role == 'Teacher':
        if not current_user.teacher_staff_id:
            flash('Teacher record not found.', 'danger')
            return redirect(url_for('teacher.dashboard.teacher_dashboard'))
        teacher = TeacherStaff.query.get(current_user.teacher_staff_id)
        # Get redos for teacher's classes only
        redos = AssignmentRedo.query.join(Assignment).join(Class).filter(
            Class.teacher_id == teacher.id
        ).options(
            joinedload(AssignmentRedo.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentRedo.student)
        ).order_by(AssignmentRedo.redo_deadline.asc()).all()
        
        # Get reopenings for teacher's classes only
        reopenings = AssignmentReopening.query.join(Assignment).join(Class).filter(
            Class.teacher_id == teacher.id,
            AssignmentReopening.is_active == True
        ).options(
            joinedload(AssignmentReopening.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentReopening.student)
        ).order_by(AssignmentReopening.reopened_at.desc()).all()
        
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    else:
        # Directors and School Administrators see all redos and reopenings
        redos = AssignmentRedo.query.options(
            joinedload(AssignmentRedo.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentRedo.student)
        ).order_by(AssignmentRedo.redo_deadline.asc()).all()
        
        reopenings = AssignmentReopening.query.filter(
            AssignmentReopening.is_active == True
        ).options(
            joinedload(AssignmentReopening.assignment).joinedload(Assignment.class_info),
            joinedload(AssignmentReopening.student)
        ).order_by(AssignmentReopening.reopened_at.desc()).all()
        
        classes = Class.query.all()
    
    # Filter out records with missing assignments or students (data integrity check)
    redos = [r for r in redos if r.assignment and r.student]
    reopenings = [r for r in reopenings if r.assignment and r.student]
    
    # Calculate statistics
    active_redos = len([r for r in redos if not r.is_used and not r.final_grade])
    completed_redos = len([r for r in redos if r.final_grade])
    now = datetime.utcnow()
    overdue_redos = len([r for r in redos if not r.is_used and r.redo_deadline and r.redo_deadline < now])
    active_reopenings = len(reopenings)
    
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
                         reopenings=reopenings,
                         classes=classes,
                         active_redos=active_redos,
                         completed_redos=completed_redos,
                         active_reopenings=active_reopenings,
                         improvement_rate=improvement_rate,
                         overdue_redos=overdue_redos,
                         now=now)


