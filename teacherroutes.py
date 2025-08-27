from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort
from flask_login import login_required, current_user
from models import db, TeacherStaff, Class, Student, Assignment, Grade, SchoolYear, Submission, Announcement, Notification, Message, MessageGroup, MessageGroupMember, MessageAttachment, ScheduledAnnouncement, Enrollment, Attendance
from decorators import teacher_required
import json
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import time

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

teacher_blueprint = Blueprint('teacher', __name__)

@teacher_blueprint.route('/dashboard')
@login_required
@teacher_required
def teacher_dashboard():
    # Debug logging
    print(f"Teacher dashboard accessed by user: {current_user.username}, role: {current_user.role}, teacher_staff_id: {current_user.teacher_staff_id}")
    
    # Check if teacher_staff_id exists
    if not current_user.teacher_staff_id:
        flash('Teacher profile not found. Please contact administration.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first()
    if not teacher:
        flash('Teacher profile not found. Please contact administration.', 'danger')
        return redirect(url_for('auth.dashboard'))
    # Directors see all classes, teachers only see their assigned classes
    if current_user.role == 'Director':
        classes = Class.query.all()
        class_ids = [c.id for c in classes]
        recent_assignments = Assignment.query.order_by(Assignment.due_date.desc()).limit(5).all()
        assignments = Assignment.query.all()
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in classes]
        recent_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).order_by(Assignment.due_date.desc()).limit(5).all()
        assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
    
    # Get recent grades (simplified)
    recent_grades = []
    for assignment in assignments[:5]:
        grades = Grade.query.filter_by(assignment_id=assignment.id).limit(3).all()
        for grade in grades:
            try:
                grade_data = json.loads(grade.grade_data)
                recent_grades.append({
                    'assignment': assignment,
                    'student': Student.query.get(grade.student_id),
                    'score': grade_data.get('score', 0)
                })
            except (json.JSONDecodeError, TypeError):
                continue
    
    # Get recent activity for the teacher
    recent_activity = []
    
    # Recent submissions
    recent_submissions = Submission.query.join(Assignment).filter(
        Assignment.class_id.in_(class_ids)
    ).order_by(Submission.submitted_at.desc()).limit(5).all()
    
    for submission in recent_submissions:
        recent_activity.append({
            'type': 'submission',
            'title': f'New submission for {submission.assignment.title}',
            'description': f'{submission.student.first_name} {submission.student.last_name} submitted work',
            'timestamp': submission.submitted_at,
            'link': url_for('teacher.grade_assignment', assignment_id=submission.assignment_id)
        })
    
    # Recent grades entered
    recent_grades_entered = Grade.query.join(Assignment).filter(
        Assignment.class_id.in_(class_ids)
    ).order_by(Grade.graded_at.desc()).limit(5).all()
    
    for grade in recent_grades_entered:
        try:
            grade_data = json.loads(grade.grade_data)
            recent_activity.append({
                'type': 'grade',
                'title': f'Grade entered for {grade.assignment.title}',
                'description': f'Graded {grade.student.first_name} {grade.student.last_name} - Score: {grade_data.get("score", "N/A")}',
                'timestamp': grade.graded_at,
                'link': url_for('teacher.grade_assignment', assignment_id=grade.assignment_id)
            })
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Recent assignments created
    for assignment in recent_assignments:
        recent_activity.append({
            'type': 'assignment',
            'title': f'New assignment: {assignment.title}',
            'description': f'Created for {assignment.class_info.name} - Due: {assignment.due_date.strftime("%b %d, %Y")}',
            'timestamp': assignment.created_at,
            'link': url_for('teacher.view_class', class_id=assignment.class_id)
        })
    
    # Sort recent activity by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:10]  # Limit to 10 most recent
    
    # Get notifications for the current user
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.timestamp.desc()).limit(10).all()
    
    # Calculate statistics
    total_students = Student.query.count()  # Simplified - should filter by enrollment
    active_assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).count()
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher, 
                         classes=classes,
                         recent_assignments=recent_assignments,
                         recent_grades=recent_grades,
                         recent_activity=recent_activity,
                         notifications=notifications,
                         total_students=total_students,
                         active_assignments=active_assignments,
                         section='home',
                         active_tab='home')

@teacher_blueprint.route('/class/<int:class_id>')
@login_required
@teacher_required
def view_class(class_id):
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    class_obj = Class.query.get_or_404(class_id)
    
    # Directors have access to all classes, teachers only to their assigned classes
    if current_user.role != 'Director' and class_obj.teacher_id != teacher.id:
        return redirect(url_for('teacher.teacher_dashboard'))

    # Get only actively enrolled students for this class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    enrolled_students = [enrollment.student for enrollment in enrollments]
    
    # Debug logging
    print(f"DEBUG: Class ID: {class_id}")
    print(f"DEBUG: Found {len(enrollments)} enrollments")
    print(f"DEBUG: Enrolled students: {[f'{s.first_name} {s.last_name}' for s in enrolled_students]}")

    # Get recent assignments for this class
    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).limit(5).all()

    # Get recent attendance records for this class (last 7 days)
    from datetime import datetime, timedelta
    recent_attendance = Attendance.query.filter(
        Attendance.class_id == class_id,
        Attendance.date >= datetime.now().date() - timedelta(days=7)
    ).order_by(Attendance.date.desc()).all()

    # Get recent announcements for this class
    announcements = Announcement.query.filter_by(class_id=class_id).order_by(Announcement.timestamp.desc()).limit(5).all()

    return render_template(
        'teacher_class_roster_view.html',
        class_item=class_obj,
        enrolled_students=enrolled_students,
        assignments=assignments,
        recent_attendance=recent_attendance,
        announcements=announcements
    )

