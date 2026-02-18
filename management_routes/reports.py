"""
Reports routes for management users.
"""

import json
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import db, ReportCard, SchoolYear, Class, Student, Enrollment


bp = Blueprint('reports', __name__)


def _sanitize_letter_grades_for_report(obj):
    """
    Recursively replace 'F' with 'D' in grade data (minimum letter grade is D).
    Handles grades dict, grades_by_quarter, and nested structures.
    """
    if obj is None:
        return obj
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in ('letter', 'letter_grade', 'overall_letter', 'grade') and v == 'F':
                result[k] = 'D'
            else:
                result[k] = _sanitize_letter_grades_for_report(v)
        return result
    if isinstance(obj, list):
        return [_sanitize_letter_grades_for_report(item) for item in obj]
    return obj


# ============================================================
# Route: /report/card/generate', methods=['GET', 'POST']
# Function: generate_report_card_form
# ============================================================

@bp.route('/report/card/generate', methods=['GET', 'POST'])
@login_required
@management_required
def generate_report_card_form():
    students = Student.query.order_by(Student.last_name, Student.first_name).all()
    school_years = SchoolYear.query.order_by(SchoolYear.name.desc()).all()
    
    if request.method == 'POST':
        # Get form data
        student_id = request.form.get('student_id')
        school_year_id = request.form.get('school_year_id')
        class_ids = request.form.getlist('class_ids')  # Get multiple class IDs
        selected_quarters = request.form.getlist('quarters')  # Get selected quarters
        report_type = request.form.get('report_type', 'official')  # Default to official
        include_attendance = request.form.get('include_attendance') == 'on'
        include_comments = request.form.get('include_comments') == 'on'
        
        if not all([student_id, school_year_id]):
            flash("Please select a student and school year.", 'danger')
            return redirect(request.url)
        
        if not class_ids:
            flash("Please select at least one class.", 'danger')
            return redirect(request.url)
        
        if not selected_quarters:
            flash("Please select at least one quarter.", 'danger')
            return redirect(request.url)

        # Validate that the values can be converted to integers
        try:
            student_id_int = int(student_id)
            school_year_id_int = int(school_year_id)
            class_ids_int = [int(cid) for cid in class_ids]
        except ValueError:
            flash("Invalid student, school year, or class selection.", 'danger')
            return redirect(request.url)
        
        # Use selected quarters instead of auto-determining
        # Validate selected quarters
        valid_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
        quarters_to_include = [q for q in selected_quarters if q in valid_quarters]
        
        if not quarters_to_include:
            flash("Invalid quarter selection. Please select valid quarters.", 'danger')
            return redirect(request.url)
        
        # Determine the report period based on selected quarters
        # If only one quarter selected, use that; otherwise use range (e.g., "Q1-Q2")
        if len(quarters_to_include) == 1:
            quarter_str = quarters_to_include[0]
        else:
            # Sort quarters and create range string
            quarter_nums = sorted([int(q.replace('Q', '')) for q in quarters_to_include])
            if len(quarter_nums) == len(quarters_to_include) and quarter_nums == list(range(min(quarter_nums), max(quarter_nums) + 1)):
                # Consecutive quarters - show as range
                quarter_str = f"Q{quarter_nums[0]}-Q{quarter_nums[-1]}"
            else:
                # Non-consecutive - use the latest quarter as primary, but show all
                quarter_str = quarters_to_include[-1]  # Use last selected as primary
        
        current_app.logger.info(f"Selected quarters: {quarters_to_include}, Report period: {quarter_str}")

        # Verify all selected classes exist and student is ACTIVELY enrolled
        valid_class_ids = []
        for class_id in class_ids_int:
            enrollment = Enrollment.query.filter_by(
                student_id=student_id_int,
                class_id=class_id,
                is_active=True  # Only include active enrollments
            ).first()
            
            if enrollment:
                valid_class_ids.append(class_id)
            else:
                flash(f"Student is not actively enrolled in one of the selected classes (ID: {class_id}).", 'warning')
        
        if not valid_class_ids:
            flash("No valid classes selected for this student.", 'danger')
            return redirect(request.url)
        
        # Calculate grades for selected classes only
        # Filter grades by selected class_ids
        from models import Grade, Assignment
        student = Student.query.get(student_id_int)
        
        # Update quarter grades in database (calculates/refreshes if needed)
        from utils.quarter_grade_calculator import update_all_quarter_grades_for_student, get_quarter_grades_for_report
        
        # Update/calculate quarter grades for this student
        # Force recalculation to ensure accurate weighted averages based on points
        update_all_quarter_grades_for_student(
            student_id=student_id_int,
            school_year_id=school_year_id_int,
            force=True  # Force recalculation to use corrected weighted average calculation
        )
        
        # Get quarter grades from database (all quarters)
        all_quarter_grades = get_quarter_grades_for_report(
            student_id=student_id_int,
            school_year_id=school_year_id_int,
            class_ids=valid_class_ids
        )
        
        # Filter to only include selected quarters
        # Note: get_quarter_grades_for_report may return keys as 'Q1', 'Q2', etc. or '1', '2', etc.
        # We need to handle both formats
        calculated_grades_by_quarter = {}
        for q in quarters_to_include:
            # Try both 'Q1' format and '1' format
            q_key = q
            q_num_key = q.replace('Q', '')
            
            if q_key in all_quarter_grades:
                calculated_grades_by_quarter[q] = all_quarter_grades[q_key]
            elif q_num_key in all_quarter_grades:
                calculated_grades_by_quarter[q] = all_quarter_grades[q_num_key]
            else:
                # Include empty dict for quarters without data (will show "—" in template)
                calculated_grades_by_quarter[q] = {}
        
        # Set the primary calculated_grades to the first selected quarter (or the determined quarter_str)
        if len(quarters_to_include) == 1:
            calculated_grades = calculated_grades_by_quarter.get(quarters_to_include[0], {})
        else:
            # For multiple quarters, use the first one as primary, but all will be shown
            calculated_grades = calculated_grades_by_quarter.get(quarters_to_include[0], {})
        
        # Get or create report card
        report_card = ReportCard.query.filter_by(
            student_id=student_id_int,
            school_year_id=school_year_id_int,
            quarter=quarter_str
        ).first()
        
        if not report_card:
            report_card = ReportCard()
            report_card.student_id = student_id_int
            report_card.school_year_id = school_year_id_int
            report_card.quarter = quarter_str
            db.session.add(report_card)
        
        # Store grades with metadata about selected classes and options
        report_card_data = {
            'classes': valid_class_ids,
            'report_type': report_type,
            'include_attendance': include_attendance,
            'include_comments': include_comments,
            'grades': calculated_grades,
            'grades_by_quarter': calculated_grades_by_quarter,  # Store all quarter grades
            'selected_quarters': quarters_to_include,  # Full list so PDF shows Q1–Q4, not just Q1 and Q4 from "Q1-Q4"
        }
        
        # Add attendance if requested
        if include_attendance:
            from models import Attendance
            attendance_data = {}
            for class_id in valid_class_ids:
                # Get attendance for this class in the quarter period
                # For now, get all attendance for this student in this class
                attendance_records = Attendance.query.filter_by(
                    student_id=student_id_int,
                    class_id=class_id
                ).all()
                
                attendance_summary = {
                    'Present': 0,
                    'Unexcused Absence': 0,
                    'Excused Absence': 0,
                    'Tardy': 0
                }
                
                for att in attendance_records:
                    status = att.status or 'Present'
                    if status in attendance_summary:
                        attendance_summary[status] += 1
                    else:
                        attendance_summary['Present'] += 1
                
                class_obj = Class.query.get(class_id)
                attendance_data[class_obj.name if class_obj else f"Class {class_id}"] = attendance_summary
            
            report_card_data['attendance'] = attendance_data

        # Save confirmation form data (gender, entrance date, etc.) so View → Download shows same values
        def _format_date_for_save(value):
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            from datetime import date, datetime as _dt
            if isinstance(value, (date, _dt)):
                return value.strftime('%m/%d/%Y')
            if isinstance(value, str):
                for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d'):
                    try:
                        return _dt.strptime(value.strip(), fmt).strftime('%m/%d/%Y')
                    except Exception:
                        continue
            return None
        confirm_gender = request.form.get('confirm_gender', '').strip()
        confirm_address = request.form.get('confirm_address', '').strip()
        confirm_dob = request.form.get('confirm_dob', '').strip()
        confirm_entrance_date = request.form.get('confirm_entrance_date', '').strip()
        confirm_first_name = request.form.get('confirm_first_name', '').strip()
        confirm_last_name = request.form.get('confirm_last_name', '').strip()
        confirm_expected_grad_date = request.form.get('confirm_expected_grad_date', '').strip()
        student_name = f"{confirm_first_name} {confirm_last_name}".strip() if (confirm_first_name or confirm_last_name) else f"{student.first_name} {student.last_name}"
        report_card_data['student_display'] = {
            'name': student_name,
            'gender': confirm_gender or getattr(student, 'gender', None),
            'address': confirm_address or None,
            'dob': _format_date_for_save(confirm_dob) or _format_date_for_save(getattr(student, 'dob', None)),
            'entrance_date': _format_date_for_save(confirm_entrance_date) or None,
            'expected_grad_date': confirm_expected_grad_date or None,
            'phone': getattr(student, 'phone', None),
        }
        
        # Update report card (save for record keeping)
        report_card.grades_details = json.dumps(report_card_data)
        report_card.generated_at = datetime.utcnow()
        db.session.commit()
        
        # Generate and return PDF directly
        try:
            from weasyprint import HTML
            from io import BytesIO
            from flask import make_response
            
            # Get class objects for selected classes
            class_objects = []
            if valid_class_ids:
                for class_id in valid_class_ids:
                    class_obj = Class.query.get(class_id)
                    if class_obj:
                        class_objects.append(class_obj)
            
            # Prepare student data for template (robust date handling)
            def _format_date_value(value):
                try:
                    if value is None:
                        return 'N/A'
                    # If already a date/datetime object
                    from datetime import date, datetime as _dt
                    if isinstance(value, (date, _dt)):
                        return value.strftime('%m/%d/%Y')
                    # If it's a string, try common formats, otherwise return as-is
                    if isinstance(value, str):
                        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d'):
                            try:
                                return _dt.strptime(value, fmt).strftime('%m/%d/%Y')
                            except Exception:
                                continue
                        return value
                    return 'N/A'
                except Exception:
                    return 'N/A'

            # Get confirmation form values (use form values if provided, otherwise use student data)
            confirm_gender = request.form.get('confirm_gender', '').strip()
            confirm_address = request.form.get('confirm_address', '').strip()
            confirm_dob = request.form.get('confirm_dob', '').strip()
            confirm_entrance_date = request.form.get('confirm_entrance_date', '').strip()
            confirm_first_name = request.form.get('confirm_first_name', '').strip()
            confirm_last_name = request.form.get('confirm_last_name', '').strip()
            
            # Use confirmation values if provided, otherwise fall back to student data
            student_name = f"{confirm_first_name} {confirm_last_name}".strip() if confirm_first_name or confirm_last_name else f"{student.first_name} {student.last_name}"
            student_dob = _format_date_value(confirm_dob) if confirm_dob else _format_date_value(getattr(student, 'dob', None))
            student_gender = confirm_gender if confirm_gender else getattr(student, 'gender', 'N/A')
            student_address = confirm_address if confirm_address else f"{getattr(student, 'street', '')}, {getattr(student, 'city', '')}, {getattr(student, 'state', '')} {getattr(student, 'zip_code', '')}".strip(', ')
            
            # Get expected graduation date from form
            confirm_expected_grad_date = request.form.get('confirm_expected_grad_date', '').strip()
            
            student_data = {
                'name': student_name,
                'student_id_formatted': student.student_id_formatted if hasattr(student, 'student_id_formatted') else (student.student_id if student.student_id else 'N/A'),
                'ssn': getattr(student, 'ssn', None),
                'dob': student_dob,
                'grade': student.grade_level,
                'gender': student_gender,
                'address': student_address,
                'phone': getattr(student, 'phone', ''),
                'entrance_date': _format_date_value(confirm_entrance_date) if confirm_entrance_date else 'N/A',
                'expected_grad_date': confirm_expected_grad_date if confirm_expected_grad_date else 'N/A'
            }
            
            # Choose template based on grade level and report type
            template_prefix = 'unofficial' if report_type == 'unofficial' else 'official'
            if student.grade_level in [1, 2]:
                template_name = f'management/{template_prefix}_report_card_pdf_template_1_2.html'
            elif student.grade_level == 3:
                template_name = f'management/{template_prefix}_report_card_pdf_template_3.html'
            else:  # Grades 4-8
                template_name = f'management/{template_prefix}_report_card_pdf_template_4_8.html'
            
            # Sanitize letter grades: minimum is D, never show F
            calculated_grades = _sanitize_letter_grades_for_report(calculated_grades)
            calculated_grades_by_quarter = _sanitize_letter_grades_for_report(calculated_grades_by_quarter)

            # Render the HTML template
            html_content = render_template(
                template_name,
                report_card=report_card,
                student=student_data,
                grades=calculated_grades,
                grades_by_quarter=calculated_grades_by_quarter,  # Only selected quarters
                selected_quarters=quarters_to_include,  # Pass selected quarters to template
                attendance=report_card_data.get('attendance', {}),
                class_objects=class_objects,
                include_attendance=include_attendance,
                include_comments=include_comments,
                generated_date=datetime.utcnow(),
                report_type=report_type,
                template_prefix=template_prefix
            )
            
            # Read CSS file from filesystem and inject it into the HTML
            import os
            import re
            import base64
            css_path = os.path.join(current_app.root_path, 'static', 'report_card_styles.css')
            try:
                with open(css_path, 'r', encoding='utf-8') as f:
                    css_content = f.read()
                # Inject CSS into the HTML (replace the link tag with embedded style)
                html_content = re.sub(
                    r'<link rel="stylesheet" href="[^"]*report_card_styles\.css[^"]*">',
                    f'<style>{css_content}</style>',
                    html_content
                )
            except Exception as e:
                current_app.logger.warning(f'Could not load CSS file: {str(e)}')
            
            # Read logo file and convert to base64 for embedding
            logo_path = os.path.join(current_app.root_path, 'static', 'img', 'clara_logo.png')
            try:
                with open(logo_path, 'rb') as f:
                    logo_data = base64.b64encode(f.read()).decode('utf-8')
                # Replace logo src with base64 data
                html_content = re.sub(
                    r'<img src="[^"]*clara_logo\.png[^"]*"',
                    f'<img src="data:image/png;base64,{logo_data}"',
                    html_content
                )
            except Exception as e:
                current_app.logger.warning(f'Could not load logo file: {str(e)}')
            
            # Generate PDF
            pdf_buffer = BytesIO()
            HTML(string=html_content).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)
            
            # Create response - use inline so browser can display it
            response = make_response(pdf_buffer.getvalue())
            response.headers['Content-Type'] = 'application/pdf'
            filename = f"ReportCard_{student.first_name}_{student.last_name}_{report_card.school_year.name.replace('/', '_')}_{report_card.quarter}.pdf"
            # Use 'inline' to display in browser, browser can still download if user wants
            response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            
            return response
            
        except ImportError:
            current_app.logger.error('WeasyPrint not installed')
            # Return error message as HTML that will display in new window
            error_url = url_for('management.report_cards', _external=True)
            error_html = f'''<!DOCTYPE html>
<html>
<head><title>PDF Generation Error</title></head>
<body style="font-family: Arial; padding: 40px; text-align: center;">
    <h2 style="color: #dc3545;">PDF Generation Error</h2>
    <p>PDF generation requires WeasyPrint. Please install it: <code>pip install weasyprint</code></p>
    <p><a href="{error_url}" style="color: #0d6efd;">Return to Report Cards</a></p>
</body>
</html>'''
            return error_html, 500
        except Exception as e:
            current_app.logger.error(f'Error generating PDF: {str(e)}')
            import traceback
            current_app.logger.error(traceback.format_exc())
            # Return error message as HTML that will display in new window
            error_url = url_for('management.report_cards', _external=True)
            error_html = f'''<!DOCTYPE html>
<html>
<head><title>PDF Generation Error</title></head>
<body style="font-family: Arial; padding: 40px; text-align: center;">
    <h2 style="color: #dc3545;">PDF Generation Error</h2>
    <p>An error occurred while generating the PDF: <strong>{str(e)}</strong></p>
    <p style="font-size: 12px; color: #666;">Please check the server logs for more details.</p>
    <p><a href="{error_url}" style="color: #0d6efd;">Return to Report Cards</a></p>
</body>
</html>'''
            return error_html, 500

    return render_template('management/report_card_generate_form.html', 
                         students=students, 
                         school_years=school_years)



