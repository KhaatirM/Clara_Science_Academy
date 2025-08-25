from flask_login import UserMixin
from datetime import datetime
from extensions import db

class User(db.Model, UserMixin):
    """
    User model for authentication and roles. This will store login credentials
    for all types of users (students, teachers, directors, etc.).
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    # Increase the length of the password_hash column
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False) # e.g., 'Student', 'Teacher', 'Director'

    # This links the User model to a specific student or teacher record.
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    teacher_staff_id = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.role}')"


class Student(db.Model):
    """
    Model for storing student information.
    """
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(20)) # Storing as string as per our previous finding
    grade_level = db.Column(db.Integer)  # Changed to Integer to match app.py expectations
    student_id = db.Column(db.String(50), nullable=True, unique=True)
    address = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    transcript_filename = db.Column(db.String(255), nullable=True)
    previous_school = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    medical_concerns = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Parent 1 information
    parent1_first_name = db.Column(db.String(100), nullable=True)
    parent1_last_name = db.Column(db.String(100), nullable=True)
    parent1_email = db.Column(db.String(120), nullable=True)
    parent1_phone = db.Column(db.String(20), nullable=True)
    parent1_relationship = db.Column(db.String(20), nullable=True)  # Mother/Father
    
    # Parent 2 information
    parent2_first_name = db.Column(db.String(100), nullable=True)
    parent2_last_name = db.Column(db.String(100), nullable=True)
    parent2_email = db.Column(db.String(120), nullable=True)
    parent2_phone = db.Column(db.String(20), nullable=True)
    parent2_relationship = db.Column(db.String(20), nullable=True)  # Mother/Father
    
    # Emergency contact
    emergency_first_name = db.Column(db.String(100), nullable=True)
    emergency_last_name = db.Column(db.String(100), nullable=True)
    emergency_email = db.Column(db.String(120), nullable=True)
    emergency_phone = db.Column(db.String(20), nullable=True)
    emergency_relationship = db.Column(db.String(50), nullable=True)  # Parent, Guardian, etc.
    
    # Address fields
    street = db.Column(db.String(200), nullable=True)
    apt_unit = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)
    
    # GPA field
    gpa = db.Column(db.Float, default=0.0)

    # Relationship to the User model
    user = db.relationship('User', backref='student_profile', uselist=False)
    
    # Relationship to report cards
    report_cards = db.relationship('ReportCard', backref='student', lazy=True)

    def generate_student_id(self):
        """Generate Student ID based on state abbreviation and DOB"""
        if not self.state or not self.dob:
            return None
        
        # State abbreviation mapping
        state_abbreviations = {
            'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
            'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
            'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
            'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
            'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
            'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
            'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
            'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
            'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
            'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
        }
        
        # Get state abbreviation
        state_abbr = state_abbreviations.get(self.state, self.state[:2].upper())
        
        # Parse DOB (handle both MM/DD/YYYY and YYYY-MM-DD)
        try:
            from datetime import datetime
            dob = self.dob
            if '-' in dob:
                # Format: YYYY-MM-DD
                dt = datetime.strptime(dob, '%Y-%m-%d')
            elif '/' in dob:
                # Format: MM/DD/YYYY
                dt = datetime.strptime(dob, '%m/%d/%Y')
            else:
                return None
            month = str(dt.month).zfill(2)
            day = str(dt.day).zfill(2)
            year = str(dt.year)[-2:]
            return f"{state_abbr}{month}{day}{year}"
        except Exception as e:
            return None
    
    def __repr__(self):
        return f"Student('{self.first_name} {self.last_name}', Grade: '{self.grade_level}')"


class TeacherStaff(db.Model):
    """
    Model for storing information about teachers and other staff.
    """
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_initial = db.Column(db.String(1), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    staff_id = db.Column(db.String(50), nullable=True, unique=True)
    
    # Personal information
    dob = db.Column(db.String(20), nullable=True)  # Date of birth
    staff_ssn = db.Column(db.String(20), nullable=True)  # Social Security Number
    
    # Professional information
    assigned_role = db.Column(db.String(100), nullable=True)  # Assigned role (e.g., Director, Math Teacher)
    hire_date = db.Column(db.String(20), nullable=True)  # Storing as string like DOB
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    subject = db.Column(db.String(200), nullable=True)  # Primary subject(s) taught
    employment_type = db.Column(db.String(20), nullable=True)  # Full Time, Part Time
    grades_taught = db.Column(db.Text, nullable=True)  # JSON string of grades taught
    
    # File uploads
    resume_filename = db.Column(db.String(255), nullable=True)
    other_document_filename = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    
    # Emergency contact information
    emergency_first_name = db.Column(db.String(100), nullable=True)
    emergency_last_name = db.Column(db.String(100), nullable=True)
    emergency_email = db.Column(db.String(120), nullable=True)
    emergency_phone = db.Column(db.String(20), nullable=True)
    emergency_relationship = db.Column(db.String(50), nullable=True)  # Spouse, Parent, etc.
    
    # Address fields
    street = db.Column(db.String(200), nullable=True)
    apt_unit = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Relationship to the User model
    user = db.relationship('User', backref='teacher_staff_profile', uselist=False)

    def generate_staff_id(self):
        """Generate Staff ID based on department abbreviation and hire date"""
        if not self.department or not self.hire_date:
            return None
        
        # Department abbreviation mapping
        department_abbreviations = {
            'Mathematics': 'MATH', 'Science': 'SCI', 'English': 'ENG', 'History & Social Studies': 'HIST',
            'Physical Education & Health': 'PE', 'Music & Arts': 'ARTS', 'Computer Science & Technology': 'TECH',
            'Administration': 'ADMIN', 'Counseling': 'COUNSEL',
            'Special Education': 'SPED', 'Foreign Language': 'LANG',
            'Business': 'BUS', 'Director': 'DIR', 'School Administrator': 'ADMIN'
        }
        
        # Get department abbreviation
        dept_abbr = department_abbreviations.get(self.department, self.department[:4].upper())
        
        # Parse hire date (handle both MM/DD/YYYY and YYYY-MM-DD)
        try:
            from datetime import datetime
            hire_date = self.hire_date
            if '-' in hire_date:
                # Format: YYYY-MM-DD
                dt = datetime.strptime(hire_date, '%Y-%m-%d')
            elif '/' in hire_date:
                # Format: MM/DD/YYYY
                dt = datetime.strptime(hire_date, '%m/%d/%Y')
            else:
                return None
            month = str(dt.month).zfill(2)
            day = str(dt.day).zfill(2)
            year = str(dt.year)[-2:]
            return f"{dept_abbr}{month}{day}{year}"
        except Exception as e:
            return None

    def __repr__(self):
        return f"TeacherStaff('{self.first_name} {self.last_name}')"


class SchoolYear(db.Model):
    """
    Model for storing school year information.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"SchoolYear('{self.name}')"