@teacher_blueprint.route('/class/<int:class_id>/assignment/add', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_assignment(class_id):
    class_obj = Class.query.get_or_404(class_id)
    # Authorization check - Directors can add assignments to any class
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    if current_user.role != 'Director' and class_obj.teacher_id != teacher.id:
        flash("You are not authorized to add assignments to this class.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, due_date_str, quarter]):
            flash("Title, Due Date, and Quarter are required.", "danger")
            return redirect(request.url)

        # Type assertion for due_date_str
        assert due_date_str is not None
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        
        current_school_year = SchoolYear.query.filter_by(is_active=True).first()
        if not current_school_year:
            flash("Cannot create assignment: No active school year.", "danger")
            return redirect(url_for('teacher.view_class', class_id=class_id))

        # Type assertion for quarter
        assert quarter is not None
        
        # Create assignment using attribute assignment
        new_assignment = Assignment()
        new_assignment.title = title
        new_assignment.description = description
        new_assignment.due_date = due_date
        new_assignment.class_id = class_id
        new_assignment.school_year_id = current_school_year.id
        new_assignment.quarter = int(quarter)
        
        # Handle file upload
        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Type assertion for filename
                    assert file.filename is not None
                    filename = secure_filename(file.filename)
                    # Create a unique filename to avoid collisions
                    unique_filename = f"assignment_{class_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    try:
                        file.save(filepath)
                        
                        # Save file information to assignment
                        new_assignment.attachment_filename = unique_filename
                        new_assignment.attachment_original_filename = filename
                        new_assignment.attachment_file_path = filepath
                        new_assignment.attachment_file_size = os.path.getsize(filepath)
                        new_assignment.attachment_mime_type = file.content_type
                        
                    except Exception as e:
                        flash(f'Error saving file: {str(e)}', 'danger')
                        return redirect(request.url)
                else:
                    flash(f'File type not allowed. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
                    return redirect(request.url)
        
        db.session.add(new_assignment)
        db.session.commit()
        
        # Create notifications for students in this class
        from app import create_notification_for_students_in_class
        create_notification_for_students_in_class(
            class_id=class_id,
            notification_type='assignment',
            title=f'New Assignment: {title}',
            message=f'A new assignment "{title}" has been created for {class_obj.name}. Due date: {due_date.strftime("%b %d, %Y")}',
            link=url_for('student.student_assignments')
        )
        
        flash('Assignment created successfully.', 'success')
        return redirect(url_for('teacher.view_class', class_id=class_id))

    return render_template('add_assignment.html', class_obj=class_obj)


@teacher_blueprint.route('/assignment/view/<int:assignment_id>')
@login_required
@teacher_required
def view_assignment(assignment_id):
    """View assignment details"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Get class information
    class_info = Class.query.get(assignment.class_id) if assignment.class_id else None
    teacher = None
    if class_info and class_info.teacher_id:
        teacher = TeacherStaff.query.get(class_info.teacher_id)
    
    # Authorization check - Directors can view any assignment, teachers can only view their own
    current_teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    if current_user.role != 'Director' and class_info.teacher_id != current_teacher.id:
        flash("You are not authorized to view this assignment.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Get submissions count (if any)
    submissions_count = 0  # This would be implemented when submission system is added
    
    # Get current date for status calculations
    today = datetime.now().date()
    
    return render_template('view_assignment.html', 
                         assignment=assignment,
                         class_info=class_info,
                         teacher=teacher,
                         submissions_count=submissions_count,
                         today=today)


@teacher_blueprint.route('/assignment/edit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_assignment(assignment_id):
    """Edit an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Authorization check - Directors can edit any assignment, teachers can only edit their own
    current_teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    if current_user.role != 'Director' and class_obj.teacher_id != current_teacher.id:
        flash("You are not authorized to edit this assignment.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        quarter = request.form.get('quarter')
        
        if not all([title, due_date_str, quarter]):
            flash('Title, Due Date, and Quarter are required.', 'danger')
            return redirect(request.url)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
            # Update assignment
            assignment.title = title
            assignment.description = description
            assignment.due_date = due_date
            assignment.quarter = int(quarter)
            
            # Handle file upload
            if 'assignment_file' in request.files:
                file = request.files['assignment_file']
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"assignment_{assignment.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        try:
                            file.save(filepath)
                            
                            # Update file information
                            assignment.attachment_filename = unique_filename
                            assignment.attachment_original_filename = filename
                        except Exception as e:
                            flash(f'Error saving file: {str(e)}', 'danger')
                            return redirect(request.url)
            
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('teacher.view_class', class_id=class_obj.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating assignment: {str(e)}', 'danger')
            return redirect(request.url)
    
    # For GET request, get all classes for the dropdown
    classes = Class.query.all()
    school_years = SchoolYear.query.all()
    
    return render_template('edit_assignment.html', 
                         assignment=assignment,
                         classes=classes,
                         school_years=school_years)


@teacher_blueprint.route('/assignment/remove/<int:assignment_id>', methods=['POST'])
@login_required
@teacher_required
def remove_assignment(assignment_id):
    """Remove an assignment"""
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Authorization check - Directors can remove any assignment, teachers can only remove their own
    current_teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    if current_user.role != 'Director' and class_obj.teacher_id != current_teacher.id:
        flash("You are not authorized to remove this assignment.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    try:
        # Delete associated file if it exists
        if assignment.attachment_filename:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], assignment.attachment_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Delete the assignment
        db.session.delete(assignment)
        db.session.commit()
        
        flash('Assignment removed successfully.', 'success')
        return redirect(url_for('teacher.view_class', class_id=class_obj.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing assignment: {str(e)}', 'danger')
        return redirect(url_for('teacher.view_class', class_id=class_obj.id))


@teacher_blueprint.route('/grade/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_info
    
    # Authorization check - Directors can grade any assignment
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    if current_user.role != 'Director' and class_obj.teacher_id != teacher.id:
        flash("You are not authorized to grade this assignment.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))

    # Get only students enrolled in this specific class
    enrolled_students = db.session.query(Student).join(Enrollment).filter(
        Enrollment.class_id == class_obj.id,
        Enrollment.is_active == True
    ).order_by(Student.last_name, Student.first_name).all()
    
    if not enrolled_students:
        flash("No students are currently enrolled in this class.", "warning")
        return redirect(url_for('teacher.view_class', class_id=class_obj.id))
    
    students = enrolled_students
    
    if request.method == 'POST':
        for student in students:
            score = request.form.get(f'score_{student.id}')
            comment = request.form.get(f'comment_{student.id}')
            
            if score is not None:
                try:
                    score_val = float(score) if score else 0.0
                    grade_data = json.dumps({'score': score_val, 'comment': comment})
                    
                    grade = Grade.query.filter_by(student_id=student.id, assignment_id=assignment_id).first()
                    if grade:
                        grade.grade_data = grade_data
                    else:
                        # Create grade using attribute assignment
                        grade = Grade()
                        grade.student_id = student.id
                        grade.assignment_id = assignment_id
                        grade.grade_data = grade_data
                        db.session.add(grade)
                    
                    # Create notification for the student
                    if student.user:
                        from app import create_notification
                        create_notification(
                            user_id=student.user.id,
                            notification_type='grade',
                            title=f'Grade posted for {assignment.title}',
                            message=f'Your grade for "{assignment.title}" has been posted. Score: {score_val}%',
                            link=url_for('student.student_grades')
                        )
                        
                except ValueError:
                    flash(f"Invalid score format for student {student.id}.", "warning")
                    continue # Skip this student and continue with others
        
        db.session.commit()
        flash('Grades updated successfully.', 'success')
        return redirect(url_for('teacher.grade_assignment', assignment_id=assignment_id))

    # Get existing grades for this assignment
    grades = {g.student_id: json.loads(g.grade_data) for g in Grade.query.filter_by(assignment_id=assignment_id).all()}
    submissions = {s.student_id: s for s in Submission.query.filter_by(assignment_id=assignment_id).all()}
    
    return render_template('teacher_grade_assignment.html', 
                         assignment=assignment, 
                         class_obj=class_obj,
                         students=students, 
                         grades=grades, 
                         submissions=submissions)


@teacher_blueprint.route('/attendance/take/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def take_attendance(class_id):
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if class is active (has an active school year)
    if not hasattr(class_obj, 'school_year_id') or not class_obj.school_year_id:
        flash("This class is not associated with an active school year.", "warning")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    # Check if class is archived or inactive
    if hasattr(class_obj, 'is_active') and not class_obj.is_active:
        flash("This class is archived or inactive. Cannot take attendance.", "warning")
        return redirect(url_for('teacher.teacher_dashboard'))
    
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    # Directors can take attendance for any class
    if current_user.role != 'Director' and class_obj.teacher_id != teacher.id:
        flash("You are not authorized to take attendance for this class.", "danger")
        return redirect(url_for('teacher.teacher_dashboard'))

    # Get only students enrolled in this specific class
    enrolled_students = db.session.query(Student).join(Enrollment).filter(
        Enrollment.class_id == class_id,
        Enrollment.is_active == True
    ).order_by(Student.last_name, Student.first_name).all()
    
    if not enrolled_students:
        flash("No students are currently enrolled in this class.", "warning")
        return redirect(url_for('teacher.view_class', class_id=class_id))
    
    students = enrolled_students
    
    # Additional validation - ensure class has active enrollment
    active_enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).count()
    if active_enrollments == 0:
        flash("This class has no active enrollments. Cannot take attendance.", "warning")
        return redirect(url_for('teacher.view_class', class_id=class_id))
    statuses = [
        "Present",
        "Late",
        "Unexcused Absence",
        "Excused Absence",
        "Suspended"
    ]

    attendance_date_str = request.args.get('date') or request.form.get('attendance_date')
    if not attendance_date_str:
        attendance_date_str = datetime.now().strftime('%Y-%m-%d')
    
    try:
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD format.", "danger")
        return redirect(url_for('teacher.take_attendance', class_id=class_id))
    
    # Check if date is not in the future
    if attendance_date > datetime.now().date():
        flash("Cannot take attendance for future dates.", "warning")
        attendance_date_str = datetime.now().strftime('%Y-%m-%d')
        attendance_date = datetime.now().date()

    # Load existing records for this class/date
    existing_records = {rec.student_id: rec for rec in Attendance.query.filter_by(class_id=class_id, date=attendance_date).all()}
    
    # Calculate attendance statistics
    total_students = len(students)
    present_count = sum(1 for record in existing_records.values() if record.status == "Present")
    late_count = sum(1 for record in existing_records.values() if record.status == "Late")
    absent_count = sum(1 for record in existing_records.values() if record.status in ["Unexcused Absence", "Excused Absence"])
    suspended_count = sum(1 for record in existing_records.values() if record.status == "Suspended")
    
    attendance_stats = {
        'total': total_students,
        'present': present_count,
        'late': late_count,
        'absent': absent_count,
        'suspended': suspended_count,
        'present_percentage': round((present_count / total_students * 100) if total_students > 0 else 0, 1)
    }

    if request.method == 'POST':
        attendance_saved = False
        valid_statuses = ["Present", "Late", "Unexcused Absence", "Excused Absence", "Suspended"]
        
        for student in students:
            status = request.form.get(f'status-{student.id}')
            notes = request.form.get(f'notes-{student.id}')
            
            if not status:
                continue
                
            # Validate status
            if status not in valid_statuses:
                flash(f"Invalid attendance status for {student.first_name} {student.last_name}.", "warning")
                continue
            
            # Validate that the student is still enrolled in this class
            enrollment = Enrollment.query.filter_by(
                student_id=student.id, 
                class_id=class_id, 
                is_active=True
            ).first()
            
            if not enrollment:
                flash(f'Student {student.first_name} {student.last_name} is no longer enrolled in this class.', 'warning')
                continue
            
            # Check if record exists
            record = Attendance.query.filter_by(student_id=student.id, class_id=class_id, date=attendance_date).first()
            if record:
                record.status = status
                record.notes = notes
                record.teacher_id = teacher.id
            else:
                record = Attendance(
                    student_id=student.id,
                    class_id=class_id,
                    date=attendance_date,
                    status=status,
                    notes=notes,
                    teacher_id=teacher.id
                )
                db.session.add(record)
            attendance_saved = True
            
            # Check for duplicate records (safety check)
            duplicate_count = Attendance.query.filter_by(
                student_id=student.id, 
                class_id=class_id, 
                date=attendance_date
            ).count()
            
            if duplicate_count > 1:
                flash(f"Warning: Multiple attendance records found for {student.first_name} {student.last_name} on {attendance_date_str}. Please contact administration.", "warning")
        
        if attendance_saved:
            try:
                db.session.commit()
                flash('Attendance recorded successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Error saving attendance. Please try again.', 'danger')
                print(f"Error saving attendance: {e}")
        else:
            flash('No attendance data was submitted.', 'warning')
        
        return redirect(url_for('teacher.view_class', class_id=class_id))

    return render_template(
        'take_attendance.html',
        class_item=class_obj,
        students=students,
        attendance_date_str=attendance_date_str,
        statuses=statuses,
        existing_records=existing_records,
        attendance_stats=attendance_stats
    )

@teacher_blueprint.route('/classes')
@login_required
@teacher_required
def my_classes():
    """View all classes taught by the teacher, or all classes for Directors"""
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    
    # Directors see all classes, teachers only see their assigned classes
    if current_user.role == 'Director':
        classes = Class.query.all()
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher, 
                         classes=classes,
                         section='classes',
                         active_tab='classes')

@teacher_blueprint.route('/assignments')
@login_required
@teacher_required
def my_assignments():
    """View all assignments created by the teacher, or all assignments for Directors"""
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    
    # Directors see all classes and assignments, teachers only see their assigned ones
    if current_user.role == 'Director':
        classes = Class.query.all()
        assignments = Assignment.query.order_by(Assignment.due_date.desc()).all()
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in classes]
        assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).order_by(Assignment.due_date.desc()).all()
    
    from datetime import datetime
    return render_template('role_teacher_dashboard.html',
                         teacher=teacher,
                         classes=classes,
                         assignments=assignments,
                         today=datetime.now(),
                         section='assignments',
                         active_tab='assignments',
                         now=datetime.now())

@teacher_blueprint.route('/grades')
@login_required
@teacher_required
def my_grades():
    """View all grades entered by the teacher, or all grades for Directors"""
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    
    # Directors see all classes, assignments, and grades, teachers only see their assigned ones
    if current_user.role == 'Director':
        classes = Class.query.all()
        assignments = Assignment.query.all()
        grades = Grade.query.all()
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
        class_ids = [c.id for c in classes]
        assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
        assignment_ids = [a.id for a in assignments]
        grades = Grade.query.filter(Grade.assignment_id.in_(assignment_ids)).all()
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher,
                         classes=classes,
                         assignments=assignments,
                         grades=grades,
                         section='grades',
                         active_tab='grades')


@teacher_blueprint.route('/student-grades')
@login_required
@teacher_required
def student_grades():
    """View detailed student grades for teacher's classes"""
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    
    # Get the class filter if provided
    class_filter = request.args.get('class_id', type=int)
    student_filter = request.args.get('student_id', type=int)
    
    # Directors see all classes, teachers only see their assigned ones
    if current_user.role == 'Director':
        classes = Class.query.all()
        if class_filter:
            classes = [c for c in classes if c.id == class_filter]
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
        if class_filter:
            classes = [c for c in classes if c.id == class_filter]
    
    # Get all students enrolled in these classes
    class_ids = [c.id for c in classes]
    enrollments = Enrollment.query.filter(
        Enrollment.class_id.in_(class_ids),
        Enrollment.is_active == True
    ).all()
    
    # Group students by class
    students_by_class = {}
    for enrollment in enrollments:
        class_id = enrollment.class_id
        if class_id not in students_by_class:
            students_by_class[class_id] = []
        students_by_class[class_id].append(enrollment.student)
    
    # Get assignments and grades for these classes
    assignments = Assignment.query.filter(Assignment.class_id.in_(class_ids)).all()
    assignment_ids = [a.id for a in assignments]
    
    # Get all grades for these assignments
    all_grades = Grade.query.filter(Grade.assignment_id.in_(assignment_ids)).all()
    
    # Organize grades by student and assignment
    grades_by_student = {}
    for grade in all_grades:
        student_id = grade.student_id
        assignment_id = grade.assignment_id
        
        if student_id not in grades_by_student:
            grades_by_student[student_id] = {}
        
        grade_data = json.loads(grade.grade_data)
        grades_by_student[student_id][assignment_id] = {
            'score': grade_data.get('score', 0),
            'feedback': grade_data.get('feedback', ''),
            'graded_at': grade.graded_at,
            'assignment': grade.assignment
        }
    
    # Calculate GPA for each student
    student_gpas = {}
    for student_id, student_grades in grades_by_student.items():
        scores = [grade_info['score'] for grade_info in student_grades.values() if 'score' in grade_info]
        if scores:
            # Convert percentage to GPA (90-100 = 4.0, 80-89 = 3.0, etc.)
            gpa_scores = []
            for score in scores:
                if score >= 90:
                    gpa_scores.append(4.0)
                elif score >= 80:
                    gpa_scores.append(3.0)
                elif score >= 70:
                    gpa_scores.append(2.0)
                elif score >= 60:
                    gpa_scores.append(1.0)
                else:
                    gpa_scores.append(0.0)
            
            student_gpas[student_id] = sum(gpa_scores) / len(gpa_scores)
        else:
            student_gpas[student_id] = 0.0
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher,
                         classes=classes,
                         assignments=assignments,
                         students_by_class=students_by_class,
                         grades_by_student=grades_by_student,
                         student_gpas=student_gpas,
                         class_filter=class_filter,
                         student_filter=student_filter,
                         section='student-grades',
                         active_tab='student-grades')

@teacher_blueprint.route('/attendance')
@login_required
@teacher_required
def attendance():
    """View attendance for teacher's classes, or all classes for Directors"""
    teacher = TeacherStaff.query.filter_by(id=current_user.teacher_staff_id).first_or_404()
    
    # Get all classes with student counts
    all_classes = Class.query.all()
    
    # For each class, get the enrolled student count
    for class_obj in all_classes:
        # Count active enrollments for this class
        student_count = db.session.query(Enrollment).filter_by(
            class_id=class_obj.id, 
            is_active=True
        ).count()
        class_obj.enrolled_student_count = student_count
    
    # Directors see all classes, teachers only see their assigned classes
    if current_user.role == 'Director':
        classes = all_classes
    else:
        classes = [c for c in all_classes if c.teacher_id == teacher.id]
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=teacher,
                         classes=classes,
                         all_classes=all_classes,  # Pass all classes for comparison
                         section='attendance',
                         active_tab='attendance')

@teacher_blueprint.route('/students')
@login_required
@teacher_required
def students_directory():
    """View students directory with search functionality"""
    search_query = request.args.get('search', '').strip()
    
    # Build the query
    query = Student.query
    
    # Apply search filter if query exists
    if search_query:
        search_filter = db.or_(
            Student.first_name.ilike(f'%{search_query}%'),
            Student.last_name.ilike(f'%{search_query}%'),
            Student.email.ilike(f'%{search_query}%'),
            Student.student_id.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)
    
    # Order by last name, then first name
    students = query.order_by(Student.last_name, Student.first_name).all()
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=current_user,
                         students=students,
                         search_query=search_query,
                         section='students',
                         active_tab='students')

@teacher_blueprint.route('/teachers-staff')
@login_required
@teacher_required
def teachers_staff_directory():
    """View teachers and staff directory with search functionality"""
    search_query = request.args.get('search', '').strip()
    
    # Build the query
    query = TeacherStaff.query
    
    # Apply search filter if query exists
    if search_query:
        search_filter = db.or_(
            TeacherStaff.first_name.ilike(f'%{search_query}%'),
            TeacherStaff.last_name.ilike(f'%{search_query}%'),
            TeacherStaff.email.ilike(f'%{search_query}%'),
            TeacherStaff.assigned_role.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)
    
    # Order by last name, then first name
    teachers_staff = query.order_by(TeacherStaff.last_name, TeacherStaff.first_name).all()
    
    return render_template('role_teacher_dashboard.html', 
                         teacher=current_user,
                         teachers_staff=teachers_staff,
                         search_query=search_query,
                         section='teachers-staff',
                         active_tab='teachers-staff')

@teacher_blueprint.route('/calendar')
@login_required
@teacher_required
def calendar():
    """View school calendar"""
    from datetime import datetime, timedelta, date
    import calendar as cal
    import holidays as pyholidays
    
    # Import all required models at the top of the function
    from models import AcademicPeriod, CalendarEvent

    def get_religious_holidays(year):
        jewish = [
            (date(year, 4, 23), "Passover (Pesach)"),
            (date(year, 9, 16), "Rosh Hashanah"),
            (date(year, 9, 25), "Yom Kippur"),
            (date(year, 9, 30), "Sukkot"),
            (date(year, 12, 25), "Hanukkah (start)")
        ]
        christian = [
            (date(year, 12, 25), "Christmas"),
            (date(year, 4, 20), "Easter"),
            (date(year, 12, 24), "Christmas Eve"),
            (date(year, 1, 6), "Epiphany"),
            (date(year, 4, 18), "Good Friday")
        ]
        muslim = [
            (date(year, 3, 10), "Ramadan Begins"),
            (date(year, 4, 9), "Eid al-Fitr"),
            (date(year, 6, 16), "Eid al-Adha")
        ]
        return jewish + christian + muslim

    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    current_date = datetime(year, month, 1)
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)
    cal_obj = cal.monthcalendar(year, month)
    month_name = datetime(year, month, 1).strftime('%B')

    # Get academic dates from the database
    academic_dates = []
    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if active_year:
        # Get academic periods for this month
        start_of_month = date(year, month, 1)
        if month == 12:
            end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get academic periods that overlap with this month
        academic_periods = AcademicPeriod.query.filter(
            AcademicPeriod.school_year_id == active_year.id,
            AcademicPeriod.start_date <= end_of_month,
            AcademicPeriod.end_date >= start_of_month
        ).all()
        
        for period in academic_periods:
            # Add start date event
            if period.start_date.month == month:
                academic_dates.append((period.start_date.day, f"{period.name} Start", 'Academic Period'))
            
            # Add end date event
            if period.end_date.month == month:
                academic_dates.append((period.end_date.day, f"{period.name} End", 'Academic Period'))
        
        # Get calendar events for this month
        calendar_events = CalendarEvent.query.filter(
            CalendarEvent.school_year_id == active_year.id,
            CalendarEvent.start_date <= end_of_month,
            CalendarEvent.end_date >= start_of_month
        ).all()
        
        for event in calendar_events:
            if event.start_date.month == month:
                academic_dates.append((event.start_date.day, event.name, event.event_type.replace('_', ' ').title()))
    
    us_holidays = pyholidays.country_holidays('US', years=[year])
    religious_holidays = get_religious_holidays(year)
    holidays_this_month = []
    
    # Add religious holidays
    for hol_date, hol_name in religious_holidays:
        if hol_date.month == month:
            holidays_this_month.append((hol_date.day, hol_name))
    
    # Add US Federal holidays with "No School" for weekdays during school year
    school_year_start = date(year, 8, 1)  # August 1st
    school_year_end = date(year, 6, 30)   # June 30th
    
    for hol_date, hol_name in us_holidays.items():
        if hol_date.month == month:
            # Check if it's a weekday (Monday=0, Sunday=6)
            is_weekday = hol_date.weekday() < 5
            # Check if it's during school year
            is_school_year = (hol_date >= school_year_start and hol_date <= school_year_end) or \
                           (hol_date >= date(year-1, 8, 1) and hol_date <= date(year, 6, 30))
            
            if is_weekday and is_school_year:
                holidays_this_month.append((hol_date.day, f"{hol_name} - No School"))
            else:
                holidays_this_month.append((hol_date.day, hol_name))

    calendar_data = {
        'month_name': month_name,
        'year': year,
        'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'weeks': []
    }
    for week in cal_obj:
        week_data = []
        for day in week:
            events = []
            if day != 0:
                # Add academic dates
                for acad_day, acad_name, acad_category in academic_dates:
                    if day == acad_day:
                        events.append({'title': acad_name, 'category': acad_category})
                
                # Add holidays
                for hol_day, hol_name in holidays_this_month:
                    if day == hol_day:
                        events.append({'title': hol_name, 'category': 'Holiday'})
            if day == 0:
                week_data.append({'day_num': '', 'is_current_month': False, 'is_today': False, 'events': []})
            else:
                is_today = (day == datetime.now().day and month == datetime.now().month and year == datetime.now().year)
                week_data.append({'day_num': day, 'is_current_month': True, 'is_today': is_today, 'events': events})
        calendar_data['weeks'].append(week_data)

    return render_template('role_teacher_dashboard.html',
                         teacher=current_user,
                         calendar_data=calendar_data,
                         month_name=month_name,
                         year=year,
                         prev_month=prev_month,
                         next_month=next_month,
                         section='calendar',
                         active_tab='calendar')

# Enhanced Communications Routes
@teacher_blueprint.route('/communications')
@login_required
@teacher_required
def teacher_communications():
    """Communications tab - Under Development."""
    return render_template('under_development.html',
                         section='communications',
                         active_tab='communications')


@teacher_blueprint.route('/messages')
@login_required
@teacher_required
def teacher_messages():
    """View all messages with filtering and sorting."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    
    # Get filter parameters
    message_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'date')
    
    # Build query
    query = Message.query.filter(
        (Message.recipient_id == current_user.id) |
        (Message.sender_id == current_user.id)
    )
    
    # Apply filters
    if message_type != 'all':
        query = query.filter(Message.message_type == message_type)
    
    if status == 'unread':
        query = query.filter(Message.is_read == False)
    elif status == 'read':
        query = query.filter(Message.is_read == True)
    
    # Apply sorting
    if sort_by == 'date':
        query = query.order_by(Message.created_at.desc())
    elif sort_by == 'sender':
        query = query.order_by(Message.sender_id)
    elif sort_by == 'subject':
        query = query.order_by(Message.subject)
    
    messages = query.all()
    
    return render_template('teacher_messages.html',
                         teacher=teacher,
                         messages=messages,
                         message_type=message_type,
                         status=status,
                         sort_by=sort_by,
                         section='communications',
                         active_tab='messages')


@teacher_blueprint.route('/messages/send', methods=['GET', 'POST'])
@login_required
@teacher_required
def send_message():
    """Send a new message."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id', type=int)
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        message_type = request.form.get('message_type', 'direct')
        group_id = request.form.get('group_id', type=int)
        
        if not content:
            flash('Message content is required.', 'error')
            return redirect(url_for('teacher.send_message'))
        
        # Create message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id if message_type == 'direct' else None,
            subject=subject,
            content=content,
            message_type=message_type,
            group_id=group_id if message_type == 'group' else None
        )
        
        db.session.add(message)
        
        # Handle file attachments
        if 'attachments' in request.files:
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"msg_{message.id}_{int(time.time())}_{filename}"
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        try:
                            file.save(filepath)
                            attachment = MessageAttachment(
                                message_id=message.id,
                                filename=unique_filename,
                                original_filename=filename,
                                file_path=filepath,
                                file_size=os.path.getsize(filepath),
                                mime_type=file.content_type
                            )
                            db.session.add(attachment)
                        except Exception as e:
                            current_app.logger.error(f"File upload failed: {e}")
        
        db.session.commit()
        
        # Create notification for recipient
        if message_type == 'direct' and recipient_id:
            notification = Notification(
                user_id=recipient_id,
                type='message',
                title=f'New message from {teacher.first_name} {teacher.last_name}',
                message=content[:100] + '...' if len(content) > 100 else content,
                message_id=message.id
            )
            db.session.add(notification)
            db.session.commit()
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('teacher.teacher_messages'))
    
    # Get potential recipients
    students = Student.query.all()
    teachers = TeacherStaff.query.all()
    groups = MessageGroup.query.filter_by(is_active=True).all()
    
    return render_template('teacher_send_message.html',
                         teacher=teacher,
                         students=students,
                         teachers=teachers,
                         groups=groups,
                         section='communications',
                         active_tab='messages')