# ============================================================
# Route: /report/card/view/<int:report_card_id>
# Function: view_report_card
# ============================================================

@bp.route('/report/card/view/<int:report_card_id>')
@login_required
@management_required
def view_report_card(report_card_id):
    report_card = ReportCard.query.get_or_404(report_card_id)
    
    # Parse report card data (new format includes metadata)
    report_card_data = json.loads(report_card.grades_details) if report_card.grades_details else {}
    
    # Extract data from new structure (backward compatible with old format)
    if isinstance(report_card_data, dict) and 'grades' in report_card_data:
        # New format with metadata
        grades = report_card_data.get('grades', {})
        attendance = report_card_data.get('attendance', {})
        selected_classes = report_card_data.get('classes', [])
        include_attendance = report_card_data.get('include_attendance', False)
        include_comments = report_card_data.get('include_comments', False)
    else:
        # Old format (just grades dict)
        grades = report_card_data if report_card_data else {}
        attendance = {}
        selected_classes = []
        include_attendance = False
        include_comments = False
    
    # If attendance is empty but was requested, provide default
    if not attendance and include_attendance:
        attendance = {"Present": 0, "Absent": 0, "Tardy": 0}

    # Sanitize letter grades: minimum is D, never show F on report cards
    grades = _sanitize_letter_grades_for_report(grades)
    
    # Get class objects for selected classes
    class_objects = []
    if selected_classes:
        for class_id in selected_classes:
            class_obj = Class.query.get(class_id)
            if class_obj:
                class_objects.append(class_obj)

    return render_template('management/report_card_detail.html', 
                         report_card=report_card, 
                         grades=grades, 
                         attendance=attendance,
                         selected_classes=selected_classes,
                         class_objects=class_objects,
                         include_attendance=include_attendance,
                         include_comments=include_comments)



