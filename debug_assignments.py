from app import create_app, db
from models import Assignment, Class

def debug_assignments():
    app = create_app()
    with app.app_context():
        print("Debugging assignments in database...")
        
        try:
            # Get all assignments
            all_assignments = Assignment.query.all()
            print(f"Total assignments in database: {len(all_assignments)}")
            
            if all_assignments:
                print("\nFirst 10 assignments:")
                for i, assignment in enumerate(all_assignments[:10]):
                    print(f"  {i+1}. ID: {assignment.id}")
                    print(f"     Title: {assignment.title}")
                    print(f"     Due Date: {assignment.due_date}")
                    print(f"     Due Date Type: {type(assignment.due_date)}")
                    print(f"     Class ID: {assignment.class_id}")
                    print(f"     Status: {assignment.status}")
                    print()
            
            # Check for assignments with NULL due dates
            null_due_date_count = Assignment.query.filter(Assignment.due_date.is_(None)).count()
            print(f"Assignments with NULL due dates: {null_due_date_count}")
            
            # Check for assignments with due dates
            with_due_date_count = Assignment.query.filter(Assignment.due_date.isnot(None)).count()
            print(f"Assignments with due dates: {with_due_date_count}")
            
            # Check specific class (ID 6 as shown in the image)
            class_6_assignments = Assignment.query.filter_by(class_id=6).all()
            print(f"\nAssignments for class ID 6: {len(class_6_assignments)}")
            
            for assignment in class_6_assignments:
                print(f"  - ID: {assignment.id}, Title: {assignment.title}")
                print(f"    Due Date: {assignment.due_date}")
                print(f"    Due Date Type: {type(assignment.due_date)}")
                print()
            
            # Check if class 6 exists
            class_6 = Class.query.get(6)
            if class_6:
                print(f"Class 6 exists: {class_6.subject}")
            else:
                print("Class 6 does not exist")
                
        except Exception as e:
            print(f"Error debugging assignments: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_assignments()
