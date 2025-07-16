# Import the factory function from our new app.py
from app import create_app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Run the application
    # The debug setting will be controlled from your config.py file
    app.run(debug=True)
