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
    
    # Email fields
    email = db.Column(db.String(120), unique=True, nullable=True)  # Personal email
    google_workspace_email = db.Column(db.String(120), unique=True, nullable=True)  # Google Workspace email (@clarascienceacademy.org)
    
    # Password management flags
    is_temporary_password = db.Column(db.Boolean, default=False, nullable=False)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Login tracking
    login_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Google OAuth tokens (encrypted)
    _google_refresh_token = db.Column(db.String(512), nullable=True)
    
    @property
    def google_refresh_token(self):
        """
        Decrypts the refresh token when accessed.
        """
        if not self._google_refresh_token:
            return None
        try:
            from flask import current_app
            from cryptography.fernet import Fernet
            f = Fernet(current_app.config['ENCRYPTION_KEY'].encode('utf-8') if isinstance(current_app.config['ENCRYPTION_KEY'], str) else current_app.config['ENCRYPTION_KEY'])
            return f.decrypt(self._google_refresh_token.encode('utf-8')).decode('utf-8')
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Failed to decrypt token for user {self.id}: {e}")
            return None
    
    @google_refresh_token.setter
    def google_refresh_token(self, token):
        """
        Encrypts the refresh token when set.
        """
        if token is None:
            self._google_refresh_token = None
        else:
            from flask import current_app
            from cryptography.fernet import Fernet
            f = Fernet(current_app.config['ENCRYPTION_KEY'].encode('utf-8') if isinstance(current_app.config['ENCRYPTION_KEY'], str) else current_app.config['ENCRYPTION_KEY'])
            self._google_refresh_token = f.encrypt(token.encode('utf-8')).decode('utf-8')

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
    
    def generate_email(self):
        """Generate email address based on first name, last initial, month & year of birth"""
        if not self.first_name or not self.last_name or not self.dob:
            return None
        
        try:
            from datetime import datetime
            
            # Parse DOB (handle both MM/DD/YYYY and YYYY-MM-DD)
            dob = self.dob
            if '-' in dob:
                # Format: YYYY-MM-DD
                dt = datetime.strptime(dob, '%Y-%m-%d')
            elif '/' in dob:
                # Format: MM/DD/YYYY
                dt = datetime.strptime(dob, '%m/%d/%Y')
            else:
                return None
            
            # Format: first name + last initial + month + year
            first_name_clean = self.first_name.lower().replace(' ', '')
            last_initial = self.last_name[0].lower()
            month = str(dt.month).zfill(2)
            year = str(dt.year)[-2:]
            
            email = f"{first_name_clean}{last_initial}{month}{year}@clarascienceacademy.org"
            return email
            
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
    Enhanced to support multiple teachers and substitute teachers.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)  # Primary teacher
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    # grade_levels = db.Column(db.String(100), nullable=True)  # Temporarily commented out until migration is applied
    
    # Class metadata
    room_number = db.Column(db.String(20), nullable=True)
    schedule = db.Column(db.String(200), nullable=True)  # e.g., "Mon/Wed/Fri 9:00-10:00"
    max_students = db.Column(db.Integer, default=30, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Google Classroom integration
    google_classroom_id = db.Column(db.String(100), nullable=True, unique=True)

    # Relationships
    teacher = db.relationship('TeacherStaff', backref='primary_classes', lazy=True, foreign_keys=[teacher_id])
    school_year = db.relationship('SchoolYear', backref='classes', lazy=True)
    
    # Many-to-many relationships for multiple teachers
    additional_teachers = db.relationship('TeacherStaff', 
                                        secondary='class_additional_teachers',
                                        backref='additional_classes',
                                        lazy='dynamic')
    
    substitute_teachers = db.relationship('TeacherStaff',
                                        secondary='class_substitute_teachers', 
                                        backref='substitute_classes',
                                        lazy='dynamic')

    def get_grade_levels(self):
        """Return grade levels as a list of integers"""
        # Temporarily return empty list until migration is applied
        return []
    
    def set_grade_levels(self, grade_list):
        """Set grade levels from a list of integers"""
        # Temporarily do nothing until migration is applied
        pass
    
    def get_grade_levels_display(self):
        """Return grade levels as a formatted string for display"""
        # Temporarily return "Not specified" until migration is applied
        return "Not specified"

    def __repr__(self):
        return f"Class('{self.name}', Subject: '{self.subject}')"


# Association tables for many-to-many relationships
class_additional_teachers = db.Table('class_additional_teachers',
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True),
    db.Column('teacher_id', db.Integer, db.ForeignKey('teacher_staff.id'), primary_key=True),
    db.Column('role', db.String(50), default='co-teacher', nullable=False),  # co-teacher, assistant, etc.
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow, nullable=False)
)

class_substitute_teachers = db.Table('class_substitute_teachers',
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True),
    db.Column('teacher_id', db.Integer, db.ForeignKey('teacher_staff.id'), primary_key=True),
    db.Column('priority', db.Integer, default=1, nullable=False),  # 1 = first choice, 2 = second choice, etc.
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow, nullable=False)
)


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
    
    # Assignment status: Active, Inactive, Voided
    status = db.Column(db.String(20), default='Active', nullable=False)
    
    # Assignment type: pdf, quiz, discussion
    assignment_type = db.Column(db.String(20), default='pdf', nullable=False)
    
    # Quiz save and continue settings
    allow_save_and_continue = db.Column(db.Boolean, default=False, nullable=False)
    max_save_attempts = db.Column(db.Integer, default=10, nullable=False)
    save_timeout_minutes = db.Column(db.Integer, default=30, nullable=False)
    
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