@teacher_blueprint.route('/messages/<int:message_id>')
@login_required
@teacher_required
def view_message(message_id):
    """View a specific message."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    message = Message.query.get_or_404(message_id)
    
    # Check if user has access to this message
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        abort(403)
    
    # Mark as read if user is recipient
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('teacher_view_message.html',
                         teacher=teacher,
                         message=message,
                         section='communications',
                         active_tab='messages')


@teacher_blueprint.route('/messages/<int:message_id>/reply', methods=['POST'])
@login_required
@teacher_required
def reply_to_message(message_id):
    """Reply to a message."""
    original_message = Message.query.get_or_404(message_id)
    
    # Check if user has access to this message
    if original_message.recipient_id != current_user.id and original_message.sender_id != current_user.id:
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Reply content is required.', 'error')
        return redirect(url_for('teacher.view_message', message_id=message_id))
    
    # Determine recipient
    if original_message.sender_id == current_user.id:
        recipient_id = original_message.recipient_id
    else:
        recipient_id = original_message.sender_id
    
    # Create reply
    reply = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        subject=f"Re: {original_message.subject}" if original_message.subject else "Re: Message",
        content=content,
        message_type='direct'
    )
    
    db.session.add(reply)
    db.session.commit()
    
    # Create notification
    notification = Notification(
        user_id=recipient_id,
        type='message',
        title=f'Reply from {current_user.username}',
        message=content[:100] + '...' if len(content) > 100 else content,
        message_id=reply.id
    )
    db.session.add(notification)
    db.session.commit()
    
    flash('Reply sent successfully!', 'success')
    return redirect(url_for('teacher.view_message', message_id=message_id))


@teacher_blueprint.route('/groups')
@login_required
@teacher_required
def teacher_groups():
    """Manage message groups."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    
    # Get groups the teacher is part of
    group_memberships = MessageGroupMember.query.filter_by(user_id=current_user.id).all()
    groups = [membership.group for membership in group_memberships if membership.group.is_active]
    
    # Get teacher's classes for creating new groups
    classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    return render_template('teacher_groups.html',
                         teacher=teacher,
                         groups=groups,
                         classes=classes,
                         section='communications',
                         active_tab='groups')


