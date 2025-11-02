"""
Management routes for quarter grade administration.
Allows administrators to manually trigger grade refreshes.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from decorators import management_required
from utils.auto_refresh_quarter_grades import refresh_all_quarter_grades, refresh_quarter_grades_for_ended_quarters
from models import SchoolYear

bp = Blueprint('quarter_grades_mgmt', __name__)

@bp.route('/quarter-grades/refresh', methods=['POST'])
@login_required
@management_required
def manual_refresh():
    """
    Manually trigger a quarter grade refresh.
    Useful for administrators after making bulk grade changes.
    """
    force = request.form.get('force', 'false').lower() == 'true'
    scope = request.form.get('scope', 'ended')  # 'ended' or 'all'
    
    try:
        if scope == 'all':
            # Refresh all quarters (heavy operation)
            stats = refresh_all_quarter_grades(force=force)
            message = f"Refreshed all quarter grades. Updated: {stats['total_grades_updated']}, Skipped: {stats['total_grades_skipped']}, Errors: {stats['errors']}"
        else:
            # Only refresh recently ended quarters (smart/efficient)
            stats = refresh_quarter_grades_for_ended_quarters()
            message = f"Refreshed grades for {len(stats.get('quarters_processed', []))} recently ended quarters. Updated: {stats.get('total_grades_updated', 0)} grades"
        
        flash(message, 'success')
    except Exception as e:
        flash(f'Error refreshing grades: {str(e)}', 'danger')
    
    return redirect(url_for('management.report_cards'))


@bp.route('/quarter-grades/status')
@login_required
@management_required
def refresh_status():
    """
    Show status of quarter grades system.
    """
    from models import QuarterGrade, AcademicPeriod
    from datetime import date, timedelta
    
    today = date.today()
    
    # Get statistics
    total_records = QuarterGrade.query.count()
    
    # Recently updated (within last 3 hours)
    three_hours_ago = datetime.utcnow() - timedelta(hours=3)
    recent_updates = QuarterGrade.query.filter(
        QuarterGrade.last_calculated >= three_hours_ago
    ).count()
    
    # Stale records (older than 3 hours)
    stale_records = QuarterGrade.query.filter(
        QuarterGrade.last_calculated < three_hours_ago
    ).count()
    
    # Quarters that ended in last 30 days
    thirty_days_ago = today - timedelta(days=30)
    recent_quarters = AcademicPeriod.query.filter(
        AcademicPeriod.period_type == 'quarter',
        AcademicPeriod.end_date >= thirty_days_ago,
        AcademicPeriod.end_date <= today
    ).all()
    
    return jsonify({
        'total_records': total_records,
        'recent_updates': recent_updates,
        'stale_records': stale_records,
        'recent_quarters': [{
            'name': q.name,
            'school_year': q.school_year.name,
            'end_date': q.end_date.isoformat()
        } for q in recent_quarters]
    })

