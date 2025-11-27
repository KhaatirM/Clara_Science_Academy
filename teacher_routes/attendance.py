"""
Attendance management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, current_app
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import db, Class, Attendance, Enrollment, Student, TeacherStaff
from datetime import datetime, timedelta, date
import csv
import io

bp = Blueprint('attendance', __name__)

@bp.route('/attendance')
@login_required
@teacher_required
def attendance_hub():
    """Main attendance hub for teachers."""
    from datetime import date
    
    # Get teacher object or None for administrators
    teacher = get_teacher_or_admin()
    
    # Get classes for the current teacher/admin
    if is_admin():
        classes = Class.query.all()
    else:
        if teacher is None:
            classes = []
        else:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    # Check attendance status for each class
    today = date.today()
    completed_today = 0
    pending_count = 0
    
    for class_obj in classes:
        # Check if attendance was taken today for this class
        attendance_today = Attendance.query.filter_by(
            class_id=class_obj.id,
            date=today
        ).first()
        
        class_obj.attendance_taken_today = attendance_today is not None
        
        if attendance_today:
            completed_today += 1
        else:
            pending_count += 1
    
    return render_template('shared/attendance_hub.html', 
                         classes=classes, 
                         teacher=teacher,
                         completed_today_count=completed_today,
                         pending_classes_count=pending_count,
                         total_classes_count=len(classes))

@bp.route('/attendance/take/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def take_attendance(class_id):
    """Take attendance for a specific class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization for this specific class
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to take attendance for this class.", "danger")
        return redirect(url_for('teacher.attendance.attendance_hub'))
    
    # Get enrolled students for this class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    if request.method == 'POST':
        # Handle attendance submission
        date_str = request.form.get('date')
        if not date_str:
            flash("Please select a date.", "danger")
            return redirect(url_for('teacher.attendance.take_attendance', class_id=class_id))
        
        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Process attendance for each student
            for student in students:
                status = request.form.get(f'status_{student.id}', 'absent')
                
                # Check if attendance already exists for this date and student
                existing_attendance = Attendance.query.filter_by(
                    class_id=class_id,
                    student_id=student.id,
                    date=attendance_date
                ).first()
                
                if existing_attendance:
                    # Update existing attendance
                    existing_attendance.status = status
                else:
                    # Create new attendance record
                    new_attendance = Attendance(
                        class_id=class_id,
                        student_id=student.id,
                        date=attendance_date,
                        status=status,
                        teacher_id=current_user.teacher_staff_id
                    )
                    db.session.add(new_attendance)
            
            db.session.commit()
            flash('Attendance recorded successfully!', 'success')
            return redirect(url_for('teacher.attendance.take_attendance', class_id=class_id, date=date_str))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error recording attendance: {str(e)}")
            flash(f'Error recording attendance: {str(e)}', 'danger')
            return redirect(url_for('teacher.attendance.take_attendance', class_id=class_id))
    
    # GET request - show attendance form
    # Get date from query parameter or default to today
    date_str = request.args.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = datetime.now().date()
    else:
        selected_date = datetime.now().date()
    
    # Get recent attendance records for context
    recent_attendance = Attendance.query.filter(
        Attendance.class_id == class_id,
        Attendance.date >= datetime.now().date() - timedelta(days=7)
    ).order_by(Attendance.date.desc()).all()
    
    # Get attendance for the selected date
    selected_date_attendance = Attendance.query.filter_by(
        class_id=class_id,
        date=selected_date
    ).all()
    
    present_count = sum(1 for a in selected_date_attendance if a.status.lower() == 'present')
    late_count = sum(1 for a in selected_date_attendance if a.status.lower() == 'late')
    absent_count = sum(1 for a in selected_date_attendance if a.status.lower() in ['absent', 'unexcused absence', 'excused absence'])
    total_students = len(students)
    present_percentage = round((present_count / total_students * 100) if total_students > 0 else 0, 1)
    
    attendance_stats = {
        'present': present_count,
        'late': late_count,
        'absent': absent_count,
        'present_percentage': present_percentage
    }
    
    # Create dictionaries for existing records
    existing_records = {a.student_id: a for a in selected_date_attendance}
    school_day_records = {}  # Placeholder for school-wide attendance if needed
    
    # Define attendance status options
    statuses = ['Present', 'Late', 'Excused Absence', 'Unexcused Absence', 'Suspended']
    
    return render_template('shared/take_attendance.html', 
                         class_item=class_obj,
                         students=students,
                         recent_attendance=recent_attendance,
                         attendance_stats=attendance_stats,
                         attendance_date_str=selected_date.strftime('%Y-%m-%d'),
                         existing_records=existing_records,
                         school_day_records=school_day_records,
                         statuses=statuses)