class QuizQuestion(db.Model):
    """
    Model for storing quiz questions.
    """
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # multiple_choice, true_false, short_answer, essay
    points = db.Column(db.Float, default=1.0, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    assignment = db.relationship('Assignment', backref='quiz_questions', lazy=True)
    
    def __repr__(self):
        return f"QuizQuestion('{self.question_text[:50]}...', Type: {self.question_type})"


class QuizOption(db.Model):
    """
    Model for storing quiz question options (for multiple choice and true/false).
    """
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    option_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    
    question = db.relationship('QuizQuestion', backref='options', lazy=True)
    
    def __repr__(self):
        return f"QuizOption('{self.option_text[:30]}...', Correct: {self.is_correct})"


class QuizAnswer(db.Model):
    """
    Model for storing student quiz answers.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=True)  # For short answer and essay
    selected_option_id = db.Column(db.Integer, db.ForeignKey('quiz_option.id'), nullable=True)  # For multiple choice and true/false
    is_correct = db.Column(db.Boolean, nullable=True)  # Calculated when submitted
    points_earned = db.Column(db.Float, default=0.0, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref='quiz_answers', lazy=True)
    question = db.relationship('QuizQuestion', backref='answers', lazy=True)
    selected_option = db.relationship('QuizOption', backref='selected_answers', lazy=True)
    
    def __repr__(self):
        return f"QuizAnswer(Student: {self.student_id}, Question: {self.question_id}, Correct: {self.is_correct})"


class QuizProgress(db.Model):
    """
    Model for tracking student progress on quiz assignments with save and continue functionality.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    current_question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=True)
    answers_data = db.Column(db.Text, nullable=True)  # JSON string of saved answers
    progress_percentage = db.Column(db.Integer, default=0, nullable=False)
    questions_answered = db.Column(db.Integer, default=0, nullable=False)
    total_questions = db.Column(db.Integer, default=0, nullable=False)
    last_saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_submitted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='quiz_progress')
    assignment = db.relationship('Assignment', backref='quiz_progress')
    current_question = db.relationship('QuizQuestion', backref='progress_tracking')
    
    def __repr__(self):
        return f"QuizProgress(Student: {self.student_id}, Assignment: {self.assignment_id}, Progress: {self.progress_percentage}%)"


class DiscussionThread(db.Model):
    """
    Model for storing discussion threads.
    """
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    
    assignment = db.relationship('Assignment', backref='discussion_threads', lazy=True)
    student = db.relationship('Student', backref='discussion_threads', lazy=True)
    
    def __repr__(self):
        return f"DiscussionThread('{self.title}', Assignment: {self.assignment_id})"


class DiscussionPost(db.Model):
    """
    Model for storing discussion posts (replies to threads).
    """
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('discussion_thread.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_teacher_post = db.Column(db.Boolean, default=False, nullable=False)
    
    thread = db.relationship('DiscussionThread', backref='posts', lazy=True)
    student = db.relationship('Student', backref='discussion_posts', lazy=True)
    
    def __repr__(self):
        return f"DiscussionPost(Thread: {self.thread_id}, Student: {self.student_id})"


class Grade(db.Model):
    """
    Model for storing student grades.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    grade_data = db.Column(db.Text, nullable=False)  # JSON string containing score and comments
    graded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Voiding fields
    is_voided = db.Column(db.Boolean, default=False, nullable=False)
    voided_by = db.Column(db.Integer, nullable=True)
    voided_at = db.Column(db.DateTime, nullable=True)
    voided_reason = db.Column(db.Text, nullable=True)

    student = db.relationship('Student', backref='grades', lazy=True)
    assignment = db.relationship('Assignment', backref='grades', lazy=True)

    def __repr__(self):
        return f"Grade(Student: {self.student_id}, Assignment: {self.assignment_id})"


class AssignmentRedo(db.Model):
    """
    Model for tracking assignment redo permissions and attempts.
    Allows teachers/admins to grant students the opportunity to redo assignments.
    """
    __tablename__ = 'assignment_redo'
    
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    
    # Redo permission details
    granted_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=True)  # Teacher who granted the redo
    granted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    redo_deadline = db.Column(db.DateTime, nullable=False)  # New deadline for redo submission
    reason = db.Column(db.Text, nullable=True)  # Why redo was granted (optional)
    
    # Redo attempt tracking
    is_used = db.Column(db.Boolean, default=False, nullable=False)  # Has student submitted redo?
    redo_submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=True)  # Links to redo submission
    redo_submitted_at = db.Column(db.DateTime, nullable=True)
    
    # Grading information
    original_grade = db.Column(db.Float, nullable=True)  # Original grade before redo
    redo_grade = db.Column(db.Float, nullable=True)  # Grade from redo attempt
    final_grade = db.Column(db.Float, nullable=True)  # Final grade (higher of the two, with late penalty if applicable)
    was_redo_late = db.Column(db.Boolean, default=False, nullable=False)  # Was redo submitted after deadline?
    
    # Relationships
    assignment = db.relationship('Assignment', backref='redos', lazy=True)
    student = db.relationship('Student', backref='assignment_redos', lazy=True)
    granted_by_teacher = db.relationship('TeacherStaff', backref='granted_redos', lazy=True)
    redo_submission = db.relationship('Submission', foreign_keys=[redo_submission_id], backref='redo_for', lazy=True)
    
    def __repr__(self):
        return f"AssignmentRedo(Assignment: {self.assignment_id}, Student: {self.student_id}, Used: {self.is_used})"


class QuarterGrade(db.Model):
    """
    Model for storing calculated quarter grades that refresh automatically.
    Stores one record per student per class per quarter.
    """
    __tablename__ = 'quarter_grade'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    quarter = db.Column(db.String(10), nullable=False)  # 'Q1', 'Q2', 'Q3', 'Q4'
    
    # Grade data
    letter_grade = db.Column(db.String(5), nullable=True)  # 'A', 'B+', etc.
    percentage = db.Column(db.Float, nullable=True)
    assignments_count = db.Column(db.Integer, default=0)
    
    # Metadata
    last_calculated = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='quarter_grades', lazy=True)
    class_info = db.relationship('Class', backref='quarter_grades', lazy=True)
    school_year = db.relationship('SchoolYear', backref='quarter_grades', lazy=True)
    
    # Unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint('student_id', 'class_id', 'school_year_id', 'quarter', name='uq_student_class_quarter'),
    )
    
    def __repr__(self):
        return f"QuarterGrade(Student: {self.student_id}, Class: {self.class_id}, Quarter: {self.quarter}, Grade: {self.letter_grade})"


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


class SchoolDayAttendance(db.Model):
    """
    Model for tracking school-day attendance (whether student came to school that day)
    This is separate from class-period attendance
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(32), nullable=False)  # Present, Absent, Late, Excused Absence
    notes = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('Student', backref='school_day_attendance')
    recorder = db.relationship('User', backref='recorded_attendance')

    # Ensure one record per student per day
    __table_args__ = (db.UniqueConstraint('student_id', 'date', name='unique_student_date'),)

    def __repr__(self):
        return f"SchoolDayAttendance(Student: {self.student_id}, Date: {self.date}, Status: {self.status})"


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


