from app import create_app, db
from sqlalchemy import text

def add_created_by_column():
    app = create_app()
    with app.app_context():
        print("Adding 'created_by' column to 'assignment' table...")
        
        try:
            # Check if the table exists
            inspector = db.inspect(db.engine)
            if 'assignment' not in inspector.get_table_names():
                print("Table 'assignment' does not exist. Skipping migration.")
                return
            
            # Check if the column already exists
            columns = inspector.get_columns('assignment')
            created_by_column = next((col for col in columns if col['name'] == 'created_by'), None)
            
            if created_by_column:
                print("Column 'created_by' already exists. No action needed.")
                return
            
            with db.engine.connect() as connection:
                # Start a transaction
                with connection.begin() as transaction:
                    try:
                        # Add the new column (nullable since existing assignments won't have a creator)
                        connection.execute(text("ALTER TABLE assignment ADD COLUMN created_by INTEGER;"))
                        print("Successfully added 'created_by' column to 'assignment' table.")
                        
                        # Add foreign key constraint
                        try:
                            connection.execute(text("ALTER TABLE assignment ADD CONSTRAINT assignment_created_by_fkey FOREIGN KEY (created_by) REFERENCES \"user\"(id);"))
                            print("Successfully added foreign key constraint for 'created_by' column.")
                        except Exception as fk_error:
                            print(f"Warning: Could not add foreign key constraint: {fk_error}")
                            print("Column added but foreign key constraint was not created.")
                        
                        transaction.commit()
                        print("Transaction committed successfully.")
                    except Exception as e:
                        transaction.rollback()
                        print(f"Transaction rolled back due to error: {e}")
                        raise
            
            # Verify the change
            columns = inspector.get_columns('assignment')
            created_by_column = next((col for col in columns if col['name'] == 'created_by'), None)
            if created_by_column:
                print("Verification successful: 'created_by' column has been added.")
            else:
                print("Verification failed: 'created_by' column was not found.")
                
        except Exception as e:
            print(f"An error occurred during migration: {e}")

if __name__ == '__main__':
    add_created_by_column()