class AcademicPeriod(db.Model):
    """
    Model for storing academic periods (quarters and semesters).
    """
    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    name = db.Column(db.String(20), nullable=False)  # e.g., 'Q1', 'Q2', 'Q3', 'Q4', 'S1', 'S2'
    period_type = db.Column(db.String(10), nullable=False)  # 'quarter' or 'semester'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    school_year = db.relationship('SchoolYear', backref='academic_periods', lazy=True)
    
    def __repr__(self):
        return f"AcademicPeriod('{self.name}' - {self.period_type})"


class CalendarEvent(db.Model):
    """
    Model for storing calendar events extracted from uploaded PDFs.
    """
    __tablename__ = 'calendar_events'
    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # 'holiday', 'break', 'professional_development', etc.
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # For single-day events, same as start_date
    description = db.Column(db.Text, nullable=True)
    pdf_filename = db.Column(db.String(255), nullable=True)  # Original PDF filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    school_year = db.relationship('SchoolYear', backref='calendar_events', lazy=True)
    
    def __repr__(self):
        return f"CalendarEvent('{self.name}' - {self.event_type} on {self.start_date})"


class TeacherWorkDay(db.Model):
    """
    Model for storing teacher work days with attendance requirements.
    """
    __tablename__ = 'teacher_work_days'
    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    attendance_requirement = db.Column(db.String(20), nullable=False, default='Mandatory')  # 'Mandatory', 'Optional'
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    school_year = db.relationship('SchoolYear', backref='teacher_work_days', lazy=True)
    
    def __repr__(self):
        return f"TeacherWorkDay('{self.title}' - {self.attendance_requirement} on {self.date})"


