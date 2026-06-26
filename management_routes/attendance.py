"""
Attendance routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import db, Student, SchoolDayAttendance, Class, Enrollment, Attendance
from sqlalchemy.orm import joinedload


bp = Blueprint('attendance', __name__)


@bp.context_processor
def attendance_template_context():
    """Quick links for attendance reports (used in dashboard sidebars)."""
    from datetime import datetime, timedelta

    today = datetime.now().date()

    def _reports_url(start, end):
        return url_for(
            'management.unified_attendance',
            reports_tab=1,
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.strftime('%Y-%m-%d'),
        )

    return {
        'attendance_quick_links': {
            'daily': _reports_url(today, today),
            'weekly': _reports_url(today - timedelta(days=6), today),
            'monthly': _reports_url(today - timedelta(days=29), today),
            'reports': url_for('management.unified_attendance', reports_tab=1),
            'analytics': url_for('management.attendance_analytics'),
        },
    }


# ============================================================
# Route: /attendance-analytics
# Function: attendance_analytics
# ============================================================

def _attendance_analytics_date_range(request):
    """Parse analytics date range (default last 30 days)."""
    from datetime import datetime, timedelta

    today = datetime.now().date()
    start_str = (request.args.get('start_date') or '').strip()
    end_str = (request.args.get('end_date') or '').strip()

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
            start_date = end_date - timedelta(days=30)
    elif start_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = today
        except ValueError:
            end_date = today
            start_date = end_date - timedelta(days=30)
    elif end_str:
        try:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            start_date = end_date - timedelta(days=30)
        except ValueError:
            end_date = today
            start_date = end_date - timedelta(days=30)
    else:
        end_date = today
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    return start_date, end_date


def _attendance_analytics_context(request):
    """Build attendance analytics summary, trends, and at-risk student list."""
    from datetime import datetime, timedelta
    from collections import defaultdict
    from urllib.parse import urlencode

    start_date, end_date = _attendance_analytics_date_range(request)
    today = datetime.now().date()
    days_analyzed = (end_date - start_date).days + 1

    risk_filter = (request.args.get('risk') or 'all').strip().lower()
    if risk_filter not in ('all', 'high', 'medium'):
        risk_filter = 'all'

    attendance_records = (
        Attendance.query.options(joinedload(Attendance.student))
        .filter(Attendance.date >= start_date, Attendance.date <= end_date)
        .order_by(Attendance.student_id, Attendance.date)
        .all()
    )

    status_counts = {
        'present': 0,
        'late': 0,
        'unexcused': 0,
        'excused': 0,
        'suspended': 0,
        'other': 0,
    }
    daily_buckets = defaultdict(lambda: {'total': 0, 'present': 0})

    for record in attendance_records:
        daily_buckets[record.date]['total'] += 1
        if record.status == 'Present':
            status_counts['present'] += 1
            daily_buckets[record.date]['present'] += 1
        elif record.status == 'Late':
            status_counts['late'] += 1
        elif record.status == 'Unexcused Absence':
            status_counts['unexcused'] += 1
        elif record.status == 'Excused Absence':
            status_counts['excused'] += 1
        elif record.status == 'Suspended':
            status_counts['suspended'] += 1
        else:
            status_counts['other'] += 1

    student_patterns = defaultdict(lambda: {
        'total_days': 0,
        'present': 0,
        'absent': 0,
        'late': 0,
        'excused': 0,
        'consecutive_absences': 0,
        'max_consecutive_absences': 0,
    })

    records_by_student = defaultdict(list)
    for record in attendance_records:
        records_by_student[record.student_id].append(record)

    for student_id, records in records_by_student.items():
        pattern = student_patterns[student_id]
        for record in sorted(records, key=lambda r: r.date):
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
            elif record.status in ('Unexcused Absence', 'Suspended'):
                pattern['absent'] += 1
                pattern['consecutive_absences'] += 1
            if pattern['consecutive_absences'] > pattern['max_consecutive_absences']:
                pattern['max_consecutive_absences'] = pattern['consecutive_absences']

    at_risk_students = []
    for student_id, pattern in student_patterns.items():
        if pattern['absent'] < 3 and pattern['late'] < 5 and pattern['max_consecutive_absences'] < 3:
            continue
        student = records_by_student[student_id][0].student if records_by_student[student_id] else Student.query.get(student_id)
        if not student:
            continue
        attendance_rate = (pattern['present'] / pattern['total_days'] * 100) if pattern['total_days'] > 0 else 0
        risk_level = 'high' if pattern['absent'] >= 5 or pattern['max_consecutive_absences'] >= 5 else 'medium'
        at_risk_students.append({
            'student': student,
            'pattern': pattern,
            'attendance_rate': round(attendance_rate, 1),
            'risk_level': risk_level,
        })

    at_risk_students.sort(
        key=lambda x: (
            x['risk_level'] != 'high',
            -x['pattern']['absent'],
            -x['pattern']['late'],
            x['student'].last_name,
        ),
    )

    at_risk_high = sum(1 for s in at_risk_students if s['risk_level'] == 'high')
    at_risk_medium = sum(1 for s in at_risk_students if s['risk_level'] == 'medium')
    if risk_filter != 'all':
        at_risk_students = [s for s in at_risk_students if s['risk_level'] == risk_filter]

    total_records = len(attendance_records)
    present_count = status_counts['present']
    overall_rate = round((present_count / total_records * 100), 1) if total_records > 0 else 0
    students_tracked = len(student_patterns)

    daily_trend = []
    cursor = start_date
    while cursor <= end_date:
        bucket = daily_buckets.get(cursor, {'total': 0, 'present': 0})
        rate = round((bucket['present'] / bucket['total'] * 100), 1) if bucket['total'] else None
        daily_trend.append({
            'date': cursor,
            'date_label': cursor.strftime('%b %d'),
            'total': bucket['total'],
            'present': bucket['present'],
            'rate': rate,
        })
        cursor += timedelta(days=1)

    trend_max = max((d['total'] for d in daily_trend), default=1) or 1

    form_action = url_for('management.attendance_analytics')
    preset_defs = [
        ('7 days', today - timedelta(days=6), today),
        ('30 days', today - timedelta(days=29), today),
        ('90 days', today - timedelta(days=89), today),
        ('Year', today - timedelta(days=364), today),
    ]
    preset_urls = []
    for label, p_start, p_end in preset_defs:
        q = urlencode([
            ('start_date', p_start.strftime('%Y-%m-%d')),
            ('end_date', p_end.strftime('%Y-%m-%d')),
        ])
        if risk_filter != 'all':
            q += '&' + urlencode([('risk', risk_filter)])
        preset_urls.append({'label': label, 'url': f'{form_action}?{q}'})

    return {
        'selected_start_date': start_date.strftime('%Y-%m-%d'),
        'selected_end_date': end_date.strftime('%Y-%m-%d'),
        'days_analyzed': days_analyzed,
        'risk_filter': risk_filter,
        'analytics_form_action': form_action,
        'preset_urls': preset_urls,
        'analytics_back_url': url_for('management.unified_attendance'),
        'analytics_reports_url': url_for(
            'management.unified_attendance',
            reports_tab=1,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
        ),
        'at_risk_students': at_risk_students,
        'overall_rate': overall_rate,
        'total_records': total_records,
        'present_count': present_count,
        'students_tracked': students_tracked,
        'at_risk_high': at_risk_high,
        'at_risk_medium': at_risk_medium,
        'status_counts': status_counts,
        'daily_trend': daily_trend,
        'trend_max': trend_max,
    }


def _wants_analytics_partial(request):
    return (
        request.method == 'GET'
        and request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )


@bp.route('/attendance-analytics')
@login_required
@management_required
def attendance_analytics():
    """Attendance analytics and pattern tracking"""
    if (
        request.method == "GET"
        and current_app.config.get("REACT_SPA_ENABLED")
        and request.args.get("legacy") != "1"
    ):
        from utils.user_roles import user_has_management_entry_access

        if user_has_management_entry_access(current_user):
            path = "/app/management/attendance/analytics"
            query = request.query_string.decode("utf-8") if request.query_string else ""
            if query:
                path = f"{path}?{query}"
            return redirect(path)

    ctx = _attendance_analytics_context(request)
    if _wants_analytics_partial(request):
        return render_template('management/_attendance_analytics_panel.html', **ctx)
    return render_template('management/attendance_analytics.html', active_tab='attendance', **ctx)




# ============================================================
# Route: /mark-all-present/<int:class_id>, methods=['POST']
# Function: mark_all_present
# ============================================================

@bp.route('/mark-all-present/<int:class_id>', methods=['POST'])
@login_required
@management_required
def mark_all_present(class_id):
    """Mark all enrolled students as present for a class (admin override)."""
    from datetime import datetime

    class_obj = Class.query.get_or_404(class_id)

    from utils.school_year_filters import get_active_school_year

    active_school_year = get_active_school_year()
    if not active_school_year:
        flash("No active school year is set.", "danger")
        return redirect(url_for('management.unified_attendance'))
    if class_obj.school_year_id != active_school_year.id or not class_obj.is_active:
        flash("Class is not part of the active school year.", "danger")
        return redirect(url_for('management.unified_attendance'))

    date_str = request.form.get('date')
    if not date_str:
        flash("Please select a date.", "danger")
        return redirect(url_for('management.unified_attendance'))

    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]

        teacher_id = getattr(current_user, 'teacher_staff_id', None)

        for student in students:
            existing_attendance = Attendance.query.filter_by(
                class_id=class_id,
                student_id=student.id,
                date=attendance_date
            ).first()

            if existing_attendance:
                existing_attendance.status = 'Present'
                existing_attendance.teacher_id = teacher_id
            else:
                new_attendance = Attendance(
                    class_id=class_id,
                    student_id=student.id,
                    date=attendance_date,
                    status='Present',
                    teacher_id=teacher_id
                )
                db.session.add(new_attendance)

        db.session.commit()
        flash('All students marked as present!', 'success')
        return redirect(url_for('management.unified_attendance', class_date=date_str, date=date_str))

    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for('management.unified_attendance'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking all present: {e}")
        flash(f'Error marking all present: {str(e)}', 'danger')
        return redirect(url_for('management.unified_attendance'))


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
        
        from utils.student_roster import active_roster_students_query
        students = active_roster_students_query(require_active_enrollment=False).all()
        
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
    if (
        request.method == "GET"
        and current_app.config.get("REACT_SPA_ENABLED")
        and request.args.get("legacy") != "1"
    ):
        from utils.user_roles import user_has_management_entry_access

        if user_has_management_entry_access(current_user):
            path = "/app/management/attendance"
            query = request.query_string.decode("utf-8") if request.query_string else ""
            if query:
                path = f"{path}?{query}"
            return redirect(path)

    if _wants_reports_partial(request):
        reports_ctx = _attendance_reports_context(
            request,
            form_action=url_for('management.unified_attendance'),
            embed_tab=True,
        )
        return render_template(
            'shared/_attendance_reports_panel.html',
            reports_tab_active=True,
            show_reports_page_header=False,
            **reports_ctx,
        )

    reports_tab_active = _reports_tab_active(request)

    # School Day Attendance Data
    selected_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = datetime.now().date()
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    
    from utils.student_roster import active_roster_students_query
    students = (
        active_roster_students_query(require_active_enrollment=False)
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    
    # End-of-day automark: if viewing today and it's >= 3:30 PM (school time), mark unrecorded students as Unexcused Absence
    try:
        from services.attendance_on_login import _now_in_school_tz, is_past_end_of_day_cutoff, apply_end_of_day_automark
        school_today, _ = _now_in_school_tz(current_app)
        if selected_date == school_today and is_past_end_of_day_cutoff(current_app):
            apply_end_of_day_automark(current_app, selected_date)
    except Exception as e:
        current_app.logger.warning('End-of-day attendance automark failed: %s', e)
    
    # Get existing attendance records for the selected date
    existing_records = {}
    if selected_date:
        records = SchoolDayAttendance.query.filter_by(date=selected_date).all()
        existing_records = {record.student_id: record for record in records}
    
    # Calculate school day statistics (Absent = Absent + Unexcused Absence)
    total_students = len(students)
    present_count = sum(1 for record in existing_records.values() if record.status == 'Present')
    absent_count = sum(
        1 for record in existing_records.values()
        if record.status in ('Absent', 'Unexcused Absence')
    )
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
    
    from utils.school_year_filters import classes_for_active_school_year

    classes = classes_for_active_school_year()
    class_ids = [class_obj.id for class_obj in classes]
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
    if class_ids:
        total_attendance_records = Attendance.query.filter(
            Attendance.date == class_date,
            Attendance.class_id.in_(class_ids),
        ).count()
        present_records = Attendance.query.filter(
            Attendance.date == class_date,
            Attendance.class_id.in_(class_ids),
            Attendance.status == 'Present',
        ).count()
    else:
        total_attendance_records = 0
        present_records = 0
    overall_attendance_rate = round((present_records / total_attendance_records * 100), 1) if total_attendance_records > 0 else 0
    
    reports_ctx = _attendance_reports_context(
        request,
        form_action=url_for('management.unified_attendance'),
        embed_tab=True,
    )

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
                         active_tab='attendance',
                         reports_tab_active=reports_tab_active,
                         **reports_ctx)



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
        
        from utils.student_roster import active_roster_students_query
        students = active_roster_students_query(require_active_enrollment=False).all()
        
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
    
    from utils.student_roster import active_roster_students_query
    students = (
        active_roster_students_query(require_active_enrollment=False)
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    
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
    from utils.school_year_filters import classes_for_active_school_year

    classes = classes_for_active_school_year()
    
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



ATTENDANCE_REPORT_STATUSES = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']
ATTENDANCE_REPORTS_PER_PAGE = 50


def _parse_id_list(values):
    ids = []
    for raw in values or []:
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    return ids


def _has_reports_query_params(request):
    """True when the request includes report filter/pagination params (not just defaults)."""
    if request.args.get('reports_tab') == '1':
        return True
    if (request.args.get('start_date') or '').strip():
        return True
    if (request.args.get('end_date') or '').strip():
        return True
    if (request.args.get('status') or '').strip():
        return True
    if request.args.getlist('student_ids') or request.args.getlist('class_ids'):
        return True
    if request.args.get('student_id') or request.args.get('class_id'):
        return True
    if request.args.get('page', type=int):
        return True
    return False


def _reports_tab_active(request):
    return _has_reports_query_params(request)


def _wants_reports_partial(request):
    return (
        request.method == 'GET'
        and request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        and (
            request.args.get('reports_partial') == '1'
            or request.args.get('reports_tab') == '1'
            or _has_reports_query_params(request)
        )
    )


def _attendance_report_filters(start_date, end_date, student_ids, class_ids, status):
    filters = [
        Attendance.date >= start_date,
        Attendance.date <= end_date,
    ]
    if student_ids:
        filters.append(Attendance.student_id.in_(student_ids))
    if class_ids:
        filters.append(Attendance.class_id.in_(class_ids))
    if status:
        filters.append(Attendance.status == status)
    return filters


def _attendance_reports_context(request, form_action=None, embed_tab=False):
    """Build filtered, paginated attendance report data (defaults to last 30 days)."""
    from datetime import datetime, timedelta
    from urllib.parse import urlencode

    today = datetime.now().date()
    start_str = (request.args.get('start_date') or '').strip()
    end_str = (request.args.get('end_date') or '').strip()

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
            start_date = end_date - timedelta(days=30)
    elif start_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = today
        except ValueError:
            end_date = today
            start_date = end_date - timedelta(days=30)
    elif end_str:
        try:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            start_date = end_date - timedelta(days=30)
        except ValueError:
            end_date = today
            start_date = end_date - timedelta(days=30)
    else:
        end_date = today
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    student_ids = _parse_id_list(request.args.getlist('student_ids'))
    if not student_ids and request.args.get('student_id'):
        student_ids = _parse_id_list([request.args.get('student_id')])

    class_ids = _parse_id_list(request.args.getlist('class_ids'))
    if not class_ids and request.args.get('class_id'):
        class_ids = _parse_id_list([request.args.get('class_id')])

    status = (request.args.get('status') or '').strip()
    page = max(1, request.args.get('page', 1, type=int))

    filters = _attendance_report_filters(start_date, end_date, student_ids, class_ids, status)
    base_query = Attendance.query.filter(*filters)

    def _count_with_status(status_value):
        q_filters = list(filters)
        if status_value:
            q_filters.append(Attendance.status == status_value)
        return Attendance.query.filter(*q_filters).count()

    summary_stats = {
        'total_records': _count_with_status(None),
        'present': _count_with_status('Present'),
        'late': _count_with_status('Late'),
        'unexcused_absence': _count_with_status('Unexcused Absence'),
        'excused_absence': _count_with_status('Excused Absence'),
        'suspended': _count_with_status('Suspended'),
    }

    def _paginate_reports(page_num):
        return (
            Attendance.query.filter(*filters)
            .options(
                joinedload(Attendance.student),
                joinedload(Attendance.class_info),
                joinedload(Attendance.teacher),
            )
            .order_by(Attendance.date.desc(), Attendance.id.desc())
            .paginate(page=page_num, per_page=ATTENDANCE_REPORTS_PER_PAGE, error_out=False)
        )

    pagination = _paginate_reports(page)
    if pagination.pages and page > pagination.pages:
        page = 1
        pagination = _paginate_reports(page)

    from utils.student_roster import active_roster_students_query
    all_students = (
        active_roster_students_query(require_active_enrollment=True)
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    all_classes = Class.query.order_by(Class.name).all()

    if not form_action:
        form_action = url_for('management.unified_attendance')

    def _build_query(extra=None):
        params = [
            ('start_date', start_date.strftime('%Y-%m-%d')),
            ('end_date', end_date.strftime('%Y-%m-%d')),
        ]
        if status:
            params.append(('status', status))
        for sid in student_ids:
            params.append(('student_ids', sid))
        for cid in class_ids:
            params.append(('class_ids', cid))
        if embed_tab:
            params.append(('reports_tab', '1'))
        if extra:
            params.extend(extra)
        return urlencode(params)

    preset_defs = [
        ('Today', today, today),
        ('7 days', today - timedelta(days=6), today),
        ('30 days', today - timedelta(days=29), today),
        ('90 days', today - timedelta(days=89), today),
    ]
    preset_urls = []
    for label, p_start, p_end in preset_defs:
        q = urlencode([
            ('start_date', p_start.strftime('%Y-%m-%d')),
            ('end_date', p_end.strftime('%Y-%m-%d')),
        ] + ([('reports_tab', '1')] if embed_tab else []))
        preset_urls.append({'label': label, 'url': f'{form_action}?{q}'})

    full_page_base = url_for('management.attendance_reports')
    reports_full_page_url = f'{full_page_base}?{_build_query()}'

    reset_q = urlencode([('reports_tab', '1')] if embed_tab else [])
    reports_reset_url = f'{form_action}?{reset_q}' if reset_q else form_action

    return {
        'reports_form_action': form_action,
        'reports_reset_url': reports_reset_url,
        'reports_embed_tab': embed_tab,
        'reports_full_page_url': reports_full_page_url,
        'preset_urls': preset_urls,
        'all_students': all_students,
        'all_classes': all_classes,
        'all_statuses': ATTENDANCE_REPORT_STATUSES,
        'selected_student_ids': student_ids,
        'selected_class_ids': class_ids,
        'selected_status': status,
        'selected_start_date': start_date.strftime('%Y-%m-%d'),
        'selected_end_date': end_date.strftime('%Y-%m-%d'),
        'summary_stats': summary_stats,
        'records': pagination.items,
        'pagination': pagination,
        'reports_per_page': ATTENDANCE_REPORTS_PER_PAGE,
        'default_range_days': 30,
    }


# ============================================================
# Route: /attendance/reports
# Function: attendance_reports
# ============================================================

@bp.route('/attendance/reports')
@login_required
@management_required
def attendance_reports():
    if (
        request.method == "GET"
        and current_app.config.get("REACT_SPA_ENABLED")
        and request.args.get("legacy") != "1"
        and not _wants_reports_partial(request)
    ):
        from utils.user_roles import user_has_management_entry_access

        if user_has_management_entry_access(current_user):
            path = "/app/management/attendance/reports"
            query = request.query_string.decode("utf-8") if request.query_string else ""
            if query:
                path = f"{path}?{query}"
            return redirect(path)

    ctx = _attendance_reports_context(
        request,
        form_action=url_for('management.attendance_reports'),
        embed_tab=False,
    )
    if _wants_reports_partial(request):
        return render_template(
            'shared/_attendance_reports_panel.html',
            reports_tab_active=True,
            show_reports_page_header=True,
            reports_back_url=url_for('management.unified_attendance', reports_tab='1'),
            **ctx,
        )
    return render_template(
        'shared/attendance_report_view.html',
        section='attendance_reports',
        active_tab='attendance_reports',
        reports_back_url=url_for('management.unified_attendance', reports_tab='1'),
        show_reports_page_header=True,
        **ctx,
    )

