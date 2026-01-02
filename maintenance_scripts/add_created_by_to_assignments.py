from app import create_app, db
from sqlalchemy import text

def add_created_by_column():
    app = create_app()
    with app.app_context():
        print("Adding 'created_by' column to 'assignment' and 'group_assignment' tables...")
        
        try:
            # Check if the tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            # Process assignment table
            if 'assignment' in tables:
                columns = inspector.get_columns('assignment')
                created_by_column = next((col for col in columns if col['name'] == 'created_by'), None)
                
                if not created_by_column:
                    with db.engine.connect() as connection:
                        with connection.begin() as transaction:
                            try:
                                connection.execute(text("ALTER TABLE assignment ADD COLUMN created_by INTEGER;"))
                                print("Successfully added 'created_by' column to 'assignment' table.")
                                transaction.commit()
                            except Exception as e:
                                transaction.rollback()
                                print(f"Error adding column to assignment table: {e}")
                                raise
                else:
                    print("Column 'created_by' already exists in 'assignment' table.")
            else:
                print("Table 'assignment' does not exist. Skipping.")
            
            # Process group_assignment table
            if 'group_assignment' in tables:
                columns = inspector.get_columns('group_assignment')
                created_by_column = next((col for col in columns if col['name'] == 'created_by'), None)
                
                if not created_by_column:
                    with db.engine.connect() as connection:
                        with connection.begin() as transaction:
                            try:
                                connection.execute(text("ALTER TABLE group_assignment ADD COLUMN created_by INTEGER;"))
                                print("Successfully added 'created_by' column to 'group_assignment' table.")
                                transaction.commit()
                            except Exception as e:
                                transaction.rollback()
                                print(f"Error adding column to group_assignment table: {e}")
                                raise
                else:
                    print("Column 'created_by' already exists in 'group_assignment' table.")
            else:
                print("Table 'group_assignment' does not exist. Skipping.")
                
        except Exception as e:
            print(f"An error occurred during migration: {e}")

if __name__ == '__main__':
    add_created_by_column()

