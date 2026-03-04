"""
Routes for Student Assistants: take attendance and enter grades for their assigned class.
All actions are logged. Alerts are sent to teacher and admins when assistant changes
existing grades or records past attendance.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import (
    db, Class, Student, Enrollment, Assignment, Attendance, Grade,
    StudentAssistant, StudentAssistantActionLog, Notification, User, TeacherStaff
)
import json

bp = Blueprint('student_assistant', __name__, url_prefix='/assistant')


def _is_assistant_for_class(class_id):
    """Return True if current user is a Student and is the assigned assistant for this class."""
    if not current_user.is_authenticated or current_user.role != 'Student' or not getattr(current_user, 'student_id', None):
        return False
    return StudentAssistant.query.filter_by(
        class_id=class_id,
        student_id=current_user.student_id
    ).first() is not None


def _require_assistant(class_id):
    """Redirect if not assistant; return (class_obj, None) or (None, response)."""
    class_obj = Class.query.get_or_404(class_id)
    if not _is_assistant_for_class(class_id):
        flash('You are not assigned as student assistant for this class.', 'danger')
        if current_user.role == 'Student':
            return None, redirect(url_for('student.student_dashboard'))
        return None, redirect(url_for('management.classes'))
    return class_obj, None


def _notify_teacher_and_admins(class_id, title, message, link=None):
    """Create notifications for the class teacher and all School Administrators/Directors."""
    try:
        class_obj = Class.query.get(class_id)
        user_ids = set()
        if class_obj and class_obj.teacher_id:
            teacher = TeacherStaff.query.get(class_obj.teacher_id)
            if teacher and hasattr(teacher, 'user') and teacher.user:
                for u in getattr(teacher.user, '__iter__', lambda: [teacher.user])() if hasattr(teacher, 'user') else [teacher.user]:
                    if u and getattr(u, 'id', None):
                        user_ids.add(u.id)
            # TeacherStaff may have backref to user
            from models import User as U
            teacher_user = U.query.filter_by(teacher_staff_id=class_obj.teacher_id).first()
            if teacher_user:
                user_ids.add(teacher_user.id)
        for u in User.query.filter(User.role.in_(['School Administrator', 'Director'])).all():
            user_ids.add(u.id)
        for uid in user_ids:
            n = Notification(
                user_id=uid,
                type='student_assistant_alert',
                title=title,
                message=message,
                link=link or ''
            )
            db.session.add(n)
    except Exception as e:
        current_app.logger.warning(f"Could not create assistant alerts: {e}")


@bp.route('/class/<int:class_id>/attendance', methods=['GET', 'POST'])
@login_required
def take_attendance(class_id):
    """Take attendance for the class (student assistant only). Logs action; alerts if past date."""
    class_obj, err = _require_assistant(class_id)
    if err:
        return err

    from models import SchoolDayAttendance
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [e.student for e in enrollments if e.student]
    if not students:
        flash('No students enrolled in this class.', 'warning')
        return redirect(url_for('student.student_dashboard'))

    statuses = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']
    date_str = request.form.get('date') or request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        attendance_date = datetime.now().date()
        date_str = attendance_date.strftime('%Y-%m-%d')

    if attendance_date > datetime.now().date():
        flash('Cannot take attendance for future dates.', 'warning')
        date_str = datetime.now().strftime('%Y-%m-%d')
        attendance_date = datetime.now().date()

    existing_records = {r.student_id: r for r in Attendance.query.filter_by(class_id=class_id, date=attendance_date).all()}
    school_day_records = {}
    if attendance_date:
        for r in SchoolDayAttendance.query.filter_by(date=attendance_date).all():
            school_day_records[r.student_id] = r

    total = len(students)
    present_count = sum(1 for r in existing_records.values() if r.status == 'Present')
    attendance_stats = {
        'total': total,
        'present': present_count,
        'late': sum(1 for r in existing_records.values() if r.status == 'Late'),
        'absent': sum(1 for r in existing_records.values() if r.status in ['Unexcused Absence', 'Excused Absence']),
        'suspended': sum(1 for r in existing_records.values() if r.status == 'Suspended'),
        'present_percentage': round((present_count / total * 100) if total else 0, 1)
    }

    if request.method == 'POST':
        valid_statuses = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']
        status_map = {
            'present': 'Present', 'late': 'Late',
            'unexcused absence': 'Unexcused Absence', 'excused absence': 'Excused Absence',
            'suspended': 'Suspended'
        }
        changes = []
        for student in students:
            raw = request.form.get(f'status_{student.id}')
            if not raw:
                continue
            status = status_map.get(raw.lower(), raw)
            if status not in valid_statuses:
                continue
            notes = request.form.get(f'notes_{student.id}', '')
            rec = existing_records.get(student.id)
            if rec:
                old_status = rec.status
                rec.status = status
                rec.notes = notes
                rec.teacher_id = None  # assistant, not teacher
                if old_status != status:
                    changes.append((student.id, student.first_name, student.last_name, old_status, status))
            else:
                rec = Attendance(
                    student_id=student.id,
                    class_id=class_id,
                    date=attendance_date,
                    status=status,
                    notes=notes,
                    teacher_id=None
                )
                db.session.add(rec)
                changes.append((student.id, student.first_name, student.last_name, None, status))

        is_past = attendance_date < datetime.now().date()
        action_type = 'past_attendance' if is_past else 'attendance'
        details = {
            'date': date_str,
            'student_ids': [s.id for s in students],
            'changes': [{'student_id': c[0], 'name': f'{c[1]} {c[2]}', 'old': c[3], 'new': c[4]} for c in changes]
        }
        log_entry = StudentAssistantActionLog(
            class_id=class_id,
            assistant_user_id=current_user.id,
            action_type=action_type,
            assignment_id=None,
            details=json.dumps(details),
            alert_sent=False
        )
        db.session.add(log_entry)
        db.session.flush()

        if is_past and changes:
            _notify_teacher_and_admins(
                class_id,
                'Student Assistant: Past attendance recorded',
                f'A student assistant recorded or changed attendance for {attendance_date} ({len(changes)} change(s)). Review the class assistant activity log.',
                link=url_for('management.view_class', class_id=class_id)
            )
            log_entry.alert_sent = True

        try:
            db.session.commit()
            flash('Attendance recorded successfully. Your action has been logged.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving attendance: {str(e)}', 'danger')
        return redirect(url_for('student_assistant.take_attendance', class_id=class_id, date=date_str))

    return render_template(
        'shared/take_attendance.html',
        class_item=class_obj,
        students=students,
        attendance_date_str=date_str,
        statuses=statuses,
        existing_records=existing_records,
        school_day_records=school_day_records,
        attendance_stats=attendance_stats,
        is_student_assistant=True
    )


@bp.route('/class/<int:class_id>/grade/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def grade_assignment(class_id, assignment_id):
    """Enter or change grades for an assignment (student assistant only). Logs and alerts on grade change."""
    class_obj, err = _require_assistant(class_id)
    if err:
        return err
    assignment = Assignment.query.filter_by(id=assignment_id, class_id=class_id).first_or_404()

    from models import Submission
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    student_ids = [e.student_id for e in enrollments if e.student_id]
    students = [e.student for e in enrollments if e.student]

    if request.method == 'POST':
        # Collect previous grades to detect changes
        existing_grades = {}
        for g in Grade.query.filter_by(assignment_id=assignment_id).all():
            if g.student_id in student_ids:
                existing_grades[g.student_id] = g

        raw_pts = assignment.total_points if assignment.total_points else 100.0
        total_points = raw_pts if raw_pts >= 10 else 100.0
        changes = []
        for student_id in student_ids:
            # Handle submission status (Submitted / Not Submitted)
            submission_type = request.form.get(f'submission_type_{student_id}')
            submission_notes = request.form.get(f'submission_notes_{student_id}', '').strip()
            if submission_type:
                submission = Submission.query.filter_by(
                    student_id=student_id,
                    assignment_id=assignment_id
                ).first()
                if submission_type in ['in_person', 'online']:
                    if submission:
                        submission.submission_type = submission_type
                        submission.submission_notes = submission_notes
                        submission.marked_at = datetime.utcnow()
                    else:
                        submission = Submission(
                            student_id=student_id,
                            assignment_id=assignment_id,
                            submission_type=submission_type,
                            submission_notes=submission_notes,
                            marked_by=None,  # Student assistant - no teacher_staff
                            marked_at=datetime.utcnow(),
                            submitted_at=datetime.utcnow(),
                            file_path=None
                        )
                        db.session.add(submission)
                elif submission_type == 'not_submitted' and submission:
                    db.session.delete(submission)

            score_val = request.form.get(f'score_{student_id}')
            if score_val is None or score_val == '':
                continue
            try:
                score = float(score_val)
            except ValueError:
                continue
            comment = request.form.get(f'comment_{student_id}', '').strip()
            percentage = round((score / total_points * 100) if total_points else 0, 2)
            grade_data = {
                'score': score,
                'points_earned': score,
                'total_points': total_points,
                'percentage': percentage,
                'feedback': comment,
                'graded_at': datetime.utcnow().isoformat()
            }
            g = existing_grades.get(student_id)
            if g:
                if g.is_voided:
                    continue
                try:
                    old_data = json.loads(g.grade_data) if g.grade_data else {}
                    old_score = old_data.get('score', old_data.get('points_earned'))
                    if old_score is not None and float(old_score) != score:
                        student = next((s for s in students if s.id == student_id), None)
                        name = f'{student.first_name} {student.last_name}' if student else str(student_id)
                        changes.append({'student_id': student_id, 'name': name, 'old': old_score, 'new': score})
                except (json.JSONDecodeError, TypeError):
                    pass
                g.grade_data = json.dumps(grade_data)
                g.graded_at = datetime.utcnow()
            else:
                g = Grade(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    grade_data=json.dumps(grade_data),
                    graded_at=datetime.utcnow(),
                    is_voided=False
                )
                db.session.add(g)

        action_type = 'grade_change' if changes else 'grade_entry'
        details = {
            'assignment_id': assignment_id,
            'assignment_title': assignment.title,
            'student_ids': student_ids,
            'changes': changes
        }
        log_entry = StudentAssistantActionLog(
            class_id=class_id,
            assistant_user_id=current_user.id,
            action_type=action_type,
            assignment_id=assignment_id,
            details=json.dumps(details),
            alert_sent=False
        )
        db.session.add(log_entry)
        db.session.flush()

        if changes:
            _notify_teacher_and_admins(
                class_id,
                'Student Assistant: Grade(s) changed',
                f'A student assistant changed existing grade(s) for "{assignment.title}" ({len(changes)} student(s)). Review the class assistant activity log.',
                link=url_for('management.view_class', class_id=class_id)
            )
            log_entry.alert_sent = True

        try:
            db.session.commit()
            flash('Grades saved. Your action has been logged.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving grades: {str(e)}', 'danger')
        return redirect(url_for('student_assistant.grade_assignment', class_id=class_id, assignment_id=assignment_id))

    # GET: show grading form (simplified - one score per student)
    grades = Grade.query.filter_by(assignment_id=assignment_id).all()
    grades_by_student = {g.student_id: g for g in grades}
    submissions = {s.student_id: s for s in Submission.query.filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id.in_(student_ids)
    ).all()} if student_ids else {}

    # Use assignment total_points; if < 10 (e.g. 1.0 from misconfigured quiz), use 100 for typical grading scale
    raw_points = assignment.total_points if assignment.total_points else 100.0
    total_points = raw_points if raw_points >= 10 else 100.0
    return render_template(
        'management/student_assistant_grade_assignment.html',
        class_obj=class_obj,
        assignment=assignment,
        students=students,
        grades_by_student=grades_by_student,
        submissions=submissions,
        total_points=total_points
    )


@bp.route('/class/<int:class_id>')
@login_required
def class_hub(class_id):
    """Hub for assistant: links to take attendance and list assignments to grade."""
    class_obj, err = _require_assistant(class_id)
    if err:
        return err
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    return render_template(
        'management/student_assistant_hub.html',
        class_obj=class_obj,
        assignments=assignments
    )