# ============================================================
# Route: /report/card/pdf/<int:report_card_id>
# Function: generate_report_card_pdf
# ============================================================

@bp.route('/report/card/pdf/<int:report_card_id>')
@login_required
@management_required
def generate_report_card_pdf(report_card_id):
    """Generate and download a PDF report card based on student's grade level"""
    try:
        from weasyprint import HTML
        from io import BytesIO
        from flask import make_response
        
        report_card = ReportCard.query.get_or_404(report_card_id)
        student = report_card.student
        
        # Parse report card data
        report_card_data = json.loads(report_card.grades_details) if report_card.grades_details else {}
        
        # Extract data from new structure (backward compatible)
        if isinstance(report_card_data, dict) and 'grades' in report_card_data:
            grades = report_card_data.get('grades', {})
            # Use saved grades_by_quarter so PDF shows what was generated, not fresh DB
            grades_by_quarter = report_card_data.get('grades_by_quarter')
            attendance = report_card_data.get('attendance', {})
            selected_classes = report_card_data.get('classes', [])
            report_type = report_card_data.get('report_type', 'official')
            include_attendance = report_card_data.get('include_attendance', False)
            include_comments = report_card_data.get('include_comments', False)
        else:
            grades = report_card_data if report_card_data else {}
            grades_by_quarter = None
            attendance = {}
            selected_classes = []
            report_type = 'official'  # Default for old report cards
            include_attendance = False
            include_comments = False

        # Only fetch fresh quarter grades from DB when we have no saved snapshot
        if not grades_by_quarter or not isinstance(grades_by_quarter, dict):
            from utils.quarter_grade_calculator import get_quarter_grades_for_report
            grades_by_quarter = get_quarter_grades_for_report(
                student_id=student.id,
                school_year_id=report_card.school_year_id,
                class_ids=selected_classes if selected_classes else None
            )

        # Sanitize letter grades: minimum is D, never show F on report cards
        grades = _sanitize_letter_grades_for_report(grades)
        grades_by_quarter = _sanitize_letter_grades_for_report(grades_by_quarter)
        
        # Get class objects
        class_objects = []
        if selected_classes:
            for class_id in selected_classes:
                class_obj = Class.query.get(class_id)
                if class_obj:
                    class_objects.append(class_obj)
        
        # Prepare student data for template (robust date handling)
        from datetime import datetime, date as date_type
        
        def _format_date_value(value):
            try:
                if value is None:
                    return 'N/A'
                # If already a date/datetime object
                if isinstance(value, (date_type, datetime)):
                    return value.strftime('%m/%d/%Y')
                # If it's a string, try common formats, otherwise return as-is
                if isinstance(value, str):
                    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d'):
                        try:
                            return datetime.strptime(value, fmt).strftime('%m/%d/%Y')
                        except Exception:
                            continue
                    return value
                return 'N/A'
            except Exception:
                return 'N/A'
        
        student_data = {
            'name': f"{student.first_name} {student.last_name}",
            'student_id_formatted': student.student_id_formatted if hasattr(student, 'student_id_formatted') else (student.student_id if student.student_id else 'N/A'),
            'ssn': getattr(student, 'ssn', None),
            'dob': _format_date_value(getattr(student, 'dob', None)),
            'grade': student.grade_level,
            'gender': getattr(student, 'gender', 'N/A'),
            'address': f"{getattr(student, 'street', '')}, {getattr(student, 'city', '')}, {getattr(student, 'state', '')} {getattr(student, 'zip_code', '')}".strip(', '),
            'phone': getattr(student, 'phone', ''),
            'entrance_date': 'N/A',
            'expected_grad_date': 'N/A',
        }
        # Override with saved confirmation data from when report was generated
        saved_student = report_card_data.get('student_display') if isinstance(report_card_data, dict) else None
        if saved_student:
            if saved_student.get('name'):
                student_data['name'] = saved_student['name']
            if saved_student.get('gender') not in (None, ''):
                student_data['gender'] = saved_student['gender']
            if saved_student.get('address') not in (None, ''):
                student_data['address'] = saved_student['address']
            if saved_student.get('dob'):
                student_data['dob'] = saved_student['dob']
            if saved_student.get('phone') is not None:
                student_data['phone'] = saved_student['phone'] or ''
            if 'entrance_date' in saved_student:
                student_data['entrance_date'] = saved_student.get('entrance_date') or 'N/A'
            if 'expected_grad_date' in saved_student:
                student_data['expected_grad_date'] = saved_student.get('expected_grad_date') or 'N/A'

        # Which quarter(s) this report card is for (PDF template uses this to show grades)
        # Prefer saved list so Q1+Q2+Q3+Q4 all show; parsing "Q1-Q4" would only give [Q1, Q4]
        saved_quarters = report_card_data.get('selected_quarters') if isinstance(report_card_data, dict) else None
        if saved_quarters and isinstance(saved_quarters, list):
            selected_quarters = [q if isinstance(q, str) and q.startswith('Q') else f'Q{q}' for q in saved_quarters]
        else:
            quarter_str = (report_card.quarter or '').strip()
            if not quarter_str:
                selected_quarters = []
            elif '-' in quarter_str:
                # Range e.g. "Q1-Q4" -> expand to all quarters in range so Q2, Q3 not lost
                parts = [p.strip() for p in quarter_str.split('-') if p.strip()]
                if len(parts) == 2:
                    try:
                        lo = int(parts[0].replace('Q', '')) if parts[0].startswith('Q') else int(parts[0])
                        hi = int(parts[1].replace('Q', '')) if parts[1].startswith('Q') else int(parts[1])
                        selected_quarters = [f'Q{i}' for i in range(lo, hi + 1)]
                    except (ValueError, TypeError):
                        selected_quarters = [p if p.startswith('Q') else f'Q{p}' for p in parts]
                else:
                    selected_quarters = [p if p.startswith('Q') else f'Q{p}' for p in parts]
            else:
                if quarter_str.startswith('Q'):
                    selected_quarters = [quarter_str]
                else:
                    try:
                        selected_quarters = [f'Q{int(quarter_str)}']
                    except (ValueError, TypeError):
                        selected_quarters = [quarter_str]

        # Choose template based on grade level and report type
        template_prefix = 'unofficial' if report_type == 'unofficial' else 'official'
        if student.grade_level in [1, 2]:
            template_name = f'management/{template_prefix}_report_card_pdf_template_1_2.html'
        elif student.grade_level == 3:
            template_name = f'management/{template_prefix}_report_card_pdf_template_3.html'
        else:  # Grades 4-8
            template_name = f'management/{template_prefix}_report_card_pdf_template_4_8.html'
        
        # Render the HTML template
        html_content = render_template(
            template_name,
            report_card=report_card,
            student=student_data,
            grades=grades,
            grades_by_quarter=grades_by_quarter,  # Cumulative quarter data
            selected_quarters=selected_quarters,  # So template shows grades for this report's quarter
            attendance=attendance,
            class_objects=class_objects,
            include_attendance=include_attendance,
            include_comments=include_comments,
            generated_date=report_card.generated_at or datetime.utcnow(),
            report_type=report_type,
            template_prefix=template_prefix
        )
        
        # Read CSS file from filesystem and inject it into the HTML
        import os
        css_path = os.path.join(current_app.root_path, 'static', 'report_card_styles.css')
        try:
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
            # Inject CSS into the HTML (replace the link tag with embedded style)
            html_content = html_content.replace(
                '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'report_card_styles.css\') }}">',
                f'<style>{css_content}</style>'
            )
            # Also handle already-rendered link tags
            import re
            html_content = re.sub(
                r'<link rel="stylesheet" href="[^"]*report_card_styles\.css[^"]*">',
                f'<style>{css_content}</style>',
                html_content
            )
        except Exception as e:
            current_app.logger.warning(f'Could not load CSS file: {str(e)}')
        
        # Read logo file and convert to base64 for embedding
        logo_path = os.path.join(current_app.root_path, 'static', 'img', 'clara_logo.png')
        try:
            import base64
            with open(logo_path, 'rb') as f:
                logo_data = base64.b64encode(f.read()).decode('utf-8')
            # Replace logo src with base64 data
            html_content = re.sub(
                r'<img src="[^"]*clara_logo\.png[^"]*"',
                f'<img src="data:image/png;base64,{logo_data}"',
                html_content
            )
        except Exception as e:
            current_app.logger.warning(f'Could not load logo file: {str(e)}')
        
        # Generate PDF
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        # Create response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        filename = f"ReportCard_{student.first_name}_{student.last_name}_{report_card.school_year.name.replace('/', '_')}_{report_card.quarter}.pdf"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except ImportError:
        flash('PDF generation requires WeasyPrint. Please install it: pip install weasyprint', 'error')
        return redirect(url_for('management.view_report_card', report_card_id=report_card_id))
    except Exception as e:
        current_app.logger.error(f'Error generating PDF: {str(e)}')
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('management.view_report_card', report_card_id=report_card_id))