@teacher_blueprint.route('/groups/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_group():
    """Create a new message group."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        group_type = request.form.get('group_type', 'class')
        class_id = request.form.get('class_id', type=int)
        
        if not name:
            flash('Group name is required.', 'error')
            return redirect(url_for('teacher.create_group'))
        
        # Create group
        group = MessageGroup(
            name=name,
            description=description,
            group_type=group_type,
            class_id=class_id,
            created_by=current_user.id
        )
        
        db.session.add(group)
        db.session.flush()  # Get the group ID
        
        # Add creator as admin member
        member = MessageGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.session.add(member)
        
        # Add class members if it's a class group
        if class_id and group_type == 'class':
            class_obj = Class.query.get(class_id)
            if class_obj:
                # Add teacher
                if class_obj.teacher and class_obj.teacher.user:
                    member = MessageGroupMember(
                        group_id=group.id,
                        user_id=class_obj.teacher.user.id,
                        is_admin=True
                    )
                    db.session.add(member)
                
                # Add only students enrolled in this specific class
                enrolled_students = db.session.query(Student).join(Enrollment).filter(
                    Enrollment.class_id == class_id,
                    Enrollment.is_active == True
                ).order_by(Student.last_name, Student.first_name).all()
                
                for student in enrolled_students:
                    if student.user:
                        member = MessageGroupMember(
                            group_id=group.id,
                            user_id=student.user.id,
                            is_admin=False
                        )
                        db.session.add(member)
        
        db.session.commit()
        flash('Group created successfully!', 'success')
        return redirect(url_for('teacher.teacher_groups'))
    
    # Directors can create groups for any class
    if current_user.role == 'Director':
        classes = Class.query.all()
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    return render_template('teacher_create_group.html',
                         teacher=teacher,
                         classes=classes,
                         section='communications',
                         active_tab='groups')


@teacher_blueprint.route('/groups/<int:group_id>')
@login_required
@teacher_required
def view_group(group_id):
    """View a message group and its messages."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    group = MessageGroup.query.get_or_404(group_id)
    
    # Check if user is member of this group
    membership = MessageGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        abort(403)
    
    # Get group messages
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.created_at.desc()).all()
    
    # Get group members
    members = MessageGroupMember.query.filter_by(group_id=group_id).all()
    
    return render_template('teacher_view_group.html',
                         teacher=teacher,
                         group=group,
                         messages=messages,
                         members=members,
                         membership=membership,
                         section='communications',
                         active_tab='groups')


