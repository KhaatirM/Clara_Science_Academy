# Clara Science App - Comprehensive Documentation

## 📚 Table of Contents

1. [System Overview](#system-overview)
2. [Core Features](#core-features)
3. [User Management](#user-management)
4. [Assignment Management](#assignment-management)
5. [Group Management](#group-management)
6. [Analytics & Reporting](#analytics--reporting)
7. [Bug Reporting System](#bug-reporting-system)
8. [Database Management](#database-management)
9. [Deployment & Configuration](#deployment--configuration)
10. [API Reference](#api-reference)

---

## 🎯 System Overview

The Clara Science App is a comprehensive educational management system designed for schools to manage students, teachers, assignments, grades, and group work. The system supports multiple user roles including Students, Teachers, School Administrators, and Directors.

### Key Features
- **Multi-role User Management**: Support for students, teachers, administrators, and directors
- **Assignment Management**: Create and manage PDF/Paper, Quiz, and Discussion assignments
- **Group Work System**: Advanced group management with analytics and collaboration tracking
- **Real-time Communication**: Messages, announcements, and notifications
- **Comprehensive Reporting**: Analytics, grade tracking, and performance metrics
- **Automatic Bug Reporting**: System-wide error capture and management

---

## 👥 User Management

### User Roles
- **Students**: Access to assignments, grades, group work, and communication
- **Teachers**: Full access to their classes, assignments, grading, and group management
- **School Administrators**: Management access to all classes and assignments
- **Directors**: Full system access including user management and system configuration

### Authentication & Security
- Password-based authentication with secure hashing
- Role-based access control (RBAC)
- CSRF protection on all forms
- Session management with Flask-Login

---

## 📝 Assignment Management

### Assignment Types

#### 1. PDF/Paper Assignments
- File upload support (PDF, DOC, DOCX, images)
- Due date and point value configuration
- Submission tracking and grading

#### 2. Quiz Assignments
- Multiple question types:
  - Multiple Choice
  - True/False
  - Short Answer
  - Essay Questions
- Automatic grading for objective questions
- Manual grading for subjective questions
- Timer functionality for timed quizzes

#### 3. Discussion Assignments
- Thread-based discussions
- Student participation tracking
- Instructor moderation capabilities

### Assignment Features
- **Status Management**: Active, Inactive, Overdue, Voided
- **Extension System**: Grant extensions to individual students
- **Grading Rubrics**: Customizable grading criteria
- **File Attachments**: Support for multiple file types
- **Template System**: Reusable assignment templates

---

## 👥 Group Management

### Group Creation & Management
- **Manual Group Creation**: Teachers can manually create and assign students to groups
- **Auto-Group Creation**: Automatic random assignment with customizable group sizes
- **Group Templates**: Reusable group configurations
- **Group Rotations**: Periodic group member rotation system

### Group Features
- **Group Contracts**: Establish group rules and expectations
- **Peer Evaluations**: Students evaluate their group members
- **Individual Contribution Tracking**: Track each member's contributions
- **Time Tracking**: Monitor time spent on group activities
- **Collaboration Metrics**: Measure group dynamics and effectiveness

### Group Analytics
- **Performance Insights**: Average grades and peer evaluation scores
- **Group Comparison**: Side-by-side performance comparison
- **Top Performers**: Identify best and worst performing groups
- **Submission Tracking**: Monitor assignment completion rates
- **Visual Indicators**: Color-coded performance badges

---

## 📊 Analytics & Reporting

### Group Work Reports
- **Comprehensive Reports**: Complete overview of groups, assignments, and performance
- **Performance Reports**: Focus on grades, scores, and academic indicators
- **Collaboration Reports**: Analysis of group dynamics and teamwork
- **Individual Progress Reports**: Detailed student contribution tracking

### Individual Contribution Tracking
- **Contribution Types**: Research, writing, presentation, coordination, other
- **Time Tracking**: Record time spent on each activity
- **Quality Ratings**: 1-5 scale rating system
- **Peer Ratings**: Student-to-student evaluation system
- **Teacher Ratings**: Instructor assessment of contributions

### Performance Metrics
- **Academic Performance**: Grades, scores, and completion rates
- **Collaboration Metrics**: Communication effectiveness and participation
- **Productivity Tracking**: Time spent vs. output quality
- **Peer Evaluation Analysis**: Student feedback aggregation

---

## 🐛 Bug Reporting System

### Automatic Error Capture
- **Server-side Errors**: 500, 404, 403, and other HTTP errors
- **Client-side Errors**: JavaScript errors and unhandled promise rejections
- **Validation Errors**: Form validation failures and CSRF errors
- **Database Errors**: SQL errors and connection issues
- **Performance Issues**: Long-running tasks and bottlenecks

### Error Classification
- **Severity Levels**: Critical, High, Medium, Low
- **Error Types**: server_error, client_error, validation_error, database_error
- **Status Tracking**: Open, Investigating, Resolved, Closed

### Tech Staff Management
- **Real-time Notifications**: Instant alerts for new bug reports
- **Assignment System**: Assign bugs to specific tech staff members
- **Status Management**: Track bug resolution progress
- **Export Functionality**: Export bug reports to CSV
- **Filtering and Search**: Find bugs by status, severity, or type

---

## 🗄️ Database Management

### Database Systems
- **SQLite**: Development and testing environment
- **PostgreSQL**: Production environment with full feature support

### Database Operations
- **Automatic Schema Updates**: System automatically handles database migrations
- **Production Fixes**: Comprehensive production database health checks
- **Sample Data**: Automated sample data creation for testing
- **Backup and Recovery**: Database backup and restoration capabilities

### Models
- **User Management**: Students, Teachers, Administrators
- **Academic Structure**: Classes, School Years, Academic Periods
- **Assignment System**: Assignments, Submissions, Grades
- **Group Work**: Groups, Group Assignments, Peer Evaluations
- **Communication**: Messages, Announcements, Notifications
- **Analytics**: Reports, Metrics, Performance Data

---

## 🚀 Deployment & Configuration

### Environment Configuration
- **Development**: Local development with SQLite
- **Production**: Render.com deployment with PostgreSQL
- **Environment Variables**: Secure configuration management
- **Database URLs**: Automatic database connection handling

### Deployment Features
- **Automatic Database Setup**: Database creation and schema updates on deployment
- **Health Checks**: System health monitoring and reporting
- **Error Monitoring**: Comprehensive error tracking and reporting
- **Performance Monitoring**: System performance metrics and optimization

---

## 🔧 Management Tools

### Unified Management Systems
- **Database Manager**: `database_manager.py` - Complete database operations
- **Sample Data Manager**: `sample_data_manager.py` - Automated sample data creation
- **Credential Manager**: `credential_manager.py` - Password and user management
- **Production Manager**: `production_manager.py` - Production fixes and health checks

### Command Line Tools
```bash
# Database Management
python database_manager.py create    # Create all tables
python database_manager.py fresh     # Setup fresh database with admin user

# Sample Data
python sample_data_manager.py        # Create sample data

# Credential Management
python credential_manager.py list    # List all users
python credential_manager.py reset-all password123  # Reset all passwords

# Production Management
python production_manager.py health  # Check database health
python production_manager.py fix-all # Run all production fixes
```

---

## 📁 Project Structure

```
Clara_science_app/
├── app.py                          # Main Flask application
├── app_entry.py                    # Unified entry point
├── models.py                       # Database models
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── render.yaml                     # Render deployment config
├── teacher_routes/                 # Modular teacher functionality
├── management_routes/              # Modular management functionality
├── templates/                      # HTML templates
├── static/                         # CSS, JS, images
├── database_manager.py             # Database operations
├── sample_data_manager.py          # Sample data creation
├── credential_manager.py           # User credential management
├── production_manager.py           # Production fixes
└── backups/                        # Backup directories for consolidated files
```

---

## 🛠️ Development Setup

### Prerequisites
- Python 3.8+
- pip package manager
- Git

### Installation
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Setup database: `python database_manager.py fresh`
6. Create sample data: `python sample_data_manager.py`
7. Run application: `python app_entry.py`

### Development Commands
```bash
# Create fresh database with admin user
python database_manager.py fresh

# Create sample data for testing
python sample_data_manager.py

# Check database health
python production_manager.py health

# Reset all user passwords
python credential_manager.py quick-reset
```

---

## 📞 Support & Maintenance

### System Maintenance
- **Health Monitoring**: Regular database health checks
- **Performance Optimization**: Continuous performance monitoring
- **Security Updates**: Regular security patches and updates
- **Backup Management**: Automated backup creation and verification

### Troubleshooting
- **Database Issues**: Use `production_manager.py health` to diagnose problems
- **User Access**: Use `credential_manager.py` to manage user accounts
- **Sample Data**: Use `sample_data_manager.py` to recreate test data
- **Production Issues**: Use `production_manager.py fix-all` for common fixes

---

## 🔄 Recent Updates

### Codebase Cleanup (Latest)
- **Modular Architecture**: Split monolithic route files into focused modules
- **Unified Management**: Consolidated management scripts into unified systems
- **Improved Organization**: Better file structure and naming conventions
- **Enhanced Maintainability**: Reduced complexity and improved code organization

### Performance Improvements
- **Optimized Imports**: Streamlined import statements and dependencies
- **Database Optimization**: Improved query performance and schema management
- **Frontend Optimization**: Reduced JavaScript and CSS complexity
- **Error Handling**: Enhanced error capture and reporting

---

*This documentation is maintained as part of the Clara Science App project. For technical support or feature requests, please contact the development team.*
