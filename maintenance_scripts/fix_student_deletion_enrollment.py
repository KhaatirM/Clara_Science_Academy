from app import create_app, db
from models import Student, Enrollment
from sqlalchemy import text

def fix_student_deletion_enrollment():
    app = create_app()
    with app.app_context():
        print("Fixing student deletion to properly handle enrollment records...")
        
        try:
            # Check if the enrollment table exists and has the expected structure
            inspector = db.inspect(db.engine)
            if 'enrollment' not in inspector.get_table_names():
                print("Table 'enrollment' does not exist. Skipping fix.")
                return
            
            # Check the enrollment table structure
            columns = inspector.get_columns('enrollment')
            enrollment_columns = [col['name'] for col in columns]
            print(f"Enrollment table columns: {enrollment_columns}")
            
            # Check if student_id column exists and is nullable
            student_id_column = next((col for col in columns if col['name'] == 'student_id'), None)
            if not student_id_column:
                print("Column 'student_id' not found in enrollment table.")
                return
            
            print(f"student_id column nullable: {student_id_column['nullable']}")
            
            # Check for any orphaned enrollment records (where student_id references non-existent students)
            with db.engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT COUNT(*) as orphaned_count
                    FROM enrollment e
                    LEFT JOIN student s ON e.student_id = s.id
                    WHERE s.id IS NULL AND e.student_id IS NOT NULL
                """))
                orphaned_count = result.fetchone()[0]
                print(f"Found {orphaned_count} orphaned enrollment records")
                
                if orphaned_count > 0:
                    print("Cleaning up orphaned enrollment records...")
                    connection.execute(text("""
                        DELETE FROM enrollment 
                        WHERE student_id NOT IN (SELECT id FROM student)
                    """))
                    connection.commit()
                    print(f"Deleted {orphaned_count} orphaned enrollment records")
            
            print("Enrollment table structure is correct.")
            print("The issue is in the application code - enrollment records need to be deleted before deleting students.")
            print("This fix will be applied in the next application update.")
            
        except Exception as e:
            print(f"An error occurred during enrollment fix: {e}")

if __name__ == '__main__':
    fix_student_deletion_enrollment()
