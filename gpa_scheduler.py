import schedule
import time
import threading
from datetime import datetime
from app import create_app
from models import db, Student, Grade
import json

def update_all_gpas():
    """Update GPA for all students"""
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
                        # Parse the grade data (stored as JSON)
                        grade_data = json.loads(grade.grade_data)
                        score = grade_data.get('score', 0)
                        
                        # Convert percentage to GPA (assuming 90+ = 4.0, 80-89 = 3.0, etc.)
                        if score >= 90:
                            gpa_points = 4.0
                        elif score >= 80:
                            gpa_points = 3.0
                        elif score >= 70:
                            gpa_points = 2.0
                        elif score >= 60:
                            gpa_points = 1.0
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

def start_gpa_scheduler():
    """Start the GPA scheduler"""
    # Schedule GPA updates 3 times every 24 hours
    # At 6:00 AM, 2:00 PM, and 10:00 PM
    schedule.every().day.at("06:00").do(update_all_gpas)
    schedule.every().day.at("14:00").do(update_all_gpas)
    schedule.every().day.at("22:00").do(update_all_gpas)
    
    print("GPA scheduler started. Updates scheduled for 6:00 AM, 2:00 PM, and 10:00 PM daily.")
    
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
    
    # Start the scheduler
    start_gpa_scheduler()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("GPA scheduler stopped.") 