# ============================================================
# Route: /report-cards
# Function: report_cards
# ============================================================

@bp.route('/report-cards')
@login_required
@management_required
def report_cards():
    """Enhanced report cards management with grade categories and filtering."""
    # Get filter parameters
    selected_school_year = request.args.get('school_year', 'All')
    selected_quarter = request.args.get('quarter', 'All')
    selected_student_id = request.args.get('student_id', type=int)
    selected_class_id = request.args.get('class_id', type=int)
    
    # Build query
    query = ReportCard.query
    
    # Apply filters
    if selected_school_year != 'All':
        school_year = SchoolYear.query.filter_by(name=selected_school_year).first()
        if school_year:
            query = query.filter_by(school_year_id=school_year.id)
    
    if selected_quarter != 'All':
        query = query.filter_by(quarter=selected_quarter)
    
    if selected_student_id:
        query = query.filter_by(student_id=selected_student_id)
    
    # Order by most recent first
    report_cards_list = query.order_by(ReportCard.generated_at.desc()).all()
    
    # Get data for filters
    school_years = [sy.name for sy in SchoolYear.query.order_by(SchoolYear.name.desc()).all()]
    all_students = Student.query.order_by(Student.last_name, Student.first_name).all()
    all_classes = Class.query.order_by(Class.name).all()
    quarters = ['All', 'Q1', 'Q2', 'Q3', 'Q4']
    
    return render_template('management/report_cards_enhanced.html', 
                         report_cards=report_cards_list,
                         recent_reports=report_cards_list,
                         school_years=SchoolYear.query.all(),
                         students=Student.query.all(),
                         classes=Class.query.all(),
                         quarters=quarters)