class StudentGroup(db.Model):
    """
    Model for student groups within a class (for group work, projects, etc.).
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    max_students = db.Column(db.Integer, nullable=True)  # Optional limit on group size
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    class_info = db.relationship('Class', backref='student_groups')
    creator = db.relationship('TeacherStaff', backref='created_groups')
    
    def __repr__(self):
        return f"StudentGroup('{self.name}', Class: {self.class_id})"


class StudentGroupMember(db.Model):
    """
    Model for tracking which students belong to which groups.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_leader = db.Column(db.Boolean, default=False)  # Optional group leader designation
    
    # Relationships
    group = db.relationship('StudentGroup', backref='members')
    student = db.relationship('Student', backref='group_memberships')
    
    def __repr__(self):
        return f"StudentGroupMember(Group: {self.group_id}, Student: {self.student_id})"


class GroupAssignment(db.Model):
    """
    Model for assignments that are specifically for groups.
    Enhanced to support all assignment types: PDF/Paper, Quiz, Discussion.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    quarter = db.Column(db.String(10), nullable=False)
    semester = db.Column(db.String(10), nullable=True)
    academic_period_id = db.Column(db.Integer, db.ForeignKey('academic_period.id'), nullable=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_year.id'), nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Assignment status: Active, Inactive, Voided
    status = db.Column(db.String(20), default='Active', nullable=False)
    
    # Assignment type: pdf, quiz, discussion
    assignment_type = db.Column(db.String(20), default='pdf', nullable=False)
    
    # Quiz save and continue settings (for quiz type)
    allow_save_and_continue = db.Column(db.Boolean, default=False, nullable=False)
    max_save_attempts = db.Column(db.Integer, default=10, nullable=False)
    save_timeout_minutes = db.Column(db.Integer, default=30, nullable=False)
    
    # Group-specific fields
    group_size_min = db.Column(db.Integer, default=2)  # Minimum students per group
    group_size_max = db.Column(db.Integer, default=4)  # Maximum students per group
    allow_individual = db.Column(db.Boolean, default=False)  # Allow individual submissions
    collaboration_type = db.Column(db.String(20), default='group')  # 'group', 'individual', 'both'
    selected_group_ids = db.Column(db.Text, nullable=True)  # JSON string of selected group IDs (null = all groups)
    
    # File attachment fields
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_original_filename = db.Column(db.String(255), nullable=True)
    attachment_file_path = db.Column(db.String(500), nullable=True)
    attachment_file_size = db.Column(db.Integer, nullable=True)
    attachment_mime_type = db.Column(db.String(100), nullable=True)
    
    # Relationships
    class_info = db.relationship('Class', backref='group_assignments')
    school_year = db.relationship('SchoolYear', backref='group_assignments')
    academic_period = db.relationship('AcademicPeriod', backref='group_assignments')
    quiz_questions = db.relationship('GroupQuizQuestion', backref='group_assignment', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"GroupAssignment('{self.title}', Class: {self.class_id})"


class GroupQuizQuestion(db.Model):
    """
    Model for storing quiz questions for group assignments.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # multiple_choice, true_false, short_answer, essay
    points = db.Column(db.Float, default=1.0, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"GroupQuizQuestion('{self.question_text[:50]}...', Type: {self.question_type})"


class GroupQuizOption(db.Model):
    """
    Model for storing quiz question options for group assignments.
    """
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('group_quiz_question.id'), nullable=False)
    option_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    
    question = db.relationship('GroupQuizQuestion', backref='options', lazy=True)
    
    def __repr__(self):
        return f"GroupQuizOption('{self.option_text[:30]}...', Correct: {self.is_correct})"