@bp.route('/attendance/records/<int:class_id>')
@login_required
@teacher_required
def view_attendance_records(class_id):
    """View attendance records for a class with filtering options."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Check authorization
        if not is_authorized_for_class(class_obj):
            flash("You are not authorized to view attendance for this class.", "danger")
            return redirect(url_for('teacher.attendance.attendance_hub'))
        
        # Get filter parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        student_id_filter = request.args.get('student_id', type=int)
        status_filter = request.args.get('status')
        
        # Default to last 30 days if no dates provided
        if not start_date_str:
            start_date = date.today() - timedelta(days=30)
        else:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = date.today() - timedelta(days=30)
        
        if not end_date_str:
            end_date = date.today()
        else:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                end_date = date.today()
        
        # Build query with join to Student table for ordering
        # Use joinedload to ensure student relationship is loaded
        from sqlalchemy.orm import joinedload
        query = Attendance.query.options(joinedload(Attendance.student)).join(Student).filter(
            Attendance.class_id == class_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )
        
        if student_id_filter:
            query = query.filter(Attendance.student_id == student_id_filter)
        
        if status_filter:
            query = query.filter(Attendance.status.ilike(f'%{status_filter}%'))
        
        # Get attendance records ordered by date (descending) and then by student name
        attendance_records = query.order_by(Attendance.date.desc(), Student.last_name, Student.first_name).all()
        
        # Get enrolled students for filter dropdown
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
        
        # Group records by date
        records_by_date = {}
        for record in attendance_records:
            if record.student:  # Safety check in case student relationship is None
                date_key = record.date.isoformat()
                if date_key not in records_by_date:
                    records_by_date[date_key] = []
                records_by_date[date_key].append(record)
        
        # Calculate summary statistics
        total_records = len(attendance_records)
        present_count = sum(1 for r in attendance_records if r.status and r.status.lower() == 'present')
        late_count = sum(1 for r in attendance_records if r.status and r.status.lower() == 'late')
        absent_count = sum(1 for r in attendance_records if r.status and r.status.lower() in ['absent', 'unexcused absence', 'excused absence'])
        
        summary_stats = {
            'total': total_records,
            'present': present_count,
            'late': late_count,
            'absent': absent_count,
            'rate': round((present_count / total_records * 100) if total_records > 0 else 0, 1)
        }
        
        return render_template('shared/view_attendance_records.html',
                             class_item=class_obj,
                             students=students,
                             records_by_date=records_by_date,
                             summary_stats=summary_stats,
                             start_date=start_date,
                             end_date=end_date,
                             student_id_filter=student_id_filter,
                             status_filter=status_filter)
    
    except Exception as e:
        current_app.logger.error(f"Error in view_attendance_records: {str(e)}", exc_info=True)
        flash(f'Error loading attendance records: {str(e)}', 'danger')
        return redirect(url_for('teacher.attendance.attendance_hub'))

@bp.route('/mark-all-present/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def mark_all_present(class_id):
    """Mark all students as present for a class."""
    class_obj = Class.query.get_or_404(class_id)
    
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to take attendance for this class.", "danger")
        return redirect(url_for('teacher.attendance.attendance_hub'))
    
    date_str = request.form.get('date')
    if not date_str:
        flash("Please select a date.", "danger")
        return redirect(url_for('teacher.attendance.take_attendance', class_id=class_id))
    
    try:
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
        
        for student in students:
            existing_attendance = Attendance.query.filter_by(
                class_id=class_id,
                student_id=student.id,
                date=attendance_date
            ).first()
            
            if existing_attendance:
                existing_attendance.status = 'present'
            else:
                new_attendance = Attendance(
                    class_id=class_id,
                    student_id=student.id,
                    date=attendance_date,
                    status='present',
                    teacher_id=current_user.teacher_staff_id
                )
                db.session.add(new_attendance)
        
        db.session.commit()
        flash('All students marked as present!', 'success')
        return redirect(url_for('teacher.attendance.take_attendance', class_id=class_id, date=date_str))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error marking all present: {str(e)}")
        flash(f'Error marking all present: {str(e)}', 'danger')
        return redirect(url_for('teacher.attendance.take_attendance', class_id=class_id))

@bp.route('/attendance/download-template/<int:class_id>')
@login_required
@teacher_required
def download_attendance_template(class_id):
    """Download CSV template for bulk attendance upload for a specific class."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        if not is_authorized_for_class(class_obj):
            flash("You are not authorized to access this class.", "danger")
            return redirect(url_for('teacher.attendance.attendance_hub'))
        
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Date (MM/DD/YYYY)',
            'Student ID',
            'Student Name',
            'Status',
            'Notes (Optional)'
        ])
        
        example_date = date.today().strftime('%m/%d/%Y')
        for student in students[:3]:
            writer.writerow([
                example_date,
                student.student_id or 'N/A',
                f'{student.first_name} {student.last_name}',
                'Present',
                'Example note - optional'
            ])
        
        output.seek(0)
        filename = f'attendance_template_{class_obj.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.csv'
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating attendance template: {e}")
        flash('Error generating template. Please try again.', 'danger')
        return redirect(url_for('teacher.attendance.attendance_hub'))