# ============================================================
# Route: /report-cards/category/<category>
# Function: report_cards_by_category
# ============================================================

@bp.route('/report-cards/category/<category>')
@login_required
@management_required
def report_cards_by_category(category):
    """Display students by grade category for report card generation."""
    # Define category mappings
    categories = {
        'k-2': {
            'name': 'Elementary School (K-2)',
            'grades': [0, 1, 2],  # 0 for Kindergarten
            'icon': 'alphabet-uppercase',
            'color': 'primary'
        },
        '3-5': {
            'name': 'Elementary School (3rd-5th)',
            'grades': [3, 4, 5],
            'icon': 'book',
            'color': 'success'
        },
        '6-8': {
            'name': 'Middle School (6th-8th)',
            'grades': [6, 7, 8],
            'icon': 'mortarboard',
            'color': 'warning'
        }
    }
    
    if category not in categories:
        flash('Invalid grade category selected.', 'danger')
        return redirect(url_for('management.report_cards'))
    
    category_info = categories[category]
    
    # Get students in this grade category
    students = Student.query.filter(
        Student.grade_level.in_(category_info['grades'])
    ).order_by(Student.last_name, Student.first_name).all()
    
    return render_template('management/report_cards_category_students.html',
                         students=students,
                         category=category,
                         category_name=category_info['name'],
                         category_icon=category_info['icon'],
                         category_color=category_info['color'],
                         grade_levels=category_info['grades'])



# ============================================================
# Route: /report-cards/delete/<int:report_card_id>', methods=['POST']
# Function: delete_report_card
# ============================================================

@bp.route('/report-cards/delete/<int:report_card_id>', methods=['POST'])
@login_required
@management_required
def delete_report_card(report_card_id):
    """Delete a report card."""
    try:
        report_card = ReportCard.query.get_or_404(report_card_id)
        student_name = f"{report_card.student.first_name} {report_card.student.last_name}" if report_card.student else "Unknown"
        quarter = report_card.quarter
        
        db.session.delete(report_card)
        db.session.commit()
        
        flash(f'Report card deleted successfully for {student_name} ({quarter}).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting report card: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('management.report_cards'))

