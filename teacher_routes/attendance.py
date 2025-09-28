"""
Attendance management routes for teachers.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from decorators import teacher_required
from .utils import get_teacher_or_admin, is_admin, is_authorized_for_class
from models import db, Class, Attendance, Enrollment
from datetime import datetime, timedelta

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
    
    return render_template('attendance_hub_simple.html', classes=classes, teacher=teacher)

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
    
    return render_template('take_attendance.html', 
                         class_obj=class_obj,
                         students=students,
                         recent_attendance=recent_attendance)

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

