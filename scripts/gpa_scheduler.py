import time
import threading
from datetime import datetime
import json
import os
import sys

# Ensure imports work in production shells (e.g. Render) even when the
# current working directory isn't the project root.
_here = os.path.abspath(os.path.dirname(__file__))
_candidate = os.path.dirname(_here)  # project root is typically parent of /scripts
for _ in range(6):
    if os.path.exists(os.path.join(_candidate, "models.py")) or os.path.exists(os.path.join(_candidate, "app.py")):
        if _candidate not in sys.path:
            sys.path.insert(0, _candidate)
        break
    _next = os.path.dirname(_candidate)
    if _next == _candidate:
        break
    _candidate = _next

# Lazy import to avoid circular dependency - create_app imported inside function
from models import db, Student, Grade

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

def calculate_student_gpa(grades):
    """Calculate GPA for a list of grades"""
    if not grades:
        return 0.0
    
    total_points = 0
    total_assignments = 0
    
    for grade in grades:
        try:
            # Skip voided grades (late enrollment, etc.)
            if hasattr(grade, 'is_voided') and grade.is_voided:
                continue
            
            # Parse the grade data (stored as JSON)
            grade_data = json.loads(grade.grade_data)
            score = grade_data.get('score', 0)
            
            # Convert percentage to GPA with +/- grading points.
            if score >= 93:
                gpa_points = 4.0
            elif score >= 90:
                gpa_points = 3.67
            elif score >= 87:
                gpa_points = 3.33
            elif score >= 83:
                gpa_points = 3.0
            elif score >= 80:
                gpa_points = 2.67
            elif score >= 77:
                gpa_points = 2.33
            elif score >= 73:
                gpa_points = 2.0
            elif score >= 70:
                gpa_points = 1.67
            elif score >= 67:
                gpa_points = 1.33
            elif score >= 63:
                gpa_points = 1.0
            elif score >= 60:
                gpa_points = 0.67
            else:
                gpa_points = 0.0
            
            total_points += gpa_points
            total_assignments += 1
            
        except (json.JSONDecodeError, KeyError, ValueError):
            # Skip invalid grade data
            continue
    
    if total_assignments > 0:
        return round(total_points / total_assignments, 2)
    else:
        return 0.0

def update_all_gpas():
    """Update GPA for all students"""
    # Lazy import to avoid circular dependency
    from app import create_app
    app = create_app()
    with app.app_context():
        print(f"[{datetime.now()}] Starting GPA update for all students...")
        
        students = Student.query.all()
        updated_count = 0
        
        for student in students:
            try:
                # Get all grades for the student
                grades = Grade.query.filter_by(student_id=student.id).all()
                
                if not grades:
                    # No grades yet, GPA should be 0
                    continue
                
                total_points = 0
                total_assignments = 0
                
                for grade in grades:
                    try:
                        # Skip voided grades (late enrollment, etc.)
                        if hasattr(grade, 'is_voided') and grade.is_voided:
                            continue
                        
                        # Parse the grade data (stored as JSON)
                        grade_data = json.loads(grade.grade_data)
                        score = grade_data.get('score', 0)
                        
                        # Convert percentage to GPA with +/- grading points.
                        if score >= 93:
                            gpa_points = 4.0
                        elif score >= 90:
                            gpa_points = 3.67
                        elif score >= 87:
                            gpa_points = 3.33
                        elif score >= 83:
                            gpa_points = 3.0
                        elif score >= 80:
                            gpa_points = 2.67
                        elif score >= 77:
                            gpa_points = 2.33
                        elif score >= 73:
                            gpa_points = 2.0
                        elif score >= 70:
                            gpa_points = 1.67
                        elif score >= 67:
                            gpa_points = 1.33
                        elif score >= 63:
                            gpa_points = 1.0
                        elif score >= 60:
                            gpa_points = 0.67
                        else:
                            gpa_points = 0.0
                        
                        total_points += gpa_points
                        total_assignments += 1
                        
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Skip invalid grade data
                        continue
                
                if total_assignments > 0:
                    gpa = round(total_points / total_assignments, 2)
                    # Update the student's GPA in the database
                    student.gpa = gpa
                    print(f"Student {student.first_name} {student.last_name}: GPA = {gpa}")
                    updated_count += 1
                else:
                    # No assignments, set GPA to 0
                    student.gpa = 0.0
                    print(f"Student {student.first_name} {student.last_name}: GPA = 0.0 (no assignments)")
                    updated_count += 1
                
            except Exception as e:
                print(f"Error updating GPA for student {student.id}: {str(e)}")
        
        # Commit all changes to the database
        db.session.commit()
        print(f"[{datetime.now()}] GPA update completed. Updated {updated_count} students.")


def run_academic_period_reminders_job():
    """Daily: 2 weeks before quarter/semester end — notify students and staff."""
    from app import create_app
    app = create_app()
    with app.app_context():
        from utils.academic_period_reminders import run_academic_period_reminders
        try:
            out = run_academic_period_reminders()
            print(f"[{datetime.now()}] Academic period reminders: {out}")
        except Exception as e:
            print(f"[{datetime.now()}] Academic period reminders error: {e}")


def start_gpa_scheduler():
    """Start the GPA scheduler"""
    if not SCHEDULE_AVAILABLE:
        print("Schedule module not available. GPA scheduler will not start.")
        return None
        
    # Schedule GPA updates 3 times every 24 hours
    # At 6:00 AM, 2:00 PM, and 10:00 PM
    schedule.every().day.at("06:00").do(update_all_gpas)
    schedule.every().day.at("14:00").do(update_all_gpas)
    schedule.every().day.at("22:00").do(update_all_gpas)
    schedule.every().day.at("08:00").do(run_academic_period_reminders_job)
    
    print("GPA scheduler started. GPA updates: 6:00 AM, 2:00 PM, 10:00 PM; academic period reminders: 8:00 AM daily.")
    
    # Run the scheduler in a separate thread
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    return scheduler_thread

if __name__ == "__main__":
    # For testing, run an immediate update
    update_all_gpas()
    
    # Start the scheduler if available
    if SCHEDULE_AVAILABLE:
        start_gpa_scheduler()
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("GPA scheduler stopped.")
    else:
        print("Schedule module not available. Cannot start scheduler.") 