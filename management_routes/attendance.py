"""
Attendance routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import db, Student, SchoolDayAttendance, Class, Enrollment, Attendance


bp = Blueprint('attendance', __name__)


# ============================================================
# Route: /attendance-analytics
# Function: attendance_analytics
# ============================================================

@bp.route('/attendance-analytics')
@login_required
@management_required
def attendance_analytics():
    """Attendance analytics and pattern tracking"""
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Get date range from request or default to last 30 days
    end_date_str = request.args.get('end_date')
    start_date_str = request.args.get('start_date')
    
    if end_date_str and start_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
    
    # Get all attendance records in date range
    attendance_records = Attendance.query.filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()
    
    # Analyze patterns per student
    student_patterns = defaultdict(lambda: {
        'total_days': 0,
        'present': 0,
        'absent': 0,
        'late': 0,
        'excused': 0,
        'consecutive_absences': 0,
        'max_consecutive_absences': 0,
        'current_streak': 0
    })
    
    # Group records by student and analyze
    for record in attendance_records:
        student_id = record.student_id
        pattern = student_patterns[student_id]
        pattern['total_days'] += 1
        
        if record.status == 'Present':
            pattern['present'] += 1
            pattern['consecutive_absences'] = 0
        elif record.status == 'Late':
            pattern['late'] += 1
            pattern['consecutive_absences'] = 0
        elif record.status == 'Excused Absence':
            pattern['excused'] += 1
            pattern['consecutive_absences'] += 1
        elif record.status in ['Unexcused Absence', 'Suspended']:
            pattern['absent'] += 1
            pattern['consecutive_absences'] += 1
        
        # Track max consecutive absences
        if pattern['consecutive_absences'] > pattern['max_consecutive_absences']:
            pattern['max_consecutive_absences'] = pattern['consecutive_absences']
    
    # Get students with concerns (3+ absences or 5+ late arrivals)
    at_risk_students = []
    for student_id, pattern in student_patterns.items():
        if pattern['absent'] >= 3 or pattern['late'] >= 5 or pattern['max_consecutive_absences'] >= 3:
            student = Student.query.get(student_id)
            if student:
                attendance_rate = (pattern['present'] / pattern['total_days'] * 100) if pattern['total_days'] > 0 else 0
                at_risk_students.append({
                    'student': student,
                    'pattern': pattern,
                    'attendance_rate': round(attendance_rate, 1),
                    'risk_level': 'high' if pattern['absent'] >= 5 else 'medium'
                })
    
    # Sort by risk level
    at_risk_students.sort(key=lambda x: (x['risk_level'] == 'high', x['pattern']['absent']), reverse=True)
    
    # Overall statistics
    total_records = len(attendance_records)
    present_count = len([r for r in attendance_records if r.status == 'Present'])
    overall_rate = round((present_count / total_records * 100), 1) if total_records > 0 else 0
    
    return render_template('management/attendance_analytics.html',
                         start_date=start_date,
                         end_date=end_date,
                         at_risk_students=at_risk_students,
                         overall_rate=overall_rate,
                         total_records=total_records,
                         present_count=present_count)




# ============================================================
# Route: /unified-attendance', methods=['GET', 'POST']
# Function: unified_attendance
# ============================================================

@bp.route('/unified-attendance', methods=['GET', 'POST'])
@login_required
@management_required
def unified_attendance():
    """Unified attendance management combining school day, class period, and reports"""
    from datetime import datetime, date
    
    # Handle School Day Attendance POST requests
    if request.method == 'POST' and 'attendance_date' in request.form:
        attendance_date_str = request.form.get('attendance_date')
        if not attendance_date_str:
            flash('Please select a date.', 'danger')
            return redirect(url_for('management.unified_attendance'))
        
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
        
        # Get all students
        students = Student.query.all()
        
        # Process attendance records
        updated_count = 0
        created_count = 0
        
        for student in students:
            student_id = student.id
            status = request.form.get(f'status-{student_id}')
            notes = request.form.get(f'notes-{student_id}', '').strip()
            
            if status:
                # Check if record already exists
                existing_record = SchoolDayAttendance.query.filter_by(
                    student_id=student_id,
                    date=attendance_date
                ).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.status = status
                    existing_record.notes = notes
                    existing_record.recorded_by = current_user.id
                    existing_record.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new record
                    new_record = SchoolDayAttendance(
                        student_id=student_id,
                        date=attendance_date,
                        status=status,
                        notes=notes,
                        recorded_by=current_user.id
                    )
                    db.session.add(new_record)
                    created_count += 1
        
        try:
            db.session.commit()
            if created_count > 0 and updated_count > 0:
                flash(f'Successfully recorded attendance for {created_count} students and updated {updated_count} existing records.', 'success')
            elif created_count > 0:
                flash(f'Successfully recorded attendance for {created_count} students.', 'success')
            elif updated_count > 0:
                flash(f'Successfully updated attendance for {updated_count} students.', 'success')
            else:
                flash('No attendance changes were made.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving attendance: {str(e)}', 'danger')
        
        return redirect(url_for('management.unified_attendance', date=attendance_date_str))
    
    # GET request - show unified attendance form
    
    # School Day Attendance Data
    selected_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = datetime.now().date()
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    
    # Get all students
    students = Student.query.order_by(Student.last_name, Student.first_name).all()
    
    # Get existing attendance records for the selected date
    existing_records = {}
    if selected_date:
        records = SchoolDayAttendance.query.filter_by(date=selected_date).all()
        existing_records = {record.student_id: record for record in records}
    
    # Calculate school day statistics
    total_students = len(students)
    present_count = sum(1 for record in existing_records.values() if record.status == 'Present')
    absent_count = sum(1 for record in existing_records.values() if record.status == 'Absent')
    late_count = sum(1 for record in existing_records.values() if record.status == 'Late')
    excused_count = sum(1 for record in existing_records.values() if record.status == 'Excused Absence')
    
    attendance_stats = {
        'total': total_students,
        'present': present_count,
        'absent': absent_count,
        'late': late_count,
        'excused': excused_count
    }
    
    # Class Period Attendance Data
    # Get class_date parameter for Class Period tab (separate from School Day date)
    # If class_date is not provided, use today's date (not the School Day date)
    class_date_str = request.args.get('class_date')
    if not class_date_str:
        class_date_str = datetime.now().strftime('%Y-%m-%d')
    try:
        class_date = datetime.strptime(class_date_str, '%Y-%m-%d').date()
    except ValueError:
        class_date = datetime.now().date()
        class_date_str = class_date.strftime('%Y-%m-%d')
    
    classes = Class.query.all()
    today_date = class_date_str  # Use selected date for display
    
    # Calculate attendance stats for each class for the selected date
    for class_obj in classes:
        # Get student count
        class_obj.student_count = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_obj.id,
            Enrollment.is_active == True
        ).count()
        
        # Check if attendance was taken for the selected date
        date_attendance = Attendance.query.filter_by(
            class_id=class_obj.id,
            date=class_date
        ).count()
        class_obj.attendance_taken_today = date_attendance > 0
        
        # Get attendance stats for the selected date
        if class_obj.attendance_taken_today:
            present_count = Attendance.query.filter_by(
                class_id=class_obj.id,
                date=class_date,
                status='Present'
            ).count()
            absent_count = Attendance.query.filter(
                Attendance.class_id == class_obj.id,
                Attendance.date == class_date,
                Attendance.status.in_(['Unexcused Absence', 'Excused Absence'])
            ).count()
            class_obj.today_present = present_count
            class_obj.today_absent = absent_count
        else:
            class_obj.today_present = 0
            class_obj.today_absent = 0
    
    # Calculate overall stats for the selected date
    today_attendance_count = sum(1 for c in classes if c.attendance_taken_today)
    pending_classes_count = len(classes) - today_attendance_count
    
    # Calculate overall attendance rate for the selected date
    total_attendance_records = Attendance.query.filter_by(date=class_date).count()
    present_records = Attendance.query.filter_by(date=class_date, status='Present').count()
    overall_attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
    
    # Attendance Reports Data
    all_students = Student.query.all()
    all_classes = Class.query.all()
    all_statuses = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']

    # Query and filter attendance records
    query = Attendance.query
    # (Filters can be added here in the future)
    records = query.all()

    # Calculate summary stats from the database
    summary_stats = {
        'total_records': len(records),
        'present': query.filter_by(status='Present').count(),
        'late': query.filter_by(status='Late').count(),
        'unexcused_absence': query.filter_by(status='Unexcused Absence').count(),
        'excused_absence': query.filter_by(status='Excused Absence').count(),
        'suspended': query.filter_by(status='Suspended').count()
    }
    
    return render_template('shared/unified_attendance.html',
                         students=students,
                         selected_date=selected_date,
                         selected_date_str=selected_date_str,
                         existing_records=existing_records,
                         attendance_stats=attendance_stats,
                         classes=classes,
                         today_date=today_date,
                         today_attendance_count=today_attendance_count,
                         pending_classes_count=pending_classes_count,
                         overall_attendance_rate=overall_attendance_rate,
                         all_students=all_students,
                         all_classes=all_classes,
                         all_statuses=all_statuses,
                         summary_stats=summary_stats,
                         records=records,
                         active_tab='attendance')



# ============================================================
# Route: /school-day-attendance', methods=['GET', 'POST']
# Function: school_day_attendance
# ============================================================

@bp.route('/school-day-attendance', methods=['GET', 'POST'])
@login_required
@management_required
def school_day_attendance():
    """Manage school-day attendance for all students"""
    from datetime import datetime, date
    
    if request.method == 'POST':
        attendance_date_str = request.form.get('attendance_date')
        if not attendance_date_str:
            flash('Please select a date.', 'danger')
            return redirect(url_for('management.school_day_attendance'))
        
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
        
        # Get all students
        students = Student.query.all()
        
        # Process attendance records
        updated_count = 0
        created_count = 0
        
        for student in students:
            student_id = student.id
            status = request.form.get(f'status_{student_id}')
            notes = request.form.get(f'notes_{student_id}', '').strip()
            
            if status:
                # Check if record already exists
                existing_record = SchoolDayAttendance.query.filter_by(
                    student_id=student_id,
                    date=attendance_date
                ).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.status = status
                    existing_record.notes = notes
                    existing_record.recorded_by = current_user.id
                    existing_record.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new record
                    new_record = SchoolDayAttendance(
                        student_id=student_id,
                        date=attendance_date,
                        status=status,
                        notes=notes,
                        recorded_by=current_user.id
                    )
                    db.session.add(new_record)
                    created_count += 1
        
        try:
            db.session.commit()
            if created_count > 0 and updated_count > 0:
                flash(f'Successfully recorded attendance for {created_count} students and updated {updated_count} existing records.', 'success')
            elif created_count > 0:
                flash(f'Successfully recorded attendance for {created_count} students.', 'success')
            elif updated_count > 0:
                flash(f'Successfully updated attendance for {updated_count} students.', 'success')
            else:
                flash('No attendance changes were made.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving attendance: {str(e)}', 'danger')
        
        return redirect(url_for('management.school_day_attendance', date=attendance_date_str))
    
    # GET request - show attendance form
    selected_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = datetime.now().date()
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    
    # Get all students
    students = Student.query.order_by(Student.last_name, Student.first_name).all()
    
    # Get existing attendance records for the selected date
    existing_records = {}
    if selected_date:
        records = SchoolDayAttendance.query.filter_by(date=selected_date).all()
        existing_records = {record.student_id: record for record in records}
    
    # Calculate statistics
    total_students = len(students)
    present_count = sum(1 for record in existing_records.values() if record.status == 'Present')
    absent_count = sum(1 for record in existing_records.values() if record.status == 'Absent')
    late_count = sum(1 for record in existing_records.values() if record.status == 'Late')
    excused_count = sum(1 for record in existing_records.values() if record.status == 'Excused Absence')
    
    attendance_stats = {
        'total': total_students,
        'present': present_count,
        'absent': absent_count,
        'late': late_count,
        'excused': excused_count
    }
    
    return render_template('shared/school_day_attendance.html',
                         students=students,
                         selected_date=selected_date,
                         selected_date_str=selected_date_str,
                         existing_records=existing_records,
                         attendance_stats=attendance_stats)



# ============================================================
# Route: /attendance
# Function: attendance
# ============================================================

@bp.route('/attendance')
@login_required
@management_required
def attendance():
    """Management attendance hub with improved interface."""
    # Get all classes
    classes = Class.query.all()
    
    # Get today's date
    from datetime import datetime
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # Calculate attendance stats for each class
    for class_obj in classes:
        # Get student count
        class_obj.student_count = db.session.query(Student).join(Enrollment).filter(
            Enrollment.class_id == class_obj.id,
            Enrollment.is_active == True
        ).count()
        
        # Check if attendance was taken today
        today_attendance = Attendance.query.filter_by(
            class_id=class_obj.id,
            date=datetime.now().date()
        ).count()
        class_obj.attendance_taken_today = today_attendance > 0
        
        # Get today's attendance stats
        if class_obj.attendance_taken_today:
            present_count = Attendance.query.filter_by(
                class_id=class_obj.id,
                date=datetime.now().date(),
                status='Present'
            ).count()
            absent_count = Attendance.query.filter(
                Attendance.class_id == class_obj.id,
                Attendance.date == datetime.now().date(),
                Attendance.status.in_(['Unexcused Absence', 'Excused Absence'])
            ).count()
            class_obj.today_present = present_count
            class_obj.today_absent = absent_count
        else:
            class_obj.today_present = 0
            class_obj.today_absent = 0
    
    # Calculate overall stats
    today_attendance_count = sum(1 for c in classes if c.attendance_taken_today)
    pending_classes_count = len(classes) - today_attendance_count
    
    # Calculate overall attendance rate
    total_attendance_records = Attendance.query.filter_by(date=datetime.now().date()).count()
    present_records = Attendance.query.filter_by(date=datetime.now().date(), status='Present').count()
    overall_attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
    
    return render_template('shared/attendance_hub.html',
                         classes=classes,
                         today_date=today_date,
                         today_attendance_count=today_attendance_count,
                         pending_classes_count=pending_classes_count,
                         overall_attendance_rate=overall_attendance_rate,
                         section='attendance',
                         active_tab='attendance')



# ============================================================
# Route: /attendance/reports
# Function: attendance_reports
# ============================================================

@bp.route('/attendance/reports')
@login_required
@management_required
def attendance_reports():
    all_students = Student.query.all()
    all_classes = Class.query.all()
    all_statuses = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']

    # Query and filter attendance records
    query = Attendance.query
    # (Filters can be added here in the future)
    records = query.all()

    # Calculate summary stats from the database
    summary_stats = {
        'total_records': len(records),
        'present': query.filter_by(status='Present').count(),
        'late': query.filter_by(status='Late').count(),
        'unexcused_absence': query.filter_by(status='Unexcused Absence').count(),
        'excused_absence': query.filter_by(status='Excused Absence').count(),
        'suspended': query.filter_by(status='Suspended').count()
    }

    return render_template('shared/attendance_report_view.html',
                         all_students=all_students,
                         all_classes=all_classes,
                         all_statuses=all_statuses,
                         selected_student_ids=[],
                         selected_class_ids=[],
                         selected_status='',
                         selected_start_date='',
                         selected_end_date='',
                         summary_stats=summary_stats,
                         records=records,
                         section='attendance_reports',
                         active_tab='attendance_reports')

