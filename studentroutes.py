import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Student, Class, Assignment, Submission, Grade, SchoolYear, Announcement, Notification, StudentGoal, Message, MessageGroup, MessageGroupMember, TeacherStaff, User
from decorators import student_required
import json
from datetime import datetime, timedelta

student_blueprint = Blueprint('student', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx', 'pptx', 'md'}

def allowed_file(filename):
    """Checks if the file's extension is in the allowed set."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_gpa(grades):
    """Calculate GPA from a list of grade percentages."""
    if not grades:
        return 0.0
    
    # Convert percentage to 4.0 scale
    def percentage_to_gpa(percentage):
        if percentage >= 93: return 4.0
        elif percentage >= 90: return 3.7
        elif percentage >= 87: return 3.3
        elif percentage >= 83: return 3.0
        elif percentage >= 80: return 2.7
        elif percentage >= 77: return 2.3
        elif percentage >= 73: return 2.0
        elif percentage >= 70: return 1.7
        elif percentage >= 67: return 1.3
        elif percentage >= 63: return 1.0
        elif percentage >= 60: return 0.7
        else: return 0.0
    
    gpa_points = [percentage_to_gpa(grade) for grade in grades]
    return round(sum(gpa_points) / len(gpa_points), 2)

def get_grade_trends(student_id, class_id, limit=10):
    """Get grade trends for a specific class."""
    submissions = Submission.query.filter_by(
        student_id=student_id
    ).join(Assignment).filter(
        Assignment.class_id == class_id
    ).order_by(Submission.submitted_at.desc()).limit(limit).all()
    
    trends = []
    for submission in reversed(submissions):  # Reverse to show chronological order
        if submission.grade:
            trends.append({
                'assignment': submission.assignment.title,
                'grade': submission.grade,
                'date': submission.submitted_at.strftime('%Y-%m-%d')
            })
    
    return trends

@student_blueprint.route('/dashboard')
@login_required
@student_required
def student_dashboard():
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get current school year
    current_school_year = SchoolYear.query.filter_by(is_active=True).first()
    if not current_school_year:
        flash("No active school year found.", "warning")
        return render_template('role_student_dashboard.html', 
                             student=student, 
                             classes=[], 
                             grades={}, 
                             attendance_summary={},
                             notifications=[],
                             gpa=0.0,
                             grade_trends={},
                             today_schedule=[],
                             goals={},
                             announcements=[],
                             past_due_assignments=[],
                             upcoming_assignments=[],
                             recent_grades=[],
                             section='home',
                             active_tab='home')

    # Get student's classes - simplified for now since Enrollment model doesn't exist
    classes = Class.query.all()  # Simplified - should filter by enrollment

    # Get grades for each class and calculate GPA
    grades = {}
    grade_trends = {}
    all_grades = []
    
    for c in classes:
        # Get grades for this class
        class_grades = Grade.query.join(Assignment).filter(
            Grade.student_id == student.id,
            Assignment.class_id == c.id,
            Assignment.school_year_id == current_school_year.id
        ).all()
        
        if class_grades:
            # Calculate average grade for this class
            grade_percentages = []
            for g in class_grades:
                grade_data = json.loads(g.grade_data)
                if 'score' in grade_data:
                    grade_percentages.append(grade_data['score'])
            
            if grade_percentages:
                avg_grade = round(sum(grade_percentages) / len(grade_percentages), 2)
                grades[c.name] = avg_grade
                all_grades.append(avg_grade)
                
                # Get grade trends for this class
                grade_trends[c.id] = get_grade_trends(student.id, c.id)
    
    # Calculate overall GPA
    gpa = calculate_gpa(all_grades)
    
    # Get student goals
    goals = StudentGoal.query.filter_by(student_id=student.id).all()
    goals_dict = {goal.class_id: goal for goal in goals}
    
    # Get today's schedule (simplified - would come from actual schedule data)
    today = datetime.now()
    today_schedule = []
    for c in classes:
        # Simplified schedule - in real app, this would come from a Schedule model
        today_schedule.append({
            'class': c,
            'time': '9:00 AM',  # Placeholder
            'room': 'Room 101',  # Placeholder
            'teacher': c.teacher.first_name + ' ' + c.teacher.last_name if c.teacher else 'TBD'
        })
    
    # Sort by time (placeholder sorting)
    today_schedule.sort(key=lambda x: x['time'])

    # Get attendance summary - simplified since Attendance model doesn't exist
    attendance_summary = {
        'Present': 0,  # Placeholder - would be calculated from Attendance model
        'Tardy': 0,
        'Absent': 0,
    }

    # Get notifications for the current user
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.timestamp.desc()).limit(10).all()

    # Get assignments for notifications (simplified)
    assignments = Assignment.query.all()
    past_due_assignments = []
    upcoming_assignments = []
    recent_grades = []
    
    for assignment in assignments:
        # Check if past due
        if assignment.due_date and assignment.due_date < today:
            past_due_assignments.append(assignment)
        # Check if upcoming (due within 7 days)
        elif assignment.due_date and assignment.due_date <= today + timedelta(days=7):
            upcoming_assignments.append(assignment)
    
    # Get recent grades (simplified)
    submissions = Submission.query.filter_by(student_id=student.id).limit(5).all()
    for submission in submissions:
        if submission.grade:
            recent_grades.append(submission)
    
    # Announcements: all students, all, or for any of their classes
    class_ids = [c.id for c in classes]
    announcements = Announcement.query.filter(
        (Announcement.target_group.in_(['all_students', 'all'])) |
        ((Announcement.target_group == 'class') & (Announcement.class_id.in_(class_ids)))
    ).order_by(Announcement.timestamp.desc()).all()

    return render_template('role_student_dashboard.html', 
                         student=student, 
                         classes=classes, 
                         grades=grades, 
                         attendance_summary=attendance_summary, 
                         announcements=announcements,
                         notifications=notifications,
                         school_year=current_school_year,
                         past_due_assignments=past_due_assignments,
                         upcoming_assignments=upcoming_assignments,
                         recent_grades=recent_grades,
                         gpa=gpa,
                         grade_trends=grade_trends,
                         today_schedule=today_schedule,
                         goals=goals_dict,
                         section='home',
                         active_tab='home')

@student_blueprint.route('/assignments')
@login_required
@student_required
def student_assignments():
    student = Student.query.get_or_404(current_user.student_id)
    from datetime import datetime
    
    # Get assignments for student's classes (simplified)
    assignments = Assignment.query.all()  # Should filter by student's enrolled classes
    
    # Create assignments with status for template
    assignments_with_status = []
    for assignment in assignments:
        # Check if student has submitted this assignment
        submission = Submission.query.filter_by(
            student_id=student.id,
            assignment_id=assignment.id
        ).first()
        
        assignments_with_status.append((assignment, submission))
    
    return render_template('role_student_dashboard.html', 
                         student=student, 
                         classes=[], 
                         grades={}, 
                         attendance_summary={},
                         assignments_with_status=assignments_with_status,
                         today=datetime.now(),
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         section='assignments',
                         active_tab='assignments')

@student_blueprint.route('/classes')
@login_required
@student_required
def student_classes():
    student = Student.query.get_or_404(current_user.student_id)
    classes = Class.query.all()  # Simplified - should filter by enrollment
    return render_template('role_student_dashboard.html', 
                         student=student, 
                         classes=[], 
                         grades={}, 
                         attendance_summary={},
                         my_classes=classes,  # Template expects 'my_classes'
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         section='classes',
                         active_tab='classes')

@student_blueprint.route('/grades')
@login_required
@student_required
def student_grades():
    student = Student.query.get_or_404(current_user.student_id)
    
    # Create sample grades data for demonstration
    grades_by_class = {
        'Mathematics': {
            'final_grade': {'letter': 'A', 'percentage': 92},
            'grades': {
                'Q1': {'overall_letter': 'A', 'overall_percentage': 90, 'grade_details': {'Quiz 1': '95%', 'Homework 1': '85%'}},
                'Q2': {'overall_letter': 'A', 'overall_percentage': 94, 'grade_details': {'Quiz 2': '98%', 'Homework 2': '90%'}},
                'Q3': {'overall_letter': 'A', 'overall_percentage': 91, 'grade_details': {'Quiz 3': '92%', 'Homework 3': '90%'}},
                'Q4': {'overall_letter': 'A', 'overall_percentage': 93, 'grade_details': {'Quiz 4': '95%', 'Homework 4': '91%'}}
            }
        },
        'Science': {
            'final_grade': {'letter': 'B+', 'percentage': 87},
            'grades': {
                'Q1': {'overall_letter': 'B', 'overall_percentage': 85, 'grade_details': {'Lab Report 1': '88%', 'Quiz 1': '82%'}},
                'Q2': {'overall_letter': 'B+', 'overall_percentage': 87, 'grade_details': {'Lab Report 2': '90%', 'Quiz 2': '84%'}},
                'Q3': {'overall_letter': 'B+', 'overall_percentage': 88, 'grade_details': {'Lab Report 3': '89%', 'Quiz 3': '87%'}},
                'Q4': {'overall_letter': 'B+', 'overall_percentage': 88, 'grade_details': {'Lab Report 4': '91%', 'Quiz 4': '85%'}}
            }
        }
    }
    
    return render_template('role_student_dashboard.html', 
                         student=student, 
                         classes=[], 
                         grades={}, 
                         attendance_summary={},
                         grades_by_class=grades_by_class,
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         section='grades',
                         active_tab='grades')
                         
@student_blueprint.route('/schedule')
@login_required
@student_required
def student_schedule():
    student = Student.query.get_or_404(current_user.student_id)
    return render_template('role_student_dashboard.html', 
                         student=student, 
                         classes=[], 
                         grades={}, 
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         section='schedule',
                         active_tab='schedule')

@student_blueprint.route('/school-calendar')
@login_required
@student_required
def student_school_calendar():
    """View school calendar (read-only for students)"""
    from datetime import datetime, timedelta, date
    import calendar as cal
    
    # Try to import holidays, but provide fallback if not available
    try:
        import holidays as pyholidays
        holidays_available = True
    except ImportError:
        holidays_available = False
        current_app.logger.warning("holidays package not available, using basic calendar")

    # --- Custom holidays for Jewish, Christian, Muslim ---
    def get_religious_holidays(year):
        # Jewish holidays (fixed dates for demonstration; real dates vary by Hebrew calendar)
        jewish = [
            (date(year, 4, 23), "Passover (Pesach)"),
            (date(year, 9, 16), "Rosh Hashanah"),
            (date(year, 9, 25), "Yom Kippur"),
            (date(year, 9, 30), "Sukkot"),
            (date(year, 12, 25), "Hanukkah (start)")
        ]
        # Christian holidays
        christian = [
            (date(year, 12, 25), "Christmas"),
            (date(year, 4, 20), "Easter"),  # Example date; real date varies
            (date(year, 12, 24), "Christmas Eve"),
            (date(year, 1, 6), "Epiphany"),
            (date(year, 4, 18), "Good Friday")
        ]
        # Muslim holidays (fixed dates for demonstration; real dates vary by Islamic calendar)
        muslim = [
            (date(year, 3, 10), "Ramadan Begins"),
            (date(year, 4, 9), "Eid al-Fitr"),
            (date(year, 6, 16), "Eid al-Adha")
        ]
        return jewish + christian + muslim

    student = Student.query.get_or_404(current_user.student_id)
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    current_date = datetime(year, month, 1)
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)
    cal_obj = cal.monthcalendar(year, month)
    month_name = datetime(year, month, 1).strftime('%B')

    # US Federal holidays
    if holidays_available:
        us_holidays = pyholidays.country_holidays('US', years=[year])
    else:
        # Basic US holidays as fallback
        us_holidays = {
            date(year, 1, 1): "New Year's Day",
            date(year, 7, 4): "Independence Day",
            date(year, 11, 11): "Veterans Day",
            date(year, 12, 25): "Christmas Day"
        }
    
    # Religious holidays
    religious_holidays = get_religious_holidays(year)
    # Combine all holidays for this month
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
                for hol_day, hol_name in holidays_this_month:
                    if day == hol_day:
                        events.append({'title': hol_name, 'category': 'Holiday'})
            if day == 0:
                week_data.append({'day_num': '', 'is_current_month': False, 'is_today': False, 'events': []})
            else:
                is_today = (day == datetime.now().day and month == datetime.now().month and year == datetime.now().year)
                week_data.append({'day_num': day, 'is_current_month': True, 'is_today': is_today, 'events': events})
        calendar_data['weeks'].append(week_data)

    return render_template('role_student_dashboard.html', 
                         student=student, 
                         classes=[], 
                         grades={}, 
                         attendance_summary={},
                         calendar_data=calendar_data,
                         prev_month=prev_month,
                         next_month=next_month,
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         section='school-calendar',
                         active_tab='school-calendar')

@student_blueprint.route('/settings')
@login_required
@student_required
def student_settings():
    student = Student.query.get_or_404(current_user.student_id)
    return render_template('role_student_dashboard.html', 
                         student=student, 
                         classes=[], 
                         grades={}, 
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         section='settings',
                         active_tab='settings')

@student_blueprint.route('/class/<int:class_id>')
@login_required
@student_required
def view_class(class_id):
    student = Student.query.get_or_404(current_user.student_id)
    class_obj = Class.query.get_or_404(class_id)
    
    # Verify student is enrolled in this class - simplified for now
    # In a real implementation, you'd check Enrollment model
    # enrollment = Enrollment.query.filter_by(student_id=student.id, class_id=class_id).first()
    # if not enrollment:
    #     abort(403)

    assignments = Assignment.query.filter_by(class_id=class_id).order_by(Assignment.due_date.desc()).all()
    
    # Get submissions and grades for this student
    student_grades = {g.assignment_id: json.loads(g.grade_data) for g in Grade.query.filter_by(student_id=student.id).all()}
    student_submissions = {s.assignment_id: s for s in Submission.query.filter_by(student_id=student.id).all()}

    return render_template('role_student_forms.html', class_obj=class_obj, assignments=assignments, grades=student_grades, submissions=student_submissions)


@student_blueprint.route('/submit/<int:assignment_id>', methods=['POST'])
@login_required
@student_required
def submit_assignment(assignment_id):
    student = Student.query.get_or_404(current_user.student_id)
    assignment = Assignment.query.get_or_404(assignment_id)

    if 'submission_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.referrer or url_for('student.view_class', class_id=assignment.class_id))
    
    file = request.files['submission_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.referrer or url_for('student.view_class', class_id=assignment.class_id))

    if file and allowed_file(file.filename):
        # Type assertion for filename
        assert file.filename is not None
        filename = secure_filename(file.filename)
        # Create a unique filename to avoid collisions
        unique_filename = f"sub_{student.id}_{assignment.id}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(filepath)
            
            # Check for existing submission and update it, or create a new one
            submission = Submission.query.filter_by(student_id=student.id, assignment_id=assignment_id).first()
            if submission:
                # Optionally, delete the old file
                if submission.file_path and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], submission.file_path)):
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], submission.file_path))
                submission.file_path = unique_filename
                submission.submitted_at = db.func.now()
            else:
                # Create new submission using attribute assignment
                submission = Submission()
                submission.student_id = student.id
                submission.assignment_id = assignment_id
                submission.file_path = unique_filename
                db.session.add(submission)
            
            db.session.commit()
            flash('Assignment submitted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while saving the file: {e}', 'danger')
            current_app.logger.error(f"File upload failed for student {student.id}, assignment {assignment_id}: {e}")

    else:
        flash(f'File type not allowed. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')

    return redirect(url_for('student.view_class', class_id=assignment.class_id))

@student_blueprint.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
@student_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    
    flash('Notification marked as read.', 'success')
    return redirect(request.referrer or url_for('student.student_dashboard'))

@student_blueprint.route('/goals/set', methods=['POST'])
@login_required
@student_required
def set_goal():
    """Set or update a goal for a specific class."""
    student = Student.query.get_or_404(current_user.student_id)
    
    class_id = request.form.get('class_id', type=int)
    target_grade = request.form.get('target_grade', type=float)
    
    if not class_id or not target_grade:
        flash('Please provide both class and target grade.', 'error')
        return redirect(url_for('student.student_dashboard'))
    
    # Check if goal already exists
    existing_goal = StudentGoal.query.filter_by(
        student_id=student.id,
        class_id=class_id
    ).first()
    
    if existing_goal:
        existing_goal.target_grade = target_grade
        existing_goal.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Goal updated successfully!', 'success')
    else:
        new_goal = StudentGoal(
            student_id=student.id,
            class_id=class_id,
            target_grade=target_grade
        )
        db.session.add(new_goal)
        db.session.commit()
        flash('Goal set successfully!', 'success')
    
    return redirect(url_for('student.student_dashboard'))

@student_blueprint.route('/goals/delete/<int:goal_id>', methods=['POST'])
@login_required
@student_required
def delete_goal(goal_id):
    """Delete a student goal."""
    goal = StudentGoal.query.get_or_404(goal_id)
    student = Student.query.get_or_404(current_user.student_id)
    
    # Ensure the goal belongs to the current student
    if goal.student_id != student.id:
        abort(403)
    
    db.session.delete(goal)
    db.session.commit()
    
    flash('Goal deleted successfully.', 'success')
    return redirect(url_for('student.student_dashboard'))

# Communications Routes for Students
@student_blueprint.route('/communications')
@login_required
@student_required
def student_communications():
    """Student communications hub - read-only access to messages and announcements."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get student's classes for filtering
    classes = Class.query.all()  # Simplified - should filter by enrollment
    class_ids = [c.id for c in classes]
    
    # Get messages for the student
    messages = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.created_at.desc()).limit(20).all()
    
    # Get announcements relevant to the student
    announcements = Announcement.query.filter(
        (Announcement.target_group.in_(['all_students', 'all'])) |
        ((Announcement.target_group == 'class') & (Announcement.class_id.in_(class_ids)))
    ).order_by(Announcement.timestamp.desc()).limit(10).all()
    
    # Get notifications
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).limit(10).all()
    
    # Get message groups the student is a member of
    groups = MessageGroup.query.join(MessageGroupMember).filter(
        MessageGroupMember.user_id == current_user.id
    ).all()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=classes,
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=announcements,
                         notifications=notifications,
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         messages=messages,
                         groups=groups,
                         section='communications',
                         active_tab='communications')

