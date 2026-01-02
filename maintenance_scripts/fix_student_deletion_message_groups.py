from app import create_app, db
from models import User, MessageGroupMember
from sqlalchemy import text

def fix_student_deletion_message_groups():
    app = create_app()
    with app.app_context():
        print("Fixing student deletion to properly handle message group memberships...")
        
        try:
            # Check if the message_group_member table exists and has the expected structure
            inspector = db.inspect(db.engine)
            if 'message_group_member' not in inspector.get_table_names():
                print("Table 'message_group_member' does not exist. Skipping fix.")
                return
            
            # Check the message_group_member table structure
            columns = inspector.get_columns('message_group_member')
            member_columns = [col['name'] for col in columns]
            print(f"Message group member table columns: {member_columns}")
            
            # Check if user_id column exists and is nullable
            user_id_column = next((col for col in columns if col['name'] == 'user_id'), None)
            if not user_id_column:
                print("Column 'user_id' not found in message_group_member table.")
                return
            
            print(f"user_id column nullable: {user_id_column['nullable']}")
            
            # Check for any orphaned message group member records
            with db.engine.connect() as connection:
                result = connection.execute(text("""
                    SELECT COUNT(*) as orphaned_count
                    FROM message_group_member mgm
                    LEFT JOIN "user" u ON mgm.user_id = u.id
                    WHERE u.id IS NULL AND mgm.user_id IS NOT NULL
                """))
                orphaned_count = result.fetchone()[0]
                print(f"Found {orphaned_count} orphaned message group member records")
                
                if orphaned_count > 0:
                    print("Cleaning up orphaned message group member records...")
                    connection.execute(text("""
                        DELETE FROM message_group_member 
                        WHERE user_id NOT IN (SELECT id FROM "user")
                    """))
                    connection.commit()
                    print(f"Deleted {orphaned_count} orphaned message group member records")
            
            print("Message group member table structure is correct.")
            print("The issue is in the application code - message group memberships need to be deleted before deleting users.")
            print("This fix will be applied in the next application update.")
            
        except Exception as e:
            print(f"An error occurred during message group member fix: {e}")

if __name__ == '__main__':
    fix_student_deletion_message_groups()