@bp.route('/attendance/upload-csv/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def upload_attendance_csv(class_id):
    """Upload bulk attendance data from CSV for a specific class."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        if not is_authorized_for_class(class_obj):
            flash("You are not authorized to upload attendance for this class.", "danger")
            return redirect(url_for('teacher.attendance.attendance_hub'))
        
        if 'attendance_file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('teacher.attendance.attendance_hub'))
        
        file = request.files['attendance_file']
        
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('teacher.attendance.attendance_hub'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return redirect(url_for('teacher.attendance.attendance_hub'))
        
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        student_id_map = {enrollment.student.student_id: enrollment.student.id 
                          for enrollment in enrollments if enrollment.student and enrollment.student.student_id}
        
        valid_statuses = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']
        
        records_added = 0
        records_updated = 0
        records_skipped = 0
        errors = []
        
        teacher = get_teacher_or_admin()
        teacher_id = teacher.id if teacher else None
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                date_str = row.get('Date (MM/DD/YYYY)', '').strip()
                if date_str.startswith('#') or not date_str:
                    continue
                
                student_id_str = row.get('Student ID', '').strip()
                status = row.get('Status', '').strip()
                notes = row.get('Notes (Optional)', '').strip()
                
                if not date_str or not student_id_str or not status:
                    errors.append(f'Row {row_num}: Missing required fields (Date, Student ID, or Status)')
                    records_skipped += 1
                    continue
                
                try:
                    attendance_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                except ValueError:
                    try:
                        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        errors.append(f'Row {row_num}: Invalid date format "{date_str}". Use MM/DD/YYYY')
                        records_skipped += 1
                        continue
                
                if attendance_date > date.today():
                    errors.append(f'Row {row_num}: Cannot upload attendance for future date {date_str}')
                    records_skipped += 1
                    continue
                
                if status not in valid_statuses:
                    errors.append(f'Row {row_num}: Invalid status "{status}". Must be one of: {", ".join(valid_statuses)}')
                    records_skipped += 1
                    continue
                
                if student_id_str not in student_id_map:
                    errors.append(f'Row {row_num}: Student ID "{student_id_str}" not found in class roster')
                    records_skipped += 1
                    continue
                
                student_db_id = student_id_map[student_id_str]
                
                existing_record = Attendance.query.filter_by(
                    class_id=class_id,
                    student_id=student_db_id,
                    date=attendance_date
                ).first()
                
                if existing_record:
                    existing_record.status = status
                    existing_record.notes = notes if notes else existing_record.notes
                    existing_record.teacher_id = teacher_id
                    records_updated += 1
                else:
                    new_record = Attendance(
                        class_id=class_id,
                        student_id=student_db_id,
                        date=attendance_date,
                        status=status,
                        notes=notes,
                        teacher_id=teacher_id
                    )
                    db.session.add(new_record)
                    records_added += 1
                    
            except Exception as e:
                errors.append(f'Row {row_num}: Error processing - {str(e)}')
                records_skipped += 1
                continue
        
        db.session.commit()
        
        success_msg = f'Bulk attendance upload complete: {records_added} new records added, {records_updated} records updated'
        if records_skipped > 0:
            success_msg += f', {records_skipped} records skipped'
        
        flash(success_msg, 'success')
        
        if errors and len(errors) <= 10:
            for error in errors[:10]:
                flash(error, 'warning')
        elif errors:
            flash(f'{len(errors)} errors occurred during upload. First 10 shown above.', 'warning')
        
        return redirect(url_for('teacher.attendance.take_attendance', class_id=class_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading attendance CSV: {e}")
        flash(f'Error processing CSV file: {str(e)}', 'danger')
        return redirect(url_for('teacher.attendance.attendance_hub'))