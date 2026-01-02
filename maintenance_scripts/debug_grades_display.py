"""
Debug script to check why grades aren't displaying in the grading interface.
This will show you what's actually stored in the Grade table.

Run on Render Shell:
    python debug_grades_display.py
"""

from app import create_app, db
from models import Grade, Assignment, Student
import json

def debug_grades():
    """Debug grade data to see what's being stored."""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 70)
            print("GRADE DATA DEBUGGING")
            print("=" * 70)
            
            # Get all grades
            all_grades = Grade.query.limit(10).all()  # Just check first 10
            
            print(f"\n📊 Checking first {len(all_grades)} grades...")
            print("\n" + "=" * 70)
            
            for i, grade in enumerate(all_grades, 1):
                print(f"\n🔍 Grade #{i}:")
                print(f"   ID: {grade.id}")
                print(f"   Student ID: {grade.student_id}")
                print(f"   Assignment ID: {grade.assignment_id}")
                
                # Get student name
                student = Student.query.get(grade.student_id)
                if student:
                    print(f"   Student: {student.first_name} {student.last_name}")
                
                # Get assignment name
                assignment = Assignment.query.get(grade.assignment_id)
                if assignment:
                    print(f"   Assignment: {assignment.title}")
                
                # Parse grade data
                print(f"\n   Raw grade_data: {grade.grade_data}")
                
                if grade.grade_data:
                    try:
                        parsed = json.loads(grade.grade_data)
                        print(f"   ✅ Parsed successfully!")
                        print(f"   📊 Contents:")
                        for key, value in parsed.items():
                            print(f"      - {key}: {value}")
                        
                        # Check specific fields
                        score = parsed.get('score')
                        comment = parsed.get('comment')
                        feedback = parsed.get('feedback')
                        
                        print(f"\n   🎯 Score value: {score} (type: {type(score).__name__})")
                        print(f"   💬 Comment: {comment or feedback or 'None'}")
                        
                    except json.JSONDecodeError as e:
                        print(f"   ❌ Failed to parse JSON: {e}")
                else:
                    print(f"   ⚠️  grade_data is empty/null")
                
                print("   " + "-" * 66)
            
            print("\n" + "=" * 70)
            print("✅ DEBUG COMPLETE")
            print("=" * 70)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_grades()