class GroupQuizAnswer(db.Model):
    """
    Model for storing group quiz answers.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=True)  # Group that answered
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)  # Individual student (for individual submissions)
    question_id = db.Column(db.Integer, db.ForeignKey('group_quiz_question.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=True)  # For short answer and essay
    selected_option_id = db.Column(db.Integer, db.ForeignKey('group_quiz_option.id'), nullable=True)  # For multiple choice and true/false
    is_correct = db.Column(db.Boolean, nullable=True)  # Calculated when submitted
    points_earned = db.Column(db.Float, default=0.0, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    group = db.relationship('StudentGroup', backref='quiz_answers', lazy=True)
    student = db.relationship('Student', backref='group_quiz_answers', lazy=True)
    question = db.relationship('GroupQuizQuestion', backref='answers', lazy=True)
    selected_option = db.relationship('GroupQuizOption', backref='selected_answers', lazy=True)
    
    def __repr__(self):
        return f"GroupQuizAnswer(Group: {self.group_id}, Student: {self.student_id}, Question: {self.question_id})"


class GroupSubmission(db.Model):
    """
    Model for group submissions to group assignments.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=True)  # Nullable for individual submissions
    submitted_by = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)  # Student who submitted
    submission_text = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_late = db.Column(db.Boolean, default=False)
    
    # File attachment fields
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_original_filename = db.Column(db.String(255), nullable=True)
    attachment_file_path = db.Column(db.String(500), nullable=True)
    attachment_file_size = db.Column(db.Integer, nullable=True)
    attachment_mime_type = db.Column(db.String(100), nullable=True)
    
    # Relationships
    group_assignment = db.relationship('GroupAssignment', backref='submissions')
    group = db.relationship('StudentGroup', backref='submissions')
    submitter = db.relationship('Student', backref='group_submissions')
    
    def __repr__(self):
        return f"GroupSubmission(Assignment: {self.group_assignment_id}, Group: {self.group_id})"


class GroupGrade(db.Model):
    """
    Model for grades on group assignments.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=True)  # Nullable for individual grades
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    grade_data = db.Column(db.Text, nullable=False)  # JSON string with grade details
    graded_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    graded_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.Column(db.Text, nullable=True)
    
    # Voiding fields
    is_voided = db.Column(db.Boolean, default=False, nullable=False)
    voided_by = db.Column(db.Integer, nullable=True)
    voided_at = db.Column(db.DateTime, nullable=True)
    voided_reason = db.Column(db.Text, nullable=True)
    
    # Relationships
    group_assignment = db.relationship('GroupAssignment', backref='grades')
    group = db.relationship('StudentGroup', backref='grades')
    student = db.relationship('Student', backref='group_grades')
    grader = db.relationship('TeacherStaff', backref='group_grades_given')
    
    def __repr__(self):
        return f"GroupGrade(Assignment: {self.group_assignment_id}, Student: {self.student_id})"


class GroupTemplate(db.Model):
    """
    Model for saving common group configurations.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    group_size = db.Column(db.Integer, nullable=False, default=3)
    grouping_criteria = db.Column(db.String(50), nullable=False, default='random')  # random, skill_based, mixed_ability
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    class_info = db.relationship('Class', backref='group_templates')
    creator = db.relationship('TeacherStaff', backref='created_group_templates')
    
    def __repr__(self):
        return f"GroupTemplate('{self.name}', Size: {self.group_size})"


class PeerEvaluation(db.Model):
    """
    Model for peer evaluations within groups.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)  # Student doing the evaluation
    evaluatee_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)  # Student being evaluated
    collaboration_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    contribution_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    communication_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    overall_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    comments = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group_assignment = db.relationship('GroupAssignment', backref='peer_evaluations')
    group = db.relationship('StudentGroup', backref='peer_evaluations')
    evaluator = db.relationship('Student', foreign_keys=[evaluator_id], backref='evaluations_given')
    evaluatee = db.relationship('Student', foreign_keys=[evaluatee_id], backref='evaluations_received')
    
    def __repr__(self):
        return f"PeerEvaluation(Evaluator: {self.evaluator_id}, Evaluatee: {self.evaluatee_id})"


class AssignmentExtension(db.Model):
    """
    Model for tracking assignment extensions granted to students.
    """
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    extended_due_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    granted_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    assignment = db.relationship('Assignment', backref='extensions')
    student = db.relationship('Student', backref='assignment_extensions')
    granter = db.relationship('TeacherStaff', backref='granted_extensions')
    
    def __repr__(self):
        return f"AssignmentExtension(Assignment: {self.assignment_id}, Student: {self.student_id}, New Due: {self.extended_due_date})"

class AssignmentRubric(db.Model):
    """
    Model for assignment rubrics.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    criteria_data = db.Column(db.Text, nullable=False)  # JSON string with rubric criteria
    total_points = db.Column(db.Integer, nullable=False, default=100)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group_assignment = db.relationship('GroupAssignment', backref='rubrics')
    creator = db.relationship('TeacherStaff', backref='created_rubrics')
    
    def __repr__(self):
        return f"AssignmentRubric('{self.name}', Points: {self.total_points})"


