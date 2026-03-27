"""
Routes for Student Assistants: take attendance and enter grades for their assigned class.
All actions are logged. Alerts are sent to teacher and admins when assistant changes
existing grades or records past attendance.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from werkzeug.utils import secure_filename
import os
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import (
    db, Class, Student, Enrollment, Assignment, AssignmentAttachment, Attendance, Grade,
    StudentAssistant, StudentAssistantActionLog, Notification, User, TeacherStaff,
    GroupAssignment, StudentGroup, StudentGroupMember, SchoolYear,
)
import json

bp = Blueprint('student_assistant', __name__, url_prefix='/assistant')


@bp.route('/')
@login_required
def assistant_console():
    """Pick a class to work in as student assistant (especially helpful when assisting two classes)."""
    if current_user.role != 'Student' or not getattr(current_user, 'student_id', None):
        flash('This page is only for student assistants.', 'warning')
        return redirect(url_for('student.student_dashboard'))
    classes = _assistant_classes_for_user()
    if not classes:
        flash('You are not assigned as a student assistant for any class.', 'info')
        return redirect(url_for('student.student_dashboard'))
    return render_template(
        'management/student_assistant_console.html',
        assistant_classes=classes,
    )


def _is_assistant_for_class(class_id):
    """Return True if current user is a Student and is the assigned assistant for this class."""
    if not current_user.is_authenticated or current_user.role != 'Student' or not getattr(current_user, 'student_id', None):
        return False
    return StudentAssistant.query.filter_by(
        class_id=class_id,
        student_id=current_user.student_id
    ).first() is not None


def _assistant_classes_for_user():
    """All classes the current user is a student assistant for (sorted by name). Non-students get []."""
    if not current_user.is_authenticated or current_user.role != 'Student' or not getattr(current_user, 'student_id', None):
        return []
    rows = StudentAssistant.query.filter_by(student_id=current_user.student_id).all()
    classes = [sa.class_info for sa in rows if sa.class_info]
    classes.sort(key=lambda c: ((c.name or '').lower(), c.id))
    return classes


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
        is_student_assistant=True,
        assistant_classes=_assistant_classes_for_user(),
        current_class_id=class_id,
    )


@bp.route('/class/<int:class_id>/grade/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def grade_assignment(class_id, assignment_id):
    """Enter or change grades for an assignment (student assistant only). Logs and alerts on grade change."""
    class_obj, err = _require_assistant(class_id)
    if err:
        return err
    assignment = Assignment.query.filter_by(id=assignment_id, class_id=class_id).first_or_404()
    from management_routes.student_assistant_utils import assignment_visible_to_students
    if not assignment_visible_to_students(assignment):
        flash('This assignment is not available for grading yet (it may still be awaiting teacher approval).', 'warning')
        return redirect(url_for('student_assistant.class_hub', class_id=class_id))

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
            notes_type = request.form.get(f'submission_notes_type_{student_id}', 'On-Time')
            notes_other = request.form.get(f'submission_notes_{student_id}', '').strip()
            submission_notes = notes_other if notes_type == 'Other' else notes_type
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
        total_points=total_points,
        assistant_classes=_assistant_classes_for_user(),
        current_class_id=class_id,
    )


@bp.route('/class/<int:class_id>/grade-group/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def grade_group_assignment(class_id, assignment_id):
    """Enter or change grades for a group assignment (student assistant only).
    Can grade every group except the group they are in (if they're in a group that has this assignment).
    """
    class_obj, err = _require_assistant(class_id)
    if err:
        return err

    from models import (
        GroupAssignment, StudentGroup, StudentGroupMember, GroupGrade,
        GroupAssignmentExtension, Student, GroupSubmission
    )
    from types import SimpleNamespace

    group_assignment = GroupAssignment.query.filter_by(
        id=assignment_id, class_id=class_id
    ).first_or_404()
    from management_routes.student_assistant_utils import assignment_visible_to_students
    if not assignment_visible_to_students(group_assignment):
        flash('This group assignment is not available for grading yet (it may still be awaiting teacher approval).', 'warning')
        return redirect(url_for('student_assistant.class_hub', class_id=class_id))

    # Get groups for this assignment (same logic as admin)
    if group_assignment.selected_group_ids:
        try:
            selected_ids = json.loads(group_assignment.selected_group_ids) if isinstance(
                group_assignment.selected_group_ids, str
            ) else group_assignment.selected_group_ids
            groups = StudentGroup.query.filter(
                StudentGroup.class_id == group_assignment.class_id,
                StudentGroup.is_active == True,
                StudentGroup.id.in_(selected_ids)
            ).all()
        except Exception:
            groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()
    else:
        groups = StudentGroup.query.filter_by(class_id=group_assignment.class_id, is_active=True).all()

    groups = list(groups)

    # Exclude the assistant's own group if they are in a group that has this assignment
    assistant_group_id = None
    if current_user.student_id:
        membership = StudentGroupMember.query.join(StudentGroup).filter(
            StudentGroupMember.student_id == current_user.student_id,
            StudentGroup.class_id == group_assignment.class_id
        ).first()
        if membership:
            assistant_group_id = membership.group_id
            # Only exclude if assistant's group is in the assignment's groups
            if any(getattr(g, 'id', None) == assistant_group_id for g in groups):
                groups = [g for g in groups if getattr(g, 'id', None) != assistant_group_id]

    # Collect students from remaining groups
    all_students = []
    students_by_id = {}
    for group in groups:
        for member in group.members:
            if member.student and member.student.id not in students_by_id:
                all_students.append(member.student)
                students_by_id[member.student.id] = member.student

    if not students_by_id and group_assignment.class_id:
        for enr in Enrollment.query.filter_by(class_id=group_assignment.class_id).all():
            if getattr(enr, 'student', None) and enr.student.id not in students_by_id:
                all_students.append(enr.student)
                students_by_id[enr.student.id] = enr.student
        if all_students:
            virtual_roster = SimpleNamespace(
                id=0,
                name='Class roster',
                members=[SimpleNamespace(student=s) for s in all_students]
            )
            groups.insert(0, virtual_roster)

    if not groups:
        flash('No groups available for you to grade. (Your own group is excluded if you are in one.)', 'warning')
        return redirect(url_for('student_assistant.class_hub', class_id=class_id))

    # Get existing grades
    grades_by_student = {}
    try:
        for grade in GroupGrade.query.filter_by(group_assignment_id=assignment_id).all():
            if grade.grade_data:
                try:
                    gd = json.loads(grade.grade_data) if isinstance(grade.grade_data, str) else grade.grade_data
                    gd['comment'] = grade.comments or ''
                    gd['comments'] = grade.comments or ''
                    grades_by_student[grade.student_id] = gd
                except Exception:
                    grades_by_student[grade.student_id] = {'score': 0, 'comments': '', 'comment': ''}
    except Exception:
        pass

    # Include orphan grades (students from deleted group)
    orphan_student_ids = [sid for sid in grades_by_student if sid not in students_by_id]
    if orphan_student_ids:
        orphan_students = Student.query.filter(Student.id.in_(orphan_student_ids)).all()
        if orphan_students:
            virtual_group = SimpleNamespace(
                id=0,
                name='Students from deleted group',
                members=[SimpleNamespace(student=s) for s in orphan_students]
            )
            groups.append(virtual_group)
            for s in orphan_students:
                if s.id not in students_by_id:
                    all_students.append(s)
                    students_by_id[s.id] = s

    extensions = GroupAssignmentExtension.query.filter_by(
        group_assignment_id=assignment_id, is_active=True
    ).all()
    extensions_dict = {ext.student_id: ext for ext in extensions}

    group_submission_status = {}
    for sub in GroupSubmission.query.filter_by(group_assignment_id=assignment_id).all():
        if sub.group_id and (sub.attachment_file_path or sub.attachment_filename):
            group_submission_status[sub.group_id] = 'online'

    total_students = len(all_students)
    graded_count = len([g for g in grades_by_student.values() if g.get('score', 0) > 0])
    total_score = sum(g.get('score', 0) for g in grades_by_student.values() if g.get('score', 0) > 0)
    average_score = (total_score / graded_count) if graded_count > 0 else 0

    if request.method == 'POST':
        try:
            valid_score_keys = {}
            for group in groups:
                gid = getattr(group, 'id', None)
                for member in group.members:
                    student = getattr(member, 'student', None)
                    if student and getattr(student, 'id', None):
                        valid_score_keys[f"score_{gid}_{student.id}"] = (gid, student.id)
            valid_student_ids = set(students_by_id.keys())

            graded_by_id = None  # Student assistant - no teacher
            total_points = group_assignment.total_points if group_assignment.total_points else 100.0
            effective_max = max(total_points, 100.0)
            saved_count = 0
            changes = []

            for key in request.form:
                if not key.startswith('score_'):
                    continue
                parts = key.split('_')
                if len(parts) != 3:
                    continue
                try:
                    gid = int(parts[1])
                    student_id = int(parts[2])
                except (ValueError, TypeError):
                    continue
                if student_id not in valid_student_ids:
                    continue
                if key not in valid_score_keys:
                    valid_score_keys[key] = (gid, student_id)
                score = request.form.get(key)
                comments_key = f"comments_{gid}_{student_id}"
                comments = request.form.get(comments_key, '')
                submission_type_key = f"submission_type_{gid}_{student_id}"
                submission_type = request.form.get(submission_type_key, '').strip() or 'not_submitted'
                notes_type_key = f"submission_notes_type_{gid}_{student_id}"
                notes_type = request.form.get(notes_type_key, 'On-Time').strip()
                notes_other_key = f"submission_notes_{gid}_{student_id}"
                notes_other = request.form.get(notes_other_key, '').strip()
                try:
                    points_earned = float(score) if (score and str(score).strip()) else 0.0
                except (ValueError, TypeError):
                    points_earned = 0.0
                if not (0 <= points_earned <= effective_max):
                    continue
                if total_points > 0 and total_points < 100 and points_earned > total_points and points_earned <= 100:
                    points_earned = round(points_earned / 100.0 * total_points, 2)
                    display_total = total_points
                else:
                    display_total = total_points
                percentage = (points_earned / display_total * 100) if display_total > 0 else 0
                letter_grade = 'A' if percentage >= 90 else ('B' if percentage >= 80 else ('C' if percentage >= 70 else ('D' if percentage >= 60 else 'D')))
                grade_data = {
                    'score': points_earned,
                    'points_earned': points_earned,
                    'total_points': display_total,
                    'max_score': display_total,
                    'percentage': round(percentage, 2),
                    'letter_grade': letter_grade
                }
                if submission_type in ('online', 'in_person', 'not_submitted'):
                    grade_data['submission_type'] = submission_type
                grade_data['submission_notes'] = notes_other if notes_type == 'Other' else (notes_type or 'On-Time')
                save_group_id = None if gid == 0 else gid

                existing_grade = GroupGrade.query.filter_by(
                    group_assignment_id=assignment_id,
                    student_id=student_id
                ).first()
                if existing_grade:
                    try:
                        old_data = json.loads(existing_grade.grade_data) if existing_grade.grade_data else {}
                        old_score = old_data.get('score', old_data.get('points_earned'))
                        if old_score is not None and float(old_score) != points_earned:
                            student = students_by_id.get(student_id)
                            name = f'{student.first_name} {student.last_name}' if student else str(student_id)
                            changes.append({'student_id': student_id, 'name': name, 'old': old_score, 'new': points_earned})
                    except (json.JSONDecodeError, TypeError):
                        pass
                    existing_grade.grade_data = json.dumps(grade_data)
                    existing_grade.comments = comments
                    existing_grade.group_id = save_group_id
                    existing_grade.graded_by = graded_by_id
                else:
                    new_grade = GroupGrade(
                        group_assignment_id=assignment_id,
                        group_id=save_group_id,
                        student_id=student_id,
                        grade_data=json.dumps(grade_data),
                        graded_by=graded_by_id,
                        comments=comments
                    )
                    db.session.add(new_grade)
                saved_count += 1

            log_entry = StudentAssistantActionLog(
                class_id=class_id,
                assistant_user_id=current_user.id,
                action_type='grade_change' if changes else 'grade_entry',
                assignment_id=None,  # FK is to Assignment; group_assignment id stored in details
                details=json.dumps({
                    'group_assignment_id': assignment_id,
                    'assignment_title': group_assignment.title,
                    'group_assignment': True,
                    'changes': changes
                }),
                alert_sent=False
            )
            db.session.add(log_entry)
            db.session.flush()

            if changes:
                _notify_teacher_and_admins(
                    class_id,
                    'Student Assistant: Group grade(s) changed',
                    f'A student assistant changed existing grade(s) for group assignment "{group_assignment.title}" ({len(changes)} student(s)). Review the class assistant activity log.',
                    link=url_for('management.view_class', class_id=class_id)
                )
                log_entry.alert_sent = True

            db.session.commit()

            wants_json = request.accept_mimetypes.accept_json or \
                        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                        'application/json' in (request.headers.get('Accept') or '')

            if wants_json:
                return jsonify({
                    'success': True,
                    'message': 'Grades saved successfully!',
                    'graded_count': saved_count
                })
            flash('Grades saved. Your action has been logged.', 'success')
            return redirect(url_for('student_assistant.grade_group_assignment', class_id=class_id, assignment_id=assignment_id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"Student assistant group grade error: {e}")
            flash('Error saving grades. Please try again.', 'danger')

    assignment_total_points = group_assignment.total_points if group_assignment.total_points else 100.0

    return render_template(
        'management/admin_grade_group_assignment.html',
        group_assignment=group_assignment,
        class_obj=group_assignment.class_info,
        groups=groups,
        students=all_students,
        grades=grades_by_student,
        extensions=extensions_dict,
        total_students=total_students,
        graded_count=graded_count,
        average_score=average_score,
        total_points=assignment_total_points,
        group_submission_status=group_submission_status,
        today=datetime.now().date(),
        is_student_assistant=True,
        back_url=url_for('student_assistant.class_hub', class_id=class_id),
        cancel_url=url_for('student_assistant.class_hub', class_id=class_id),
        assistant_classes=_assistant_classes_for_user(),
        current_class_id=class_id,
    )


@bp.route('/class/<int:class_id>')
@login_required
def class_hub(class_id):
    """Hub for assistant: links to take attendance and list assignments to grade."""
    class_obj, err = _require_assistant(class_id)
    if err:
        return err
    from management_routes.student_assistant_utils import (
        assignment_student_visibility_filter,
        group_assignment_student_visibility_filter,
        ASSISTANT_APPROVAL_PENDING,
        ASSISTANT_APPROVAL_REJECTED,
    )

    assignments = Assignment.query.filter(
        Assignment.class_id == class_id,
        Assignment.status != 'Voided',
        assignment_student_visibility_filter(),
    ).order_by(Assignment.due_date.desc()).all()

    group_assignments = GroupAssignment.query.filter(
        GroupAssignment.class_id == class_id,
        GroupAssignment.status != 'Voided',
        group_assignment_student_visibility_filter(),
    ).order_by(GroupAssignment.due_date.desc()).all()

    sid = current_user.student_id
    my_pending_assignments = Assignment.query.filter(
        Assignment.class_id == class_id,
        Assignment.proposed_by_student_id == sid,
        Assignment.assistant_approval_status == ASSISTANT_APPROVAL_PENDING,
    ).order_by(Assignment.created_at.desc()).all()
    my_pending_group = GroupAssignment.query.filter(
        GroupAssignment.class_id == class_id,
        GroupAssignment.proposed_by_student_id == sid,
        GroupAssignment.assistant_approval_status == ASSISTANT_APPROVAL_PENDING,
    ).order_by(GroupAssignment.created_at.desc()).all()
    my_rejected_assignments = Assignment.query.filter(
        Assignment.class_id == class_id,
        Assignment.proposed_by_student_id == sid,
        Assignment.assistant_approval_status == ASSISTANT_APPROVAL_REJECTED,
    ).order_by(Assignment.assistant_approval_reviewed_at.desc()).limit(15).all()
    my_rejected_group = GroupAssignment.query.filter(
        GroupAssignment.class_id == class_id,
        GroupAssignment.proposed_by_student_id == sid,
        GroupAssignment.assistant_approval_status == ASSISTANT_APPROVAL_REJECTED,
    ).order_by(GroupAssignment.assistant_approval_reviewed_at.desc()).limit(15).all()

    return render_template(
        'management/student_assistant_hub.html',
        class_obj=class_obj,
        assignments=assignments,
        group_assignments=group_assignments,
        my_pending_assignments=my_pending_assignments,
        my_pending_group=my_pending_group,
        my_rejected_assignments=my_rejected_assignments,
        my_rejected_group=my_rejected_group,
        assistant_classes=_assistant_classes_for_user(),
        current_class_id=class_id,
    )


def _assistant_allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'xls', 'xlsx', 'ppt', 'pptx'}


@bp.route('/class/<int:class_id>/assignments/new', methods=['GET', 'POST'])
@login_required
def assistant_add_assignment(class_id):
    """Create a PDF/paper assignment proposal (requires teacher or school admin approval)."""
    class_obj, err = _require_assistant(class_id)
    if err:
        return err

    from management_routes.student_assistant_utils import ASSISTANT_APPROVAL_PENDING
    from teacher_routes.utils import get_current_quarter
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None
    from datetime import time as time_cls

    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            due_date_str = request.form.get('due_date')
            quarter = request.form.get('quarter')
            assignment_context = request.form.get('assignment_context', 'homework')
            total_points = request.form.get('total_points', type=float)

            if not all([title, due_date_str, quarter]):
                flash('Title, Due Date, and Quarter are required.', 'danger')
                return redirect(url_for('student_assistant.assistant_add_assignment', class_id=class_id))

            if total_points is None or total_points <= 0:
                total_points = 100.0

            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')

            open_date_str = request.form.get('open_date', '').strip()
            close_date_str = request.form.get('close_date', '').strip()
            open_date = None
            close_date = None
            if open_date_str:
                try:
                    open_date = datetime.strptime(open_date_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
            if close_date_str:
                try:
                    close_date = datetime.strptime(close_date_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    pass
            if not close_date:
                close_date = due_date

            current_school_year = SchoolYear.query.filter_by(is_active=True).first()
            if not current_school_year:
                flash('Cannot create assignment: No active school year.', 'danger')
                return redirect(url_for('student_assistant.assistant_add_assignment', class_id=class_id))

            new_assignment = Assignment(
                title=title,
                description=description,
                due_date=due_date,
                open_date=open_date,
                close_date=close_date,
                quarter=quarter,
                class_id=class_id,
                school_year_id=current_school_year.id,
                assignment_type='pdf_paper',
                status='Inactive',
                assignment_context=assignment_context,
                total_points=total_points,
                created_by=current_user.id,
                assistant_approval_status=ASSISTANT_APPROVAL_PENDING,
                proposed_by_student_id=current_user.student_id,
            )
            db.session.add(new_assignment)
            db.session.flush()

            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments')
            os.makedirs(upload_dir, exist_ok=True)
            files_to_save = request.files.getlist('assignment_files') or []
            if not files_to_save or not (files_to_save[0] and files_to_save[0].filename):
                single = request.files.get('assignment_file')
                if single and single.filename:
                    files_to_save = [single]
            for idx, file in enumerate(files_to_save):
                if not file or not file.filename or not _assistant_allowed_file(file.filename):
                    continue
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                unique_filename = timestamp + f"{idx}_{filename}"
                filepath = os.path.join(upload_dir, unique_filename)
                file.save(filepath)
                attachment_file_path_stored = os.path.join('assignments', unique_filename)
                att = AssignmentAttachment(
                    assignment_id=new_assignment.id,
                    attachment_filename=unique_filename,
                    attachment_original_filename=filename,
                    attachment_file_path=attachment_file_path_stored,
                    attachment_file_size=os.path.getsize(filepath),
                    attachment_mime_type=file.content_type or None,
                    sort_order=idx,
                )
                db.session.add(att)
                if idx == 0:
                    new_assignment.attachment_filename = unique_filename
                    new_assignment.attachment_original_filename = filename
                    new_assignment.attachment_file_path = attachment_file_path_stored
                    new_assignment.attachment_file_size = os.path.getsize(filepath)
                    new_assignment.attachment_mime_type = file.content_type

            db.session.commit()
            _notify_teacher_and_admins(
                class_id,
                'Assignment pending your approval (student assistant)',
                f'{current_user.username} proposed "{title}". Review and approve it before students will see it.',
                link=url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id),
            )
            flash(
                'Your assignment was submitted for approval. It will not appear to students until a teacher or '
                'administrator approves it.',
                'success',
            )
            return redirect(url_for('student_assistant.class_hub', class_id=class_id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f'Assistant add assignment: {e}')
            flash(f'Error creating assignment: {str(e)}', 'danger')
            return redirect(url_for('student_assistant.assistant_add_assignment', class_id=class_id))

    current_quarter = get_current_quarter()
    context = request.args.get('context', 'homework')
    default_due_date = None
    in_class_due_date_str = None
    if context == 'in-class' and ZoneInfo:
        try:
            est = ZoneInfo('America/New_York')
            now_est = datetime.now(est)
            today_est = now_est.date()
            in_class_dt = datetime.combine(today_est, time_cls(16, 0))
            in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
            default_due_date = in_class_dt
        except Exception:
            in_class_dt = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
            in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
            default_due_date = in_class_dt
    elif context == 'in-class':
        in_class_dt = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
        in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
        default_due_date = in_class_dt
    else:
        try:
            est = ZoneInfo('America/New_York')
            now_est = datetime.now(est)
            today_est = now_est.date()
            in_class_dt = datetime.combine(today_est, time_cls(16, 0))
            in_class_due_date_str = in_class_dt.strftime('%Y-%m-%dT%H:%M')
        except Exception:
            in_class_due_date_str = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0).strftime(
                '%Y-%m-%dT%H:%M'
            )

    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    form_action = url_for('student_assistant.assistant_add_assignment', class_id=class_id)
    return render_template(
        'shared/add_assignment.html',
        class_obj=class_obj,
        classes=[class_obj],
        school_years=school_years,
        current_quarter=current_quarter,
        context=context,
        default_due_date=default_due_date,
        in_class_due_date_str=in_class_due_date_str,
        teacher=None,
        student_assistant_mode=True,
        form_action=form_action,
    )


@bp.route('/class/<int:class_id>/group-assignment/create', methods=['GET'])
@login_required
def assistant_create_group_assignment(class_id):
    """Form to propose a group assignment (same as teacher flow; submission goes to assistant save)."""
    class_obj, err = _require_assistant(class_id)
    if err:
        return err

    groups = StudentGroup.query.filter_by(class_id=class_id, is_active=True).all()
    for group in groups:
        members = StudentGroupMember.query.filter_by(group_id=group.id).all()
        group.members_list = [m.student for m in members if m.student]
        group.member_count = len(group.members_list)

    if not groups:
        flash('No groups found for this class. Ask your teacher to create groups first.', 'warning')
        return redirect(url_for('student_assistant.class_hub', class_id=class_id))

    form_action = url_for('student_assistant.assistant_save_group_assignment', class_id=class_id)
    return render_template(
        'teachers/teacher_create_group_assignment.html',
        class_item=class_obj,
        groups=groups,
        student_assistant_mode=True,
        form_action=form_action,
        back_url=url_for('student_assistant.class_hub', class_id=class_id),
    )


@bp.route('/class/<int:class_id>/group-assignment/save', methods=['POST'])
@login_required
def assistant_save_group_assignment(class_id):
    from management_routes.student_assistant_utils import ASSISTANT_APPROVAL_PENDING

    class_obj, err = _require_assistant(class_id)
    if err:
        return err

    try:
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        open_date_str = request.form.get('open_date', '').strip()
        close_date_str = request.form.get('close_date', '').strip()
        quarter = request.form.get('quarter', '').strip()
        assignment_category = request.form.get('assignment_category', '').strip()
        total_points_str = request.form.get('total_points', '100').strip()
        try:
            total_points = float(total_points_str) if total_points_str else 100.0
        except (ValueError, TypeError):
            total_points = 100.0
        category_weight_str = request.form.get('category_weight', '0').strip()
        try:
            category_weight = float(category_weight_str) if category_weight_str else 0.0
        except (ValueError, TypeError):
            category_weight = 0.0

        allow_extra_credit = request.form.get('allow_extra_credit') == 'on'
        max_extra_credit_points_str = request.form.get('max_extra_credit_points', '0').strip()
        try:
            max_extra_credit_points = float(max_extra_credit_points_str) if max_extra_credit_points_str else 0.0
        except (ValueError, TypeError):
            max_extra_credit_points = 0.0

        late_penalty_enabled = request.form.get('late_penalty_enabled') == 'on'
        late_penalty_per_day_str = request.form.get('late_penalty_per_day', '0').strip()
        try:
            late_penalty_per_day = float(late_penalty_per_day_str) if late_penalty_per_day_str else 0.0
        except (ValueError, TypeError):
            late_penalty_per_day = 0.0
        late_penalty_max_days_str = request.form.get('late_penalty_max_days', '0').strip()
        try:
            late_penalty_max_days = int(late_penalty_max_days_str) if late_penalty_max_days_str else 0
        except (ValueError, TypeError):
            late_penalty_max_days = 0

        grade_scale_preset = request.form.get('grade_scale_preset', '').strip()
        grade_scale = None
        if grade_scale_preset == 'standard':
            grade_scale = json.dumps({'A': 90, 'B': 80, 'C': 70, 'D': 60, 'F': 0, 'use_plus_minus': False})
        elif grade_scale_preset == 'strict':
            grade_scale = json.dumps({'A': 93, 'B': 85, 'C': 77, 'D': 70, 'F': 0, 'use_plus_minus': False})
        elif grade_scale_preset == 'lenient':
            grade_scale = json.dumps({'A': 88, 'B': 78, 'C': 68, 'D': 58, 'F': 0, 'use_plus_minus': False})

        selected_groups = request.form.getlist('groups')

        if not title or not due_date_str or not selected_groups or not quarter:
            flash('Title, due date, quarter, and at least one group are required.', 'danger')
            return redirect(url_for('student_assistant.assistant_create_group_assignment', class_id=class_id))

        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        open_date = datetime.strptime(open_date_str, '%Y-%m-%dT%H:%M') if open_date_str else None
        close_date = datetime.strptime(close_date_str, '%Y-%m-%dT%H:%M') if close_date_str else None

        current_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_year:
            flash('No active school year found.', 'danger')
            return redirect(url_for('student_assistant.assistant_create_group_assignment', class_id=class_id))

        assignment_context = request.form.get('assignment_context', 'homework')

        new_assignment = GroupAssignment(
            title=title,
            description=description,
            class_id=class_id,
            due_date=due_date,
            open_date=open_date,
            close_date=close_date,
            quarter=quarter,
            school_year_id=current_year.id,
            assignment_type='pdf',
            assignment_context=assignment_context,
            total_points=total_points,
            assignment_category=assignment_category or None,
            category_weight=category_weight,
            allow_extra_credit=allow_extra_credit,
            max_extra_credit_points=max_extra_credit_points,
            late_penalty_enabled=late_penalty_enabled,
            late_penalty_per_day=late_penalty_per_day,
            late_penalty_max_days=late_penalty_max_days,
            grade_scale=grade_scale,
            selected_group_ids=json.dumps(selected_groups),
            created_by=current_user.id,
            status='Inactive',
            assistant_approval_status=ASSISTANT_APPROVAL_PENDING,
            proposed_by_student_id=current_user.student_id,
        )
        db.session.add(new_assignment)
        db.session.flush()

        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file and file.filename and _assistant_allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                unique_filename = timestamp + filename
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'group_assignments')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, unique_filename)
                file.save(filepath)
                new_assignment.attachment_filename = unique_filename
                new_assignment.attachment_original_filename = filename
                new_assignment.attachment_file_path = filepath
                new_assignment.attachment_file_size = os.path.getsize(filepath)
                new_assignment.attachment_mime_type = file.content_type

        db.session.commit()
        _notify_teacher_and_admins(
            class_id,
            'Group assignment pending your approval (student assistant)',
            f'{current_user.username} proposed group assignment "{title}".',
            link=url_for('teacher.assignments.pending_assistant_assignments', class_id=class_id),
        )
        flash(
            'Your group assignment was submitted for approval. Students will not see it until a teacher or '
            'administrator approves it.',
            'success',
        )
        return redirect(url_for('student_assistant.class_hub', class_id=class_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f'Assistant group assignment: {e}')
        flash(f'Error creating group assignment: {str(e)}', 'danger')
        return redirect(url_for('student_assistant.assistant_create_group_assignment', class_id=class_id))