class SchoolBreak(db.Model):
    """
    Model for storing school breaks and vacations.
    """
    __tablename__ = 'school_breaks'
    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    break_type = db.Column(db.String(50), nullable=False, default='Vacation')  # 'Vacation', 'Holiday', 'Professional Development'
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    school_year = db.relationship('SchoolYear', backref='school_breaks', lazy=True)
    
    def __repr__(self):
        return f"SchoolBreak('{self.name}' - {self.break_type} from {self.start_date} to {self.end_date})"


class Class(db.Model):
    """
    Model for storing class information.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)

    teacher = db.relationship('TeacherStaff', backref='classes', lazy=True)
    school_year = db.relationship('SchoolYear', backref='classes', lazy=True)

    def __repr__(self):
        return f"Class('{self.name}', Subject: '{self.subject}')"


class ClassSchedule(db.Model):
    """
    Model for storing class schedule information.
    """
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 1=Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    class_info = db.relationship('Class', backref='schedules')
    
    def __repr__(self):
        return f"ClassSchedule(Class: {self.class_id}, Day: {self.day_of_week}, Time: {self.start_time}-{self.end_time})"


class Assignment(db.Model):
    """
    Model for storing assignment information.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    quarter = db.Column(db.String(10), nullable=False)
    semester = db.Column(db.String(10), nullable=True)  # S1 or S2
    academic_period_id = db.Column(db.Integer, db.ForeignKey('academic_period.id'), nullable=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # File attachment fields
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_original_filename = db.Column(db.String(255), nullable=True)
    attachment_file_path = db.Column(db.String(500), nullable=True)
    attachment_file_size = db.Column(db.Integer, nullable=True)
    attachment_mime_type = db.Column(db.String(100), nullable=True)

    class_info = db.relationship('Class', backref='assignments', lazy=True)
    school_year = db.relationship('SchoolYear', backref='assignments', lazy=True)
    academic_period = db.relationship('AcademicPeriod', backref='assignments', lazy=True)

    def __repr__(self):
        return f"Assignment('{self.title}', Class: {self.class_id})"


class Submission(db.Model):
    """
    Model for storing student assignment submissions.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(500), nullable=True)
    comments = db.Column(db.Text, nullable=True)

    student = db.relationship('Student', backref='submissions', lazy=True)
    assignment = db.relationship('Assignment', backref='submissions', lazy=True)

    def __repr__(self):
        return f"Submission(Student: {self.student_id}, Assignment: {self.assignment_id})"


class Grade(db.Model):
    """
    Model for storing student grades.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    grade_data = db.Column(db.Text, nullable=False)  # JSON string containing score and comments
    graded_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='grades', lazy=True)
    assignment = db.relationship('Assignment', backref='grades', lazy=True)

    def __repr__(self):
        return f"Grade(Student: {self.student_id}, Assignment: {self.assignment_id})"