class GroupContract(db.Model):
    """
    Model for group contracts and expectations.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=True)
    contract_data = db.Column(db.Text, nullable=False)  # JSON string with contract terms
    is_agreed = db.Column(db.Boolean, default=False)
    agreed_by = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    agreed_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group = db.relationship('StudentGroup', backref='contracts')
    group_assignment = db.relationship('GroupAssignment', backref='contracts')
    student = db.relationship('Student', backref='contract_agreements')
    creator = db.relationship('TeacherStaff', backref='created_contracts')
    
    def __repr__(self):
        return f"GroupContract(Group: {self.group_id}, Agreed: {self.is_agreed})"


class ReflectionJournal(db.Model):
    """
    Model for student reflection journals on group work.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    reflection_text = db.Column(db.Text, nullable=False)
    collaboration_rating = db.Column(db.Integer, nullable=False)  # 1-5 scale
    learning_rating = db.Column(db.Integer, nullable=False)  # 1-5 scale
    challenges_faced = db.Column(db.Text, nullable=True)
    lessons_learned = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='reflection_journals')
    group = db.relationship('StudentGroup', backref='reflection_journals')
    group_assignment = db.relationship('GroupAssignment', backref='reflection_journals')
    
    def __repr__(self):
        return f"ReflectionJournal(Student: {self.student_id}, Assignment: {self.group_assignment_id})"


class GroupProgress(db.Model):
    """
    Model for tracking group progress on assignments.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    progress_percentage = db.Column(db.Integer, nullable=False, default=0)  # 0-100
    status = db.Column(db.String(20), nullable=False, default='not_started')  # not_started, in_progress, completed
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    group = db.relationship('StudentGroup', backref='progress_tracking')
    group_assignment = db.relationship('GroupAssignment', backref='progress_tracking')
    
    def __repr__(self):
        return f"GroupProgress(Group: {self.group_id}, Progress: {self.progress_percentage}%)"


class AssignmentTemplate(db.Model):
    """
    Model for saving common assignment structures.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    template_data = db.Column(db.Text, nullable=False)  # JSON string with assignment structure
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    class_info = db.relationship('Class', backref='assignment_templates')
    creator = db.relationship('TeacherStaff', backref='created_assignment_templates')

class GroupRotation(db.Model):
    """
    Model for managing group rotations and member changes.
    """
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    rotation_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rotation_type = db.Column(db.String(50), nullable=False, default='manual')  # manual, automatic, scheduled
    rotation_frequency = db.Column(db.String(20), nullable=True)  # weekly, biweekly, monthly, custom
    group_size = db.Column(db.Integer, nullable=False, default=3)
    grouping_criteria = db.Column(db.String(50), nullable=False, default='random')  # random, skill_based, mixed_ability
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_rotated = db.Column(db.DateTime, nullable=True)
    next_rotation = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    class_info = db.relationship('Class', backref='group_rotations')
    creator = db.relationship('TeacherStaff', backref='created_group_rotations')

class GroupRotationHistory(db.Model):
    """
    Model for tracking group rotation history.
    """
    id = db.Column(db.Integer, primary_key=True)
    rotation_id = db.Column(db.Integer, db.ForeignKey('group_rotation.id'), nullable=False)
    rotation_date = db.Column(db.DateTime, default=datetime.utcnow)
    previous_groups = db.Column(db.Text, nullable=False)  # JSON string with previous group assignments
    new_groups = db.Column(db.Text, nullable=False)  # JSON string with new group assignments
    rotation_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    rotation = db.relationship('GroupRotation', backref='rotation_history')

class PeerReview(db.Model):
    """
    Model for peer review of student work.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)  # Student doing the review
    reviewee_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)  # Student being reviewed
    work_quality_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    creativity_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    presentation_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    overall_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    constructive_feedback = db.Column(db.Text, nullable=True)
    strengths = db.Column(db.Text, nullable=True)
    improvements = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group_assignment = db.relationship('GroupAssignment', backref='peer_reviews')
    group = db.relationship('StudentGroup', backref='peer_reviews')
    reviewer = db.relationship('Student', foreign_keys=[reviewer_id], backref='reviews_given')
    reviewee = db.relationship('Student', foreign_keys=[reviewee_id], backref='reviews_received')

class DraftSubmission(db.Model):
    """
    Model for draft submissions with feedback capability.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    draft_content = db.Column(db.Text, nullable=False)
    draft_attachments = db.Column(db.Text, nullable=True)  # JSON string with file paths
    submission_notes = db.Column(db.Text, nullable=True)
    is_final = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group_assignment = db.relationship('GroupAssignment', backref='draft_submissions')
    group = db.relationship('StudentGroup', backref='draft_submissions')
    student = db.relationship('Student', backref='draft_submissions')

class DraftFeedback(db.Model):
    """
    Model for feedback on draft submissions.
    """
    id = db.Column(db.Integer, primary_key=True)
    draft_submission_id = db.Column(db.Integer, db.ForeignKey('draft_submission.id'), nullable=False)
    feedback_provider_id = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    feedback_content = db.Column(db.Text, nullable=False)
    feedback_type = db.Column(db.String(20), nullable=False, default='general')  # general, specific, improvement
    is_approved = db.Column(db.Boolean, default=False)
    provided_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    draft_submission = db.relationship('DraftSubmission', backref='feedback')
    feedback_provider = db.relationship('TeacherStaff', backref='draft_feedback')