@student_blueprint.route('/communications/messages')
@login_required
@student_required
def student_messages():
    """View all messages for the student."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get all messages for the student
    messages = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.created_at.desc()).all()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=[],
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         messages=messages,
                         section='messages',
                         active_tab='communications')

@student_blueprint.route('/communications/message/<int:message_id>')
@login_required
@student_required
def student_view_message(message_id):
    """View a specific message."""
    student = Student.query.get_or_404(current_user.student_id)
    message = Message.query.get_or_404(message_id)
    
    # Ensure the student is the recipient
    if message.recipient_id != current_user.id:
        abort(403)
    
    # Mark as read
    if not message.is_read:
        message.is_read = True
        db.session.commit()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=[],
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         message=message,
                         section='view_message',
                         active_tab='communications')

@student_blueprint.route('/communications/groups')
@login_required
@student_required
def student_groups():
    """View message groups the student is a member of."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get groups the student is a member of
    groups = MessageGroup.query.join(MessageGroupMember).filter(
        MessageGroupMember.user_id == current_user.id
    ).all()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=[],
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         groups=groups,
                         section='groups',
                         active_tab='communications')

@student_blueprint.route('/communications/group/<int:group_id>')
@login_required
@student_required
def student_view_group(group_id):
    """View a specific message group."""
    student = Student.query.get_or_404(current_user.student_id)
    group = MessageGroup.query.get_or_404(group_id)
    
    # Ensure the student is a member of this group
    membership = MessageGroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not membership:
        abort(403)
    
    # Get group messages
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.created_at.desc()).all()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=[],
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         group=group,
                         messages=messages,
                         section='view_group',
                         active_tab='communications')

