"""
Database migration script to add google_workspace_email column to User model.
Run this script to update your database schema.
"""

from app import app, db
from models import User
from sqlalchemy import text

def add_google_workspace_email_column():
    """Add google_workspace_email column to User table if it doesn't exist."""
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            if 'google_workspace_email' in columns:
                print("✅ Column 'google_workspace_email' already exists in User table.")
                return
            
            print("Adding 'google_workspace_email' column to User table...")
            
            # Add the column using raw SQL
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE user ADD COLUMN google_workspace_email VARCHAR(120) UNIQUE"
                ))
                conn.commit()
            
            print("✅ Successfully added 'google_workspace_email' column to User table!")
            print("\nNext steps:")
            print("1. Run 'python populate_google_workspace_emails.py' to populate the emails")
            print("2. Or manually update emails via the management dashboard")
            
        except Exception as e:
            print(f"❌ Error adding column: {str(e)}")
            print("\nIf you're using Flask-Migrate, you can also run:")
            print("  flask db migrate -m 'Add google_workspace_email to User model'")
            print("  flask db upgrade")

if __name__ == '__main__':
    add_google_workspace_email_column()