class DeadlineReminder(db.Model):
    """
    Model for deadline reminders with automated notifications.
    """
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    reminder_type = db.Column(db.String(20), nullable=False, default='assignment')  # assignment, group_assignment, general
    reminder_title = db.Column(db.String(200), nullable=False)
    reminder_message = db.Column(db.Text, nullable=False)
    reminder_date = db.Column(db.DateTime, nullable=False)
    reminder_frequency = db.Column(db.String(20), nullable=False, default='once')  # once, daily, weekly
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_sent = db.Column(db.DateTime, nullable=True)
    next_send = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    assignment = db.relationship('Assignment', backref='deadline_reminders')
    group_assignment = db.relationship('GroupAssignment', backref='deadline_reminders')
    class_info = db.relationship('Class', backref='deadline_reminders')
    creator = db.relationship('TeacherStaff', backref='created_deadline_reminders')

class ReminderNotification(db.Model):
    """
    Model for tracking reminder notifications sent to students.
    """
    id = db.Column(db.Integer, primary_key=True)
    reminder_id = db.Column(db.Integer, db.ForeignKey('deadline_reminder.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    notification_type = db.Column(db.String(20), nullable=False, default='email')  # email, in_app, sms
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='sent')  # sent, delivered, failed
    response_data = db.Column(db.Text, nullable=True)  # JSON string with response details
    
    # Relationships
    reminder = db.relationship('DeadlineReminder', backref='notifications')
    student = db.relationship('Student', backref='reminder_notifications')
    
    def __repr__(self):
        return f"ReminderNotification('{self.notification_type}', Student: {self.student_id})"


# 360-Degree Feedback Models
class Feedback360(db.Model):
    """
    Model for 360-degree feedback sessions.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    target_student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    feedback_type = db.Column(db.String(20), nullable=False, default='comprehensive')  # comprehensive, peer_only, self_only
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    class_info = db.relationship('Class', backref='feedback360_sessions')
    target_student = db.relationship('Student', foreign_keys=[target_student_id], backref='feedback360_received')
    creator = db.relationship('TeacherStaff', backref='created_feedback360')
    
    def __repr__(self):
        return f"Feedback360('{self.title}', Target: {self.target_student_id})"


class Feedback360Response(db.Model):
    """
    Model for individual feedback responses in 360-degree feedback.
    """
    id = db.Column(db.Integer, primary_key=True)
    feedback360_id = db.Column(db.Integer, db.ForeignKey('feedback360.id'), nullable=False)
    respondent_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    respondent_type = db.Column(db.String(20), nullable=False)  # peer, self, teacher
    feedback_data = db.Column(db.Text, nullable=False)  # JSON string with feedback responses
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_anonymous = db.Column(db.Boolean, default=False)
    
    # Relationships
    feedback360 = db.relationship('Feedback360', backref='responses')
    respondent = db.relationship('Student', backref='feedback360_given')
    
    def __repr__(self):
        return f"Feedback360Response('{self.respondent_type}', Session: {self.feedback360_id})"


class Feedback360Criteria(db.Model):
    """
    Model for feedback criteria in 360-degree feedback sessions.
    """
    id = db.Column(db.Integer, primary_key=True)
    feedback360_id = db.Column(db.Integer, db.ForeignKey('feedback360.id'), nullable=False)
    criteria_name = db.Column(db.String(200), nullable=False)
    criteria_description = db.Column(db.Text, nullable=True)
    criteria_type = db.Column(db.String(20), nullable=False, default='rating')  # rating, text, scale
    scale_min = db.Column(db.Integer, default=1)
    scale_max = db.Column(db.Integer, default=5)
    is_required = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    
    # Relationships
    feedback360 = db.relationship('Feedback360', backref='criteria')
    
    def __repr__(self):
        return f"Feedback360Criteria('{self.criteria_name}', Session: {self.feedback360_id})"


# Conflict Resolution Models
class GroupConflict(db.Model):
    """
    Model for tracking group conflicts and their resolution.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    conflict_type = db.Column(db.String(50), nullable=False)  # communication, workload, personality, other
    conflict_description = db.Column(db.Text, nullable=False)
    severity_level = db.Column(db.String(20), nullable=False, default='medium')  # low, medium, high, critical
    status = db.Column(db.String(20), nullable=False, default='reported')  # reported, investigating, resolved, escalated
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=True)
    
    # Relationships
    group = db.relationship('StudentGroup', backref='conflicts')
    group_assignment = db.relationship('GroupAssignment', backref='conflicts')
    reporter = db.relationship('Student', foreign_keys=[reported_by], backref='reported_conflicts')
    resolver = db.relationship('TeacherStaff', backref='resolved_conflicts')
    
    def __repr__(self):
        return f"GroupConflict('{self.conflict_type}', Group: {self.group_id})"


class ConflictResolution(db.Model):
    """
    Model for tracking conflict resolution steps and outcomes.
    """
    id = db.Column(db.Integer, primary_key=True)
    conflict_id = db.Column(db.Integer, db.ForeignKey('group_conflict.id'), nullable=False)
    resolution_step = db.Column(db.String(100), nullable=False)
    step_description = db.Column(db.Text, nullable=False)
    step_type = db.Column(db.String(30), nullable=False)  # mediation, intervention, restructuring, other
    outcome = db.Column(db.String(20), nullable=False, default='pending')  # pending, successful, unsuccessful, partial
    implemented_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    implemented_at = db.Column(db.DateTime, default=datetime.utcnow)
    follow_up_date = db.Column(db.DateTime, nullable=True)
    follow_up_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    conflict = db.relationship('GroupConflict', backref='resolution_steps')
    implementer = db.relationship('TeacherStaff', backref='implemented_resolutions')
    
    def __repr__(self):
        return f"ConflictResolution('{self.resolution_step}', Conflict: {self.conflict_id})"


