from app import create_app, db # Imports your Flask app factory and SQLAlchemy db object

# Create the app instance
app = create_app()

# Push an application context to make 'app' and 'db' available
with app.app_context():
    # This command creates all tables defined in your models
    # It checks for existing tables, so it's safe to run even if some tables exist.
    db.create_all()

print("Database tables have been created/updated successfully!")
print("You should now have a database file in your project directory (if it wasn't there already),")
print("and all tables should be set up.")