@student_blueprint.route('/communications/announcements')
@login_required
@student_required
def student_announcements():
    """View announcements relevant to the student."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get student's classes for filtering
    classes = Class.query.all()  # Simplified - should filter by enrollment
    class_ids = [c.id for c in classes]
    
    # Get announcements relevant to the student
    announcements = Announcement.query.filter(
        (Announcement.target_group.in_(['all_students', 'all'])) |
        ((Announcement.target_group == 'class') & (Announcement.class_id.in_(class_ids)))
    ).order_by(Announcement.timestamp.desc()).all()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=[],
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=announcements,
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         section='announcements',
                         active_tab='communications')

# New routes for student messaging capabilities
@student_blueprint.route('/communications/send-message', methods=['GET', 'POST'])
@login_required
@student_required
def student_send_message():
    """Send a new message."""
    student = Student.query.get_or_404(current_user.student_id)
    
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id', type=int)
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        
        if not recipient_id or not content:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('student.student_send_message'))
        
        # Verify recipient exists
        recipient = User.query.get(recipient_id)
        if not recipient:
            flash('Invalid recipient selected.', 'error')
            return redirect(url_for('student.student_send_message'))
        
        # Create the message
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            message_type='direct'
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash('Message sent successfully!', 'success')
        return redirect(url_for('student.student_messages'))
    
    # Get potential recipients (other students and teachers)
    students = Student.query.all()
    teachers = TeacherStaff.query.all()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=[],
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         students=students,
                         teachers=teachers,
                         section='send_message',
                         active_tab='communications')

@student_blueprint.route('/communications/create-group', methods=['GET', 'POST'])
@login_required
@student_required
def student_create_group():
    """Create a new message group."""
    student = Student.query.get_or_404(current_user.student_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        group_type = request.form.get('group_type', 'student')
        member_ids = request.form.getlist('members')
        
        if not name:
            flash('Please provide a group name.', 'error')
            return redirect(url_for('student.student_create_group'))
        
        # Create the group
        group = MessageGroup(
            name=name,
            description=description,
            group_type=group_type,
            created_by=current_user.id
        )
        
        db.session.add(group)
        db.session.flush()  # Get the group ID
        
        # Add the creator as a member and admin
        creator_member = MessageGroupMember(
            group_id=group.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.session.add(creator_member)
        
        # Add other members
        for member_id in member_ids:
            if member_id and int(member_id) != current_user.id:
                member = MessageGroupMember(
                    group_id=group.id,
                    user_id=int(member_id)
                )
                db.session.add(member)
        
        db.session.commit()
        
        flash('Group created successfully!', 'success')
        return redirect(url_for('student.student_groups'))
    
    # Get potential members (other students)
    students = Student.query.filter(Student.id != student.id).all()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=[],
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         students=students,
                         section='create_group',
                         active_tab='communications')

@student_blueprint.route('/communications/group/<int:group_id>/send-message', methods=['POST'])
@login_required
@student_required
def student_send_group_message(group_id):
    """Send a message to a group."""
    student = Student.query.get_or_404(current_user.student_id)
    group = MessageGroup.query.get_or_404(group_id)
    
    # Ensure the student is a member of this group
    membership = MessageGroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not membership:
        abort(403)
    
    content = request.form.get('content', '').strip()
    subject = request.form.get('subject', '').strip()
    
    if not content:
        flash('Please provide message content.', 'error')
        return redirect(url_for('student.student_view_group', group_id=group_id))
    
    # Create the group message
    message = Message(
        sender_id=current_user.id,
        recipient_id=None,  # Group messages don't have a specific recipient
        subject=subject,
        content=content,
        message_type='group',
        group_id=group_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    flash('Message sent to group!', 'success')
    return redirect(url_for('student.student_view_group', group_id=group_id))

@student_blueprint.route('/communications/sent-messages')
@login_required
@student_required
def student_sent_messages():
    """View messages sent by the student."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Get messages sent by the student
    sent_messages = Message.query.filter_by(sender_id=current_user.id).order_by(Message.created_at.desc()).all()
    
    return render_template('role_student_dashboard.html',
                         student=student,
                         classes=[],
                         grades={},
                         attendance_summary={},
                         gpa=0.0,
                         grade_trends={},
                         today_schedule=[],
                         goals={},
                         announcements=[],
                         notifications=[],
                         past_due_assignments=[],
                         upcoming_assignments=[],
                         recent_grades=[],
                         sent_messages=sent_messages,
                         section='sent_messages',
                         active_tab='communications')

@student_blueprint.route('/communications/group/<int:group_id>/leave', methods=['POST'])
@login_required
@student_required
def student_leave_group(group_id):
    """Leave a message group."""
    student = Student.query.get_or_404(current_user.student_id)
    
    # Find the membership
    membership = MessageGroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('student.student_groups'))
    
    # Don't allow the creator to leave (or implement group transfer logic)
    group = MessageGroup.query.get(group_id)
    if group.created_by == current_user.id:
        flash('Group creators cannot leave their own groups.', 'error')
        return redirect(url_for('student.student_groups'))
    
    db.session.delete(membership)
    db.session.commit()
    
    flash('You have left the group.', 'success')
    return redirect(url_for('student.student_groups'))