class ConflictParticipant(db.Model):
    """
    Model for tracking students involved in conflicts.
    """
    id = db.Column(db.Integer, primary_key=True)
    conflict_id = db.Column(db.Integer, db.ForeignKey('group_conflict.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # reporter, involved, witness, other
    student_perspective = db.Column(db.Text, nullable=True)
    is_resolved = db.Column(db.Boolean, default=False)
    
    # Relationships
    conflict = db.relationship('GroupConflict', backref='participants')
    student = db.relationship('Student', backref='conflict_participations')
    
    def __repr__(self):
        return f"ConflictParticipant('{self.role}', Student: {self.student_id})"


# Comprehensive Reporting & Analytics Models
class GroupWorkReport(db.Model):
    """
    Model for comprehensive group work reports and analytics.
    """
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    report_name = db.Column(db.String(200), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # comprehensive, performance, collaboration, individual
    report_period_start = db.Column(db.DateTime, nullable=False)
    report_period_end = db.Column(db.DateTime, nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    report_data = db.Column(db.Text, nullable=False)  # JSON string with comprehensive report data
    is_exported = db.Column(db.Boolean, default=False)
    export_format = db.Column(db.String(20), nullable=True)  # pdf, excel, csv
    export_path = db.Column(db.String(500), nullable=True)
    
    # Relationships
    class_info = db.relationship('Class', backref='group_work_reports')
    generator = db.relationship('TeacherStaff', backref='generated_reports')
    
    def __repr__(self):
        return f"GroupWorkReport('{self.report_name}', Type: {self.report_type})"


class IndividualContribution(db.Model):
    """
    Model for tracking individual student contributions to group work.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    contribution_type = db.Column(db.String(50), nullable=False)  # research, writing, presentation, coordination, other
    contribution_description = db.Column(db.Text, nullable=False)
    time_spent_minutes = db.Column(db.Integer, nullable=True)
    contribution_quality = db.Column(db.Integer, nullable=True)  # 1-5 scale
    peer_rating = db.Column(db.Float, nullable=True)  # Average peer rating
    teacher_rating = db.Column(db.Float, nullable=True)  # Teacher assessment
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=True)
    
    # Relationships
    student = db.relationship('Student', backref='contributions')
    group = db.relationship('StudentGroup', backref='member_contributions')
    group_assignment = db.relationship('GroupAssignment', backref='contributions')
    recorder = db.relationship('TeacherStaff', backref='recorded_contributions')
    
    def __repr__(self):
        return f"IndividualContribution(Student: {self.student_id}, Type: {self.contribution_type})"


class TimeTracking(db.Model):
    """
    Model for tracking time spent on group assignments and activities.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=True)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=True)
    activity_type = db.Column(db.String(50), nullable=False)  # research, writing, meeting, presentation, other
    activity_description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    productivity_rating = db.Column(db.Integer, nullable=True)  # 1-5 scale
    notes = db.Column(db.Text, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    student = db.relationship('Student', backref='time_tracking')
    group = db.relationship('StudentGroup', backref='time_tracking')
    group_assignment = db.relationship('GroupAssignment', backref='time_tracking')
    verifier = db.relationship('TeacherStaff', backref='verified_time_tracking')
    
    def __repr__(self):
        return f"TimeTracking(Student: {self.student_id}, Duration: {self.duration_minutes}min)"


class CollaborationMetrics(db.Model):
    """
    Model for tracking collaboration metrics and group dynamics.
    """
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    group_assignment_id = db.Column(db.Integer, db.ForeignKey('group_assignment.id'), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # communication, participation, leadership, conflict_resolution
    metric_value = db.Column(db.Float, nullable=False)
    metric_description = db.Column(db.Text, nullable=True)
    measurement_date = db.Column(db.DateTime, default=datetime.utcnow)
    measured_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=True)
    measurement_method = db.Column(db.String(50), nullable=False)  # observation, peer_evaluation, self_assessment, automated
    
    # Relationships
    group = db.relationship('StudentGroup', backref='collaboration_metrics')
    group_assignment = db.relationship('GroupAssignment', backref='collaboration_metrics')
    measurer = db.relationship('TeacherStaff', backref='measured_collaboration')
    
    def __repr__(self):
        return f"CollaborationMetrics(Group: {self.group_id}, Type: {self.metric_type})"


class ReportExport(db.Model):
    """
    Model for tracking report exports and downloads.
    """
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('group_work_report.id'), nullable=False)
    export_format = db.Column(db.String(20), nullable=False)  # pdf, excel, csv, json
    export_path = db.Column(db.String(500), nullable=False)
    file_size_bytes = db.Column(db.Integer, nullable=True)
    exported_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    exported_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    last_downloaded = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    report = db.relationship('GroupWorkReport', backref='exports')
    exporter = db.relationship('TeacherStaff', backref='exported_reports')
    
    def __repr__(self):
        return f"ReportExport(Report: {self.report_id}, Format: {self.export_format})"


class AnalyticsDashboard(db.Model):
    """
    Model for storing dashboard configurations and saved analytics views.
    """
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    dashboard_name = db.Column(db.String(200), nullable=False)
    dashboard_type = db.Column(db.String(50), nullable=False)  # overview, detailed, custom
    widget_config = db.Column(db.Text, nullable=False)  # JSON string with widget configurations
    filter_settings = db.Column(db.Text, nullable=True)  # JSON string with filter settings
    is_shared = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, nullable=True)
    access_count = db.Column(db.Integer, default=0)
    
    # Relationships
    class_info = db.relationship('Class', backref='analytics_dashboards')
    creator = db.relationship('TeacherStaff', backref='created_dashboards')
    
    def __repr__(self):
        return f"AnalyticsDashboard('{self.dashboard_name}', Type: {self.dashboard_type})"


class PerformanceBenchmark(db.Model):
    """
    Model for storing performance benchmarks and standards.
    """
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    benchmark_name = db.Column(db.String(200), nullable=False)
    benchmark_type = db.Column(db.String(50), nullable=False)  # grade, participation, collaboration, time_management
    benchmark_value = db.Column(db.Float, nullable=False)
    benchmark_description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('teacher_staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    effective_date = db.Column(db.DateTime, nullable=True)
    expiration_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    class_info = db.relationship('Class', backref='performance_benchmarks')
    creator = db.relationship('TeacherStaff', backref='created_benchmarks')
    
    def __repr__(self):
        return f"PerformanceBenchmark('{self.benchmark_name}', Value: {self.benchmark_value})"


# BugReport model temporarily removed to fix deployment issues
# Will be re-added after successful deployment


# ===== STUDENT JOBS MODELS =====

class CleaningTeam(db.Model):
    """
    Model for storing cleaning team information.
    """
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100), nullable=False, unique=True)  # "Team 1" or "Team 2"
    team_description = db.Column(db.String(200), nullable=False)  # "4 Classrooms & Hallway Trash"
    team_type = db.Column(db.String(50), default='cleaning')  # 'cleaning', 'lunch_duty', 'experiment_duty', 'other'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team_members = db.relationship('CleaningTeamMember', backref='cleaning_team', cascade='all, delete-orphan')
    inspections = db.relationship('CleaningInspection', backref='cleaning_team', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"CleaningTeam('{self.team_name}', '{self.team_description}')"


class CleaningTeamMember(db.Model):
    """
    Model for storing team member assignments.
    """
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('cleaning_team.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # "Sweeping Team", "Wipe Down Team", "Trash Team", "Bathroom Team"
    assignment_description = db.Column(db.Text, nullable=True)  # Detailed job assignment description
    is_active = db.Column(db.Boolean, default=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='cleaning_assignments')
    
    def __repr__(self):
        return f"CleaningTeamMember(Team: {self.team_id}, Student: {self.student_id}, Role: {self.role})"


class CleaningInspection(db.Model):
    """
    Model for storing cleaning inspection results.
    """
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('cleaning_team.id'), nullable=False)
    inspection_date = db.Column(db.Date, nullable=False)
    inspector_name = db.Column(db.String(100), nullable=False)
    inspection_type = db.Column(db.String(50), default='cleaning')  # 'cleaning', 'lunch_duty', 'experiment_duty', 'other'
    
    # Score tracking
    starting_score = db.Column(db.Integer, default=100)
    major_deductions = db.Column(db.Integer, default=0)  # -10 points each
    moderate_deductions = db.Column(db.Integer, default=0)  # -5 points each
    minor_deductions = db.Column(db.Integer, default=0)  # -2 points each
    bonus_points = db.Column(db.Integer, default=0)  # +15 max
    final_score = db.Column(db.Integer, nullable=False)
    
    # Detailed deductions
    bathroom_not_restocked = db.Column(db.Boolean, default=False)
    trash_can_left_full = db.Column(db.Boolean, default=False)
    floor_not_swept = db.Column(db.Boolean, default=False)
    materials_left_out = db.Column(db.Boolean, default=False)
    tables_missed = db.Column(db.Boolean, default=False)
    classroom_trash_full = db.Column(db.Boolean, default=False)
    bathroom_floor_poor = db.Column(db.Boolean, default=False)
    not_finished_on_time = db.Column(db.Boolean, default=False)
    small_debris_left = db.Column(db.Boolean, default=False)
    trash_spilled = db.Column(db.Boolean, default=False)
    dispensers_half_filled = db.Column(db.Boolean, default=False)
    
    # Bonus points
    exceptional_finish = db.Column(db.Boolean, default=False)
    speed_efficiency = db.Column(db.Boolean, default=False)
    going_above_beyond = db.Column(db.Boolean, default=False)
    teamwork_award = db.Column(db.Boolean, default=False)
    
    # Additional information
    inspector_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"CleaningInspection(Team: {self.team_id}, Date: {self.inspection_date}, Score: {self.final_score})"


class CleaningTask(db.Model):
    """
    Model for storing specific cleaning tasks and their assignments.
    """
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('cleaning_team.id'), nullable=False)
    task_name = db.Column(db.String(100), nullable=False)  # "Sweeping Team", "Wipe Down Team", etc.
    task_description = db.Column(db.Text, nullable=False)
    area_covered = db.Column(db.String(200), nullable=False)  # "all four classrooms", "both bathrooms", etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    team = db.relationship('CleaningTeam', backref='tasks')
    
    def __repr__(self):
        return f"CleaningTask('{self.task_name}', Team: {self.team_id})"


class CleaningSchedule(db.Model):
    """
    Model for storing cleaning schedules and rotations.
    """
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('cleaning_team.id'), nullable=False)
    schedule_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    team = db.relationship('CleaningTeam', backref='schedules')
    
    def __repr__(self):
        return f"CleaningSchedule(Team: {self.team_id}, Date: {self.schedule_date})"

