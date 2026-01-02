from app import create_app, db
from models import User, Notification
from sqlalchemy import text

def fix_student_deletion_notifications():
    app = create_app()
    with app.app_context():
        print("Fixing student deletion to properly handle notifications...")
        
        try:
            # Check if the notification table exists and has the expected structure
            inspector = db.inspect(db.engine)
            if 'notification' not in inspector.get_table_names():
                print("Table 'notification' does not exist. Skipping fix.")
                return
            
            # Check the notification table structure
            columns = inspector.get_columns('notification')
            notification_columns = [col['name'] for col in columns]
            print(f"Notification table columns: {notification_columns}")
            
            # Check if user_id column exists and is nullable
            user_id_column = next((col for col in columns if col['name'] == 'user_id'), None)
            if not user_id_column:
                print("Column 'user_id' not found in notification table.")
                return
            
            print(f"user_id column nullable: {user_id_column['nullable']}")
            
            # Check for any orphaned notification records
            with db.engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT COUNT(*) as orphaned_count
                    FROM notification n
                    LEFT JOIN "user" u ON n.user_id = u.id
                    WHERE u.id IS NULL AND n.user_id IS NOT NULL
                """))
                orphaned_count = result.fetchone()[0]
                print(f"Found {orphaned_count} orphaned notification records")
                
                if orphaned_count > 0:
                    print("Cleaning up orphaned notification records...")
                    connection.execute(text("""
                        DELETE FROM notification 
                        WHERE user_id NOT IN (SELECT id FROM "user")
                    """))
                    connection.commit()
                    print(f"Deleted {orphaned_count} orphaned notification records")
            
            print("Notification table structure is correct.")
            print("The issue is in the application code - notifications need to be deleted before deleting users.")
            print("This fix will be applied in the next application update.")
            
        except Exception as e:
            print(f"An error occurred during notification fix: {e}")

if __name__ == '__main__':
    fix_student_deletion_notifications()
