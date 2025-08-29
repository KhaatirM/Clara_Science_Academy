from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Simple in-memory storage for testing
users = {
    'tech1': {'password_hash': generate_password_hash('password123'), 'role': 'Tech'},
    'admin1': {'password_hash': generate_password_hash('password123'), 'role': 'Director'},
    'student1': {'password_hash': generate_password_hash('password123'), 'role': 'Student'}
}

maintenance_mode = None

class User(UserMixin):
    def __init__(self, username, role):
        self.id = username
        self.username = username
        self.role = role

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id, users[user_id]['role'])
    return None

@app.route('/')
def home():
    global maintenance_mode
    
    if maintenance_mode and maintenance_mode['end_time'] > datetime.now():
        # Allow tech users to bypass maintenance mode
        if current_user.is_authenticated and current_user.role in ['Tech', 'IT Support', 'Director']:
            return render_template('home_simple.html')
        
        # Show maintenance page for non-tech users
        return render_template('maintenance_simple.html', maintenance=maintenance_mode)
    
    return render_template('home_simple.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    global maintenance_mode
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users and check_password_hash(users[username]['password_hash'], password):
            user = User(username, users[username]['role'])
            login_user(user)
            
            # Check if user is tech and maintenance is active
            if maintenance_mode and maintenance_mode['end_time'] > datetime.now():
                if user.role in ['Tech', 'IT Support', 'Director']:
                    flash('Welcome back! You have access during maintenance mode.', 'info')
                else:
                    flash('System is under maintenance. Only tech users can access.', 'warning')
                    logout_user()
                    return redirect(url_for('login'))
            
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login_simple.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Tech':
        return render_template('tech_dashboard_simple.html')
    elif current_user.role == 'Director':
        return render_template('admin_dashboard_simple.html')
    else:
        return render_template('student_dashboard_simple.html')

@app.route('/maintenance/start', methods=['POST'])
@login_required
def start_maintenance():
    global maintenance_mode
    
    if current_user.role not in ['Tech', 'Director']:
        flash('Only tech users can start maintenance mode.', 'danger')
        return redirect(url_for('dashboard'))
    
    duration_minutes = int(request.form.get('duration_minutes', 60))
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    maintenance_mode = {
        'is_active': True,
        'start_time': start_time,
        'end_time': end_time,
        'duration_minutes': duration_minutes,
        'reason': 'Test maintenance',
        'allow_tech_access': True
    }
    
    flash(f'Maintenance mode activated for {duration_minutes} minutes.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/maintenance/stop', methods=['POST'])
@login_required
def stop_maintenance():
    global maintenance_mode
    
    if current_user.role not in ['Tech', 'Director']:
        flash('Only tech users can stop maintenance mode.', 'danger')
        return redirect(url_for('dashboard'))
    
    maintenance_mode = None
    flash('Maintenance mode deactivated.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)