class ReportCard(db.Model):
    """
    Model for storing report card records.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    quarter = db.Column(db.String(10), nullable=False)
    grades_details = db.Column(db.Text, nullable=True)  # JSON string containing calculated grades
    generated_at = db.Column(db.DateTime, nullable=True)
    
    school_year = db.relationship('SchoolYear', backref='report_cards', lazy=True)

    def __repr__(self):
        return f"ReportCard(Student ID: {self.student_id}, Quarter: {self.quarter})"


class Announcement(db.Model):
    """
    Model for storing announcements sent by teachers or administrators.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Targeting: 'class', 'all_students', 'all_staff', 'all'
    target_group = db.Column(db.String(32), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)
    # New fields for enhanced announcements
    is_important = db.Column(db.Boolean, default=False)  # Requires read receipts
    requires_confirmation = db.Column(db.Boolean, default=False)  # Users must confirm they read it
    rich_content = db.Column(db.Text, nullable=True)  # For formatted content
    expires_at = db.Column(db.DateTime, nullable=True)  # Auto-expire announcements
    # Optionally, you could add a field for staff_id if you want to target specific staff

    sender = db.relationship('User', backref='announcements_sent', lazy=True)
    class_info = db.relationship('Class', backref='announcements', lazy=True)

    def __repr__(self):
        return f"Announcement('{self.title}', Target: '{self.target_group}')"


class Notification(db.Model):
    """
    Model for storing per-user notifications (students, teachers, etc.).
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(32), nullable=False)  # e.g., 'announcement', 'assignment', 'grade', 'message', etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)  # Optional URL for more info/action
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    # New field to link to actual message
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)

    user = db.relationship('User', backref='notifications', lazy=True)
    linked_message = db.relationship('Message', backref='notifications')

    def __repr__(self):
        return f"Notification(User: {self.user_id}, Type: {self.type}, Title: {self.title})"


class MaintenanceMode(db.Model):
    """
    Model for tracking maintenance mode sessions.
    """
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=False)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    initiated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    maintenance_message = db.Column(db.Text, nullable=True)
    allow_tech_access = db.Column(db.Boolean, default=True)  # Allow tech users to still access
    
    initiator = db.relationship('User', backref='maintenance_sessions', lazy=True)

    def __repr__(self):
        return f"MaintenanceMode(Active: {self.is_active}, Start: {self.start_time}, End: {self.end_time})"


class ActivityLog(db.Model):
    """
    Model for tracking user activities for auditing and security purposes.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='activity_logs', lazy=True)
    
    def __repr__(self):
        return f"ActivityLog(User: {self.user_id}, Action: {self.action}, Success: {self.success})"

class StudentGoal(db.Model):
    """
    Model for tracking student academic goals for each class.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    target_grade = db.Column(db.Float, nullable=False)  # Target percentage (e.g., 90.0 for 90%)
    target_letter = db.Column(db.String(2), nullable=True)  # Target letter grade (e.g., 'A')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = db.relationship('Student', backref='goals', lazy=True)
    class_info = db.relationship('Class', backref='student_goals', lazy=True)
    
    def __repr__(self):
        return f"StudentGoal(Student: {self.student_id}, Class: {self.class_id}, Target: {self.target_grade}%)"


class Message(db.Model):
    """
    Model for direct messages between users.
    """
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='direct')  # 'direct', 'group', 'announcement'
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # For group messages
    group_id = db.Column(db.Integer, db.ForeignKey('message_group.id'), nullable=True)
    
    # For announcements
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=True)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    group = db.relationship('MessageGroup', backref='messages')
    announcement = db.relationship('Announcement', backref='messages')
    
    def __repr__(self):
        return f"Message(Sender: {self.sender_id}, Recipient: {self.recipient_id}, Type: {self.message_type})"


class MessageGroup(db.Model):
    """
    Model for group messaging (class chats, etc.).
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    group_type = db.Column(db.String(20), default='class')  # 'class', 'staff', 'parent'
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    class_info = db.relationship('Class', backref='message_groups')
    creator = db.relationship('User', backref='created_groups')
    
    def __repr__(self):
        return f"MessageGroup('{self.name}', Type: {self.group_type})"


