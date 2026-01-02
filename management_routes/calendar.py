"""
Calendar routes for management users.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, Response, abort, jsonify
from flask_login import login_required, current_user
from decorators import management_required
from models import (
    db, CalendarEvent, TeacherWorkDay, SchoolBreak, SchoolYear, AcademicPeriod
)
from datetime import datetime, timedelta, date
import os
import json

bp = Blueprint('calendar', __name__)

def get_academic_dates_for_calendar(year, month):
    """Get academic dates (quarters, semesters, holidays) for a specific month/year."""
    academic_dates = []
    
    # Get the active school year
    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        return academic_dates
    
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
            event_type = f"{period.period_type}_start"
            academic_dates.append({
                'day': period.start_date.day,
                'title': f"{period.name} Start",
                'category': f"{period.period_type.title()}",
                'type': event_type
            })
        
        # Add end date event
        if period.end_date.month == month:
            event_type = f"{period.period_type}_end"
            academic_dates.append({
                'day': period.end_date.day,
                'title': f"{period.name} End",
                'category': f"{period.period_type.title()}",
                'type': event_type
            })
    
    # Get calendar events for this month
    calendar_events = CalendarEvent.query.filter(
        CalendarEvent.school_year_id == active_year.id,
        CalendarEvent.start_date <= end_of_month,
        CalendarEvent.end_date >= start_of_month
    ).all()
    
    for event in calendar_events:
        if event.start_date.month == month:
            event_type = event.event_type if event.event_type else 'other_event'
            academic_dates.append({
                'day': event.start_date.day,
                'title': event.name,
                'category': event.event_type.replace('_', ' ').title() if event.event_type else 'Other Event',
                'type': event_type
            })
    
    # Get teacher work days for this month
    teacher_work_days = TeacherWorkDay.query.filter(
        TeacherWorkDay.school_year_id == active_year.id,
        TeacherWorkDay.date >= start_of_month,
        TeacherWorkDay.date <= end_of_month
    ).all()
    
    for work_day in teacher_work_days:
        if work_day.date.month == month:
            short_title = work_day.title
            if "Professional Development" in short_title:
                short_title = "PD Day"
            elif "First Day" in short_title:
                short_title = "First Day"
            
            academic_dates.append({
                'day': work_day.date.day,
                'title': short_title,
                'category': 'Teacher Work Day',
                'type': 'teacher_work_day'
            })
    
    # Get school breaks for this month
    school_breaks = SchoolBreak.query.filter(
        SchoolBreak.school_year_id == active_year.id,
        SchoolBreak.start_date <= end_of_month,
        SchoolBreak.end_date >= start_of_month
    ).all()
    
    for school_break in school_breaks:
        if (school_break.start_date.month == month or 
            school_break.end_date.month == month or
            (school_break.start_date.month < month and school_break.end_date.month > month)):
            
            if school_break.start_date.month == month:
                short_name = school_break.name
                if "Thanksgiving" in short_name:
                    short_name = "Thanksgiving"
                elif "Winter" in short_name:
                    short_name = "Winter"
                elif "Spring" in short_name:
                    short_name = "Spring"
                
                academic_dates.append({
                    'day': school_break.start_date.day,
                    'title': f"{short_name} Start",
                    'category': school_break.break_type,
                    'type': 'school_break_start'
                })
            
            if school_break.end_date.month == month:
                short_name = school_break.name
                if "Thanksgiving" in short_name:
                    short_name = "Thanksgiving"
                elif "Winter" in short_name:
                    short_name = "Winter"
                elif "Spring" in short_name:
                    short_name = "Spring"
                
                academic_dates.append({
                    'day': school_break.end_date.day,
                    'title': f"{short_name} End",
                    'category': school_break.break_type,
                    'type': 'school_break_end'
                })
    
    return academic_dates


# ============================================================
# Route: /calendar
# Function: calendar
# ============================================================

@bp.route('/calendar')
@login_required
@management_required
def calendar():
    """School calendar view"""
    from datetime import datetime, timedelta
    import calendar as cal
    
    # Get current month/year from query params or use current date
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    # Calculate previous and next month
    current_date = datetime(year, month, 1)
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)
    
    # Create calendar data
    cal_obj = cal.monthcalendar(year, month)
    month_name = datetime(year, month, 1).strftime('%B')
    
    # Get academic dates for this month
    academic_dates = get_academic_dates_for_calendar(year, month)
    
    # Simple calendar data structure
    calendar_data = {
        'month_name': month_name,
        'year': year,
        'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'weeks': []
    }
    
    # Convert calendar to our format
    for week in cal_obj:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'day_num': '', 'is_current_month': False, 'is_today': False, 'events': []})
            else:
                is_today = (day == datetime.now().day and month == datetime.now().month and year == datetime.now().year)
                
                # Get events for this day
                day_events = []
                for academic_date in academic_dates:
                    if academic_date['day'] == day:
                        day_events.append({
                            'title': academic_date['title'],
                            'category': academic_date['category']
                        })
                
                week_data.append({'day_num': day, 'is_current_month': True, 'is_today': is_today, 'events': day_events})
        calendar_data['weeks'].append(week_data)
    
    # Get school years for the academic calendar management tab
    school_years = SchoolYear.query.order_by(SchoolYear.start_date.desc()).all()
    
    # Get active school year and add academic periods and calendar events data
    active_school_year = SchoolYear.query.filter_by(is_active=True).first()
    
    # Add academic periods to each school year
    for year in school_years:
        year.academic_periods = AcademicPeriod.query.filter_by(school_year_id=year.id, is_active=True).all()
        year.calendar_events = CalendarEvent.query.filter_by(school_year_id=year.id).all()
        if year.start_date and year.end_date:
            year.total_days = (year.end_date - year.start_date).days
    
    return render_template('shared/calendar.html', 
                         calendar_data=calendar_data,
                         prev_month=prev_month,
                         next_month=next_month,
                         school_years=school_years,
                         active_school_year=active_school_year,
                         month_name=month_name,
                         year=year,
                         section='calendar',
                         active_tab='calendar')



# ============================================================
# Route: /calendar/add-event', methods=['POST']
# Function: add_calendar_event
# ============================================================

@bp.route('/calendar/add-event', methods=['POST'])
@login_required
@management_required
def add_calendar_event():
    """Add a new calendar event"""
    flash('Calendar event functionality will be implemented soon!', 'info')
    return redirect(url_for('management.calendar'))



# ============================================================
# Route: /calendar/delete-event/<int:event_id>', methods=['POST']
# Function: delete_calendar_event
# ============================================================

@bp.route('/calendar/delete-event/<int:event_id>', methods=['POST'])
@login_required
@management_required
def delete_calendar_event(event_id):
    """Delete a calendar event"""
    flash('Calendar event deletion will be implemented soon!', 'info')
    return redirect(url_for('management.calendar'))


# Teacher Work Day Management Routes


# ============================================================
# Route: /calendar/school-breaks
# Function: school_breaks
# ============================================================

@bp.route('/calendar/school-breaks')
@login_required
@management_required
def school_breaks():
    """View and manage school breaks"""
    # Get active school year
    active_year = SchoolYear.query.filter_by(is_active=True).first()
    if not active_year:
        flash('No active school year found.', 'warning')
        return redirect(url_for('management.calendar'))
    
    # Get all school breaks for the active school year
    breaks = SchoolBreak.query.filter_by(school_year_id=active_year.id).order_by(SchoolBreak.start_date).all()
    
    return render_template('management/management_school_breaks.html',
                         breaks=breaks,
                         school_year=active_year,
                         section='calendar',
                         active_tab='calendar')




# ============================================================
# Route: /calendar/school-breaks/add', methods=['POST']
# Function: add_school_break
# ============================================================

@bp.route('/calendar/school-breaks/add', methods=['POST'])
@login_required
@management_required
def add_school_break():
    """Add a school break"""
    try:
        name = request.form.get('name', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        break_type = request.form.get('break_type', 'Vacation')
        description = request.form.get('description', '').strip()
        
        if not all([name, start_date_str, end_date_str]):
            flash('Name, start date, and end date are required.', 'danger')
            return redirect(url_for('management.school_breaks'))
        
        # Get active school year
        active_year = SchoolYear.query.filter_by(is_active=True).first()
        if not active_year:
            flash('No active school year found.', 'danger')
            return redirect(url_for('management.school_breaks'))
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        if start_date > end_date:
            flash('Start date must be before or equal to end date.', 'danger')
            return redirect(url_for('management.school_breaks'))
        
        # Check if break already exists for this date range
        existing = SchoolBreak.query.filter(
            SchoolBreak.school_year_id == active_year.id,
            SchoolBreak.start_date <= end_date,
            SchoolBreak.end_date >= start_date
        ).first()
        
        if not existing:
            school_break = SchoolBreak(
                school_year_id=active_year.id,
                name=name,
                start_date=start_date,
                end_date=end_date,
                break_type=break_type,
                description=description
            )
            db.session.add(school_break)
            db.session.commit()
            flash('School break added successfully.', 'success')
        else:
            flash('A break already exists for this date range.', 'warning')
        
    except ValueError:
        flash('Invalid date format. Use YYYY-MM-DD format.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding school break: {str(e)}', 'danger')
    
    return redirect(url_for('management.school_breaks'))




# ============================================================
# Route: /calendar/school-breaks/delete/<int:break_id>', methods=['POST']
# Function: delete_school_break
# ============================================================

@bp.route('/calendar/school-breaks/delete/<int:break_id>', methods=['POST'])
@login_required
@management_required
def delete_school_break(break_id):
    """Delete a school break"""
    try:
        school_break = SchoolBreak.query.get_or_404(break_id)
        db.session.delete(school_break)
        db.session.commit()
        flash('School break deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting school break: {str(e)}', 'danger')
    
    return redirect(url_for('management.school_breaks'))




# ============================================================
# Route: /upload-calendar-pdf', methods=['POST']
# Function: upload_calendar_pdf
# ============================================================

@bp.route('/upload-calendar-pdf', methods=['POST'])
@login_required
@management_required
def upload_calendar_pdf():
    """Upload and process a school calendar PDF."""
    # PDF processing temporarily disabled due to import issues
    flash('PDF processing is temporarily unavailable. Please check back later.', 'warning')
    return redirect(url_for('management.calendar'))


# def process_calendar_pdf(filepath):
#     """Process a PDF calendar to extract important dates."""
#     # PDF processing temporarily disabled due to import issues
#     return {}

# def extract_school_year_dates(text_content, text_lower):
#     """Extract school year start and end dates."""
#     # PDF processing temporarily disabled due to import issues
#     return {'school_year_start': None, 'school_year_end': None}

# def extract_academic_periods(text_content, text_lower):
#     """Extract quarter and semester dates."""
#     # PDF processing temporarily disabled due to import issues
#     return {'quarters': [], 'semesters': []}

# def extract_holidays_and_events(text_content, text_lower):
#     """Extract holidays and special event dates."""
#     # PDF processing temporarily disabled due to import issues
#     return {'holidays': [], 'parent_teacher_conferences': [], 'early_dismissal': [], 'no_school': []}

