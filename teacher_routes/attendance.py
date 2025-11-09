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
    
    return render_template('shared/attendance_hub.html', classes=classes, teacher=teacher)

@bp.route('/attendance/take/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def take_attendance(class_id):
    """Take attendance for a specific class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization for this specific class
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to take attendance for this class.", "danger")
        return redirect(url_for('teacher.attendance_hub'))
    
    # Get enrolled students for this class
    enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
    students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
    
    if request.method == 'POST':
        # Handle attendance submission
        date_str = request.form.get('date')
        if not date_str:
            flash("Please select a date.", "danger")
            return redirect(url_for('teacher.take_attendance', class_id=class_id))
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Process attendance for each student
            for student in students:
                status = request.form.get(f'status_{student.id}', 'absent')
                
                # Check if attendance already exists for this date and student
                existing_attendance = Attendance.query.filter_by(
                    class_id=class_id,
                    student_id=student.id,
                    date=date
                ).first()
                
                if existing_attendance:
                    # Update existing attendance
                    existing_attendance.status = status
                else:
                    # Create new attendance record
                    new_attendance = Attendance(
                        class_id=class_id,
                        student_id=student.id,
                        date=date,
                        status=status,
                        taken_by=current_user.id
                    )
                    db.session.add(new_attendance)
            
            db.session.commit()
            flash('Attendance recorded successfully!', 'success')
            return redirect(url_for('teacher.take_attendance', class_id=class_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error recording attendance: {str(e)}")
            flash(f'Error recording attendance: {str(e)}', 'danger')
            return redirect(url_for('teacher.take_attendance', class_id=class_id))
    
    # GET request - show attendance form
    # Get recent attendance records for context
    recent_attendance = Attendance.query.filter(
        Attendance.class_id == class_id,
        Attendance.date >= datetime.now().date() - timedelta(days=7)
    ).order_by(Attendance.date.desc()).all()
    
    # Calculate attendance statistics for today
    today = datetime.now().date()
    today_attendance = Attendance.query.filter_by(
        class_id=class_id,
        date=today
    ).all()
    
    present_count = sum(1 for a in today_attendance if a.status == 'present')
    late_count = sum(1 for a in today_attendance if a.status == 'late')
    absent_count = sum(1 for a in today_attendance if a.status == 'absent')
    total_students = len(students)
    present_percentage = round((present_count / total_students * 100) if total_students > 0 else 0, 1)
    
    attendance_stats = {
        'present': present_count,
        'late': late_count,
        'absent': absent_count,
        'present_percentage': present_percentage
    }
    
    # Create dictionaries for existing records
    existing_records = {a.student_id: a for a in today_attendance}
    school_day_records = {}  # Placeholder for school-wide attendance if needed
    
    # Define attendance status options
    statuses = ['Present', 'Late', 'Absent', 'Suspended']
    
    return render_template('shared/take_attendance.html', 
                         class_item=class_obj,
                         students=students,
                         recent_attendance=recent_attendance,
                         attendance_stats=attendance_stats,
                         attendance_date_str=today.strftime('%Y-%m-%d'),
                         existing_records=existing_records,
                         school_day_records=school_day_records,
                         statuses=statuses)

@bp.route('/mark-all-present/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def mark_all_present(class_id):
    """Mark all students as present for a class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization for this specific class
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to take attendance for this class.", "danger")
        return redirect(url_for('teacher.attendance_hub'))
    
    date_str = request.form.get('date')
    if not date_str:
        flash("Please select a date.", "danger")
        return redirect(url_for('teacher.take_attendance', class_id=class_id))
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
        
        # Mark all students as present
        for student in students:
            # Check if attendance already exists for this date and student
            existing_attendance = Attendance.query.filter_by(
                class_id=class_id,
                student_id=student.id,
                date=date
            ).first()
            
            if existing_attendance:
                # Update existing attendance
                existing_attendance.status = 'present'
            else:
                # Create new attendance record
                new_attendance = Attendance(
                    class_id=class_id,
                    student_id=student.id,
                    date=date,
                    status='present',
                    taken_by=current_user.id
                )
                db.session.add(new_attendance)
        
        db.session.commit()
        flash('All students marked as present!', 'success')
        return redirect(url_for('teacher.take_attendance', class_id=class_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error marking all present: {str(e)}")
        flash(f'Error marking all present: {str(e)}', 'danger')
        return redirect(url_for('teacher.take_attendance', class_id=class_id))

@bp.route('/quick-attendance/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def quick_attendance(class_id):
    """Quick attendance marking for a class."""
    class_obj = Class.query.get_or_404(class_id)
    
    # Check authorization for this specific class
    if not is_authorized_for_class(class_obj):
        flash("You are not authorized to take attendance for this class.", "danger")
        return redirect(url_for('teacher.attendance_hub'))
    
    date_str = request.form.get('date')
    if not date_str:
        flash("Please select a date.", "danger")
        return redirect(url_for('teacher.take_attendance', class_id=class_id))
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
        
        # Process attendance for each student
        for student in students:
            status = request.form.get(f'status_{student.id}', 'absent')
            
            # Check if attendance already exists for this date and student
            existing_attendance = Attendance.query.filter_by(
                class_id=class_id,
                student_id=student.id,
                date=date
            ).first()
            
            if existing_attendance:
                # Update existing attendance
                existing_attendance.status = status
            else:
                # Create new attendance record
                new_attendance = Attendance(
                    class_id=class_id,
                    student_id=student.id,
                    date=date,
                    status=status,
                    taken_by=current_user.id
                )
                db.session.add(new_attendance)
        
        db.session.commit()
        flash('Quick attendance recorded successfully!', 'success')
        return redirect(url_for('teacher.take_attendance', class_id=class_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error recording quick attendance: {str(e)}")
        flash(f'Error recording quick attendance: {str(e)}', 'danger')
        return redirect(url_for('teacher.take_attendance', class_id=class_id))

@bp.route('/attendance/download-template/<int:class_id>')
@login_required
@teacher_required
def download_attendance_template(class_id):
    """Download CSV template for bulk attendance upload for a specific class."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Check authorization for this specific class
        if not is_authorized_for_class(class_obj):
            flash("You are not authorized to access this class.", "danger")
            return redirect(url_for('teacher.attendance_hub'))
        
        # Get enrolled students for this class
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        students = [enrollment.student for enrollment in enrollments if enrollment.student is not None]
        
        # Create CSV template in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Date (MM/DD/YYYY)',
            'Student ID',
            'Student Name',
            'Status',
            'Notes (Optional)'
        ])
        
        # Write example rows with actual students from the class
        example_date = date.today().strftime('%m/%d/%Y')
        for student in students[:3]:  # Show first 3 students as examples
            writer.writerow([
                example_date,
                student.student_id or 'N/A',
                f'{student.first_name} {student.last_name}',
                'Present',  # Example status
                'Example note - optional'
            ])
        
        # Add instruction rows as comments
        writer.writerow([])
        writer.writerow(['# INSTRUCTIONS:'])
        writer.writerow(['# 1. Date format must be MM/DD/YYYY (e.g., 11/08/2025)'])
        writer.writerow(['# 2. Valid Status values: Present, Late, Unexcused Absence, Excused Absence, Suspended'])
        writer.writerow(['# 3. Student ID must match exactly (case-sensitive)'])
        writer.writerow(['# 4. Student Name is for reference only - matching is done by Student ID'])
        writer.writerow(['# 5. Notes are optional'])
        writer.writerow(['# 6. Delete these instruction rows before uploading'])
        writer.writerow([])
        writer.writerow(['# ENROLLED STUDENTS IN THIS CLASS:'])
        writer.writerow(['# Student ID', '# Student Name', '# Grade'])
        for student in students:
            grade_display = 'K' if student.grade_level == 0 else (str(student.grade_level) if student.grade_level else 'N/A')
            writer.writerow([
                f'# {student.student_id or "N/A"}',
                f'# {student.first_name} {student.last_name}',
                f'# Grade {grade_display}'
            ])
        
        # Create response
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
        return redirect(url_for('teacher.attendance_hub'))

@bp.route('/attendance/upload-csv/<int:class_id>', methods=['POST'])
@login_required
@teacher_required
def upload_attendance_csv(class_id):
    """Upload bulk attendance data from CSV for a specific class."""
    try:
        class_obj = Class.query.get_or_404(class_id)
        
        # Check authorization for this specific class
        if not is_authorized_for_class(class_obj):
            flash("You are not authorized to upload attendance for this class.", "danger")
            return redirect(url_for('teacher.attendance_hub'))
        
        # Check if file was uploaded
        if 'attendance_file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('teacher.attendance_hub'))
        
        file = request.files['attendance_file']
        
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('teacher.attendance_hub'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return redirect(url_for('teacher.attendance_hub'))
        
        # Read and parse CSV
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        # Get enrolled students for validation
        enrollments = Enrollment.query.filter_by(class_id=class_id, is_active=True).all()
        student_id_map = {enrollment.student.student_id: enrollment.student.id 
                          for enrollment in enrollments if enrollment.student and enrollment.student.student_id}
        
        # Valid attendance statuses
        valid_statuses = ['Present', 'Late', 'Unexcused Absence', 'Excused Absence', 'Suspended']
        
        # Track statistics
        records_added = 0
        records_updated = 0
        records_skipped = 0
        errors = []
        
        # Get teacher ID for tracking
        teacher = get_teacher_or_admin()
        teacher_id = teacher.id if teacher else None
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Skip comment rows
                date_str = row.get('Date (MM/DD/YYYY)', '').strip()
                if date_str.startswith('#') or not date_str:
                    continue
                
                student_id_str = row.get('Student ID', '').strip()
                status = row.get('Status', '').strip()
                notes = row.get('Notes (Optional)', '').strip()
                
                # Validate required fields
                if not date_str or not student_id_str or not status:
                    errors.append(f'Row {row_num}: Missing required fields (Date, Student ID, or Status)')
                    records_skipped += 1
                    continue
                
                # Parse date
                try:
                    attendance_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                except ValueError:
                    try:
                        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        errors.append(f'Row {row_num}: Invalid date format "{date_str}". Use MM/DD/YYYY')
                        records_skipped += 1
                        continue
                
                # Validate date is not in the future
                if attendance_date > date.today():
                    errors.append(f'Row {row_num}: Cannot upload attendance for future date {date_str}')
                    records_skipped += 1
                    continue
                
                # Validate status
                if status not in valid_statuses:
                    errors.append(f'Row {row_num}: Invalid status "{status}". Must be one of: {", ".join(valid_statuses)}')
                    records_skipped += 1
                    continue
                
                # Find student by ID
                if student_id_str not in student_id_map:
                    errors.append(f'Row {row_num}: Student ID "{student_id_str}" not found in class roster')
                    records_skipped += 1
                    continue
                
                student_db_id = student_id_map[student_id_str]
                
                # Check if attendance record already exists
                existing_record = Attendance.query.filter_by(
                    class_id=class_id,
                    student_id=student_db_id,
                    date=attendance_date
                ).first()
                
                if existing_record:
                    # Update existing record
                    existing_record.status = status
                    existing_record.notes = notes if notes else existing_record.notes
                    existing_record.teacher_id = teacher_id
                    records_updated += 1
                else:
                    # Create new record
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
        
        # Commit all changes
        db.session.commit()
        
        # Generate summary message
        success_msg = f'Bulk attendance upload complete: {records_added} new records added, {records_updated} records updated'
        if records_skipped > 0:
            success_msg += f', {records_skipped} records skipped'
        
        flash(success_msg, 'success')
        
        # Show errors if any
        if errors and len(errors) <= 10:  # Only show first 10 errors
            for error in errors[:10]:
                flash(error, 'warning')
        elif errors:
            flash(f'{len(errors)} errors occurred during upload. First 10 shown above.', 'warning')
        
        return redirect(url_for('teacher.take_attendance', class_id=class_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading attendance CSV: {e}")
        flash(f'Error processing CSV file: {str(e)}', 'danger')
        return redirect(url_for('teacher.attendance_hub'))