class MessageGroupMember(db.Model):
    """
    Model for tracking group members.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('message_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)  # For group admins
    is_muted = db.Column(db.Boolean, default=False)  # For muting notifications
    
    group = db.relationship('MessageGroup', backref='members')
    user = db.relationship('User', backref='group_memberships')
    
    def __repr__(self):
        return f"MessageGroupMember(Group: {self.group_id}, User: {self.user_id})"


class MessageAttachment(db.Model):
    """
    Model for file attachments in messages.
    """
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    message = db.relationship('Message', backref='attachments')
    
    def __repr__(self):
        return f"MessageAttachment('{self.original_filename}', Message: {self.message_id})"


class AnnouncementReadReceipt(db.Model):
    """
    Model for tracking who has read important announcements.
    """
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    announcement = db.relationship('Announcement', backref='read_receipts')
    user = db.relationship('User', backref='announcement_reads')
    
    def __repr__(self):
        return f"AnnouncementReadReceipt(Announcement: {self.announcement_id}, User: {self.user_id})"


class ScheduledAnnouncement(db.Model):
    """
    Model for announcements scheduled to be sent at a future date.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_group = db.Column(db.String(32), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)
    scheduled_for = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    
    sender = db.relationship('User', backref='scheduled_announcements')
    class_info = db.relationship('Class', backref='scheduled_announcements')

    def __repr__(self):
        return f"ScheduledAnnouncement('{self.title}', Scheduled: {self.scheduled_for})"


class Enrollment(db.Model):
    """
    Model for tracking student enrollment in classes.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    dropped_at = db.Column(db.DateTime, nullable=True)
    
    student = db.relationship('Student', backref='enrollments')
    class_info = db.relationship('Class', backref='enrollments')
    
    def __repr__(self):
        return f"Enrollment(Student: {self.student_id}, Class: {self.class_id})"


class BugReport(db.Model):
    """
    Model for storing bug reports submitted by users.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    contact_email = db.Column(db.String(120), nullable=True)
    severity = db.Column(db.String(20), default='medium')  # 'low', 'medium', 'high', 'critical'
    status = db.Column(db.String(20), default='open')  # 'open', 'in_progress', 'resolved', 'closed'
    browser_info = db.Column(db.String(200), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    page_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    reporter = db.relationship('User', foreign_keys=[user_id], backref='bug_reports')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_bugs')

    def __repr__(self):
        return f"BugReport('{self.title}', Status: '{self.status}', Reporter: {self.user_id})"


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(32), nullable=False)  # Present, Late, etc.
    notes = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='attendance_records')
    class_info = db.relationship('Class', backref='attendance_records')
    teacher = db.relationship('TeacherStaff', backref='attendance_taken')

    def __repr__(self):
        return f"Attendance(Student: {self.student_id}, Class: {self.class_id}, Date: {self.date}, Status: {self.status})"


class SystemConfig(db.Model):
    """
    Model for storing system configuration settings.
    """
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # 'general', 'security', 'performance', 'backup'
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    updater = db.relationship('User', backref='config_updates')
    
    def __repr__(self):
        return f"SystemConfig('{self.key}': '{self.value}')"
    
    @classmethod
    def get_value(cls, key, default=None):
        """Get a configuration value by key."""
        config = cls.query.filter_by(key=key).first()
        return config.value if config else default
    
    @classmethod
    def set_value(cls, key, value, description=None, category='general', user_id=None):
        """Set a configuration value by key."""
        config = cls.query.filter_by(key=key).first()
        if config:
            config.value = value
            config.description = description
            config.category = category
            config.updated_by = user_id
        else:
            config = cls(
                key=key,
                value=value,
                description=description,
                category=category,
                updated_by=user_id
            )
            db.session.add(config)
        
        db.session.commit()
        return config