@teacher_blueprint.route('/groups/<int:group_id>/send', methods=['POST'])
@login_required
@teacher_required
def send_group_message(group_id):
    """Send a message to a group."""
    group = MessageGroup.query.get_or_404(group_id)
    
    # Check if user is member of this group
    membership = MessageGroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id
    ).first()
    
    if not membership:
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Message content is required.', 'error')
        return redirect(url_for('teacher.view_group', group_id=group_id))
    
    # Create group message
    message = Message(
        sender_id=current_user.id,
        content=content,
        message_type='group',
        group_id=group_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Create notifications for all group members except sender
    members = MessageGroupMember.query.filter_by(group_id=group_id).all()
    for member in members:
        if member.user_id != current_user.id and not member.is_muted:
            notification = Notification(
                user_id=member.user_id,
                type='group_message',
                title=f'New message in {group.name}',
                message=content[:100] + '...' if len(content) > 100 else content,
                message_id=message.id
            )
            db.session.add(notification)
    
    db.session.commit()
    
    flash('Message sent to group!', 'success')
    return redirect(url_for('teacher.view_group', group_id=group_id))


@teacher_blueprint.route('/announcements/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_announcement():
    """Create a new announcement."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        is_important = request.form.get('is_important', type=bool)
        requires_confirmation = request.form.get('requires_confirmation', type=bool)
        rich_content = request.form.get('rich_content', '')
        
        if not title or not message:
            flash('Title and message are required.', 'error')
            return redirect(url_for('teacher.create_announcement'))
        
        # Create announcement
        announcement = Announcement(
            title=title,
            message=message,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id,
            is_important=is_important,
            requires_confirmation=requires_confirmation,
            rich_content=rich_content
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement created successfully!', 'success')
        return redirect(url_for('teacher.teacher_communications'))
    
    # Directors can create announcements for any class
    if current_user.role == 'Director':
        classes = Class.query.all()
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    return render_template('teacher_create_announcement.html',
                         teacher=teacher,
                         classes=classes,
                         section='communications',
                         active_tab='announcements')


@teacher_blueprint.route('/announcements/schedule', methods=['GET', 'POST'])
@login_required
@teacher_required
def schedule_announcement():
    """Schedule an announcement for future delivery."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_group = request.form.get('target_group', 'all_students')
        class_id = request.form.get('class_id', type=int)
        scheduled_for = request.form.get('scheduled_for')
        
        if not title or not message or not scheduled_for:
            flash('Title, message, and scheduled time are required.', 'error')
            return redirect(url_for('teacher.schedule_announcement'))
        
        try:
            scheduled_datetime = datetime.strptime(scheduled_for, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'error')
            return redirect(url_for('teacher.schedule_announcement'))
        
        # Create scheduled announcement
        scheduled = ScheduledAnnouncement(
            title=title,
            message=message,
            sender_id=current_user.id,
            target_group=target_group,
            class_id=class_id,
            scheduled_for=scheduled_datetime
        )
        
        db.session.add(scheduled)
        db.session.commit()
        
        flash('Announcement scheduled successfully!', 'success')
        return redirect(url_for('teacher.teacher_communications'))
    
    # Directors can schedule announcements for any class
    if current_user.role == 'Director':
        classes = Class.query.all()
    else:
        classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    return render_template('teacher_schedule_announcement.html',
                         teacher=teacher,
                         classes=classes,
                         section='communications',
                         active_tab='announcements')


@teacher_blueprint.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
@teacher_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    
    flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('teacher.teacher_communications'))


@teacher_blueprint.route('/messages/mark-read/<int:message_id>', methods=['POST'])
@login_required
@teacher_required
def mark_message_read(message_id):
    """Mark a message as read."""
    message = Message.query.get_or_404(message_id)
    
    # Ensure the message belongs to the current user
    if message.recipient_id != current_user.id:
        abort(403)
    
    message.is_read = True
    message.read_at = datetime.utcnow()
    db.session.commit()
    
    flash('Message marked as read.', 'success')
    return redirect(request.referrer or url_for('teacher.teacher_messages'))


@teacher_blueprint.route('/settings')
@login_required
@teacher_required
def settings():
    """Teacher settings page."""
    teacher = TeacherStaff.query.get_or_404(current_user.teacher_staff_id)
    
    return render_template('teacher_settings.html',
                         teacher=teacher,
                         section='settings',
                         active_tab='settings')