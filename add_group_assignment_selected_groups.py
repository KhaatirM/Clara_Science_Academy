from app import create_app, db
from models import GroupAssignment
from sqlalchemy import text

def add_selected_group_ids_column():
    app = create_app()
    with app.app_context():
        print("Adding 'selected_group_ids' column to 'group_assignment' table...")
        
        try:
            # Check if the table exists
            inspector = db.inspect(db.engine)
            if 'group_assignment' not in inspector.get_table_names():
                print("Table 'group_assignment' does not exist. Skipping migration.")
                return
            
            # Check if the column already exists
            columns = inspector.get_columns('group_assignment')
            selected_group_ids_column = next((col for col in columns if col['name'] == 'selected_group_ids'), None)
            
            if selected_group_ids_column:
                print("Column 'selected_group_ids' already exists. No action needed.")
                return
            
            with db.engine.connect() as connection:
                # Start a transaction
                with connection.begin() as transaction:
                    try:
                        # Add the new column
                        connection.execute(text("ALTER TABLE group_assignment ADD COLUMN selected_group_ids TEXT;"))
                        print("Successfully added 'selected_group_ids' column to 'group_assignment' table.")
                        
                        transaction.commit()
                        print("Transaction committed successfully.")
                    except Exception as e:
                        transaction.rollback()
                        print(f"Transaction rolled back due to error: {e}")
                        raise
            
            # Verify the change
            columns = inspector.get_columns('group_assignment')
            selected_group_ids_column = next((col for col in columns if col['name'] == 'selected_group_ids'), None)
            if selected_group_ids_column:
                print("Verification successful: 'selected_group_ids' column has been added.")
            else:
                print("Verification failed: 'selected_group_ids' column was not found.")
                
        except Exception as e:
            print(f"An error occurred during migration: {e}")

if __name__ == '__main__':
    add_selected_group_ids_column()
