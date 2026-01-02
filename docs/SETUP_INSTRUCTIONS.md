# Setup Instructions for Enhanced Grading System

## Prerequisites
- Python environment set up
- Database connection configured
- All dependencies installed (`pip install -r requirements.txt`)

## Step 1: Run Database Migrations

### Migration 1: Add Total Points Field
```bash
python add_total_points_column.py
```

This adds the `total_points` field to both `assignment` and `group_assignment` tables.

### Migration 2: Add Enhancement Fields
```bash
python add_enhancement_fields_migration.py
```

This adds all the enhancement fields:
- Extra credit fields
- Late penalty fields
- Grade scale field
- Assignment category and weight fields
- Grade history table
- Grade extra credit and late penalty fields

## Step 2: Connect Local Database to PostgreSQL Export

### Option A: Import PostgreSQL Dump to Local SQLite (for testing)
If you have a PostgreSQL dump file:

1. **Convert PostgreSQL dump to SQLite format** (if needed):
   ```bash
   # Use pg_dump to export
   pg_dump -h your_host -U your_user -d your_database > export.sql
   
   # Or use a conversion tool
   # Note: Some manual adjustments may be needed
   ```

2. **Update your local config** to use the exported data:
   - Copy the database file to your local project
   - Update `config.py` or `.env` with the database path

### Option B: Use PostgreSQL Locally
1. **Install PostgreSQL locally** (if not already installed)
2. **Import your database dump**:
   ```bash
   createdb clara_science_local
   psql clara_science_local < export.sql
   ```

3. **Update your local config**:
   ```python
   # In config.py or .env
   SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/clara_science_local'
   ```

### Option C: Use SQLAlchemy to Migrate Data
Create a script to copy data from PostgreSQL to SQLite:

```python
# migrate_data.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# PostgreSQL connection
pg_engine = create_engine('postgresql://user:password@host/database')
pg_session = sessionmaker(bind=pg_engine)()

# SQLite connection
sqlite_engine = create_engine('sqlite:///local_database.db')
sqlite_session = sessionmaker(bind=sqlite_engine)()

# Copy data (example for assignments)
from models import Assignment

pg_assignments = pg_session.query(Assignment).all()
for assignment in pg_assignments:
    sqlite_session.merge(assignment)

sqlite_session.commit()
```

## Step 3: Verify Migrations

### Check Tables
```python
from app import create_app
from extensions import db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    
    # Check assignment table
    assignment_columns = [col['name'] for col in inspector.get_columns('assignment')]
    required_fields = [
        'total_points', 'allow_extra_credit', 'max_extra_credit_points',
        'late_penalty_enabled', 'late_penalty_per_day', 'late_penalty_max_days',
        'grade_scale', 'assignment_category', 'category_weight'
    ]
    
    for field in required_fields:
        if field in assignment_columns:
            print(f"✓ {field} exists")
        else:
            print(f"✗ {field} missing")
    
    # Check grade_history table
    tables = inspector.get_table_names()
    if 'grade_history' in tables:
        print("✓ grade_history table exists")
    else:
        print("✗ grade_history table missing")
```

## Step 4: Test the Features

### Test Assignment Creation
1. Start the development server:
   ```bash
   python app_entry.py
   ```

2. Log in as a teacher or administrator

3. Create a new assignment:
   - Navigate to "Create Assignment"
   - Fill in basic details
   - Set custom total points (e.g., 150)
   - Enable extra credit (set max to 10 points)
   - Enable late penalty (10% per day)
   - Set assignment category (e.g., "Tests")
   - Set category weight (e.g., 30%)

4. Verify the assignment was created with all fields

### Test Grading
1. Navigate to the grading page for an assignment
2. Enter grades for students
3. Verify:
   - Points are displayed correctly
   - Percentage is calculated correctly
   - Letter grades use the grade scale

### Test Statistics
1. After grading some students, check statistics
2. Verify:
   - Average, median, min, max are calculated
   - Grade distribution is shown

## Step 5: Troubleshooting

### Migration Errors
- **"Column already exists"**: The field was already added. This is fine, continue.
- **"Table doesn't exist"**: Run `db.create_all()` first to create tables.
- **"Foreign key constraint"**: Make sure all referenced tables exist.

### Data Import Issues
- **Encoding errors**: Ensure the dump file uses UTF-8 encoding
- **Type mismatches**: PostgreSQL and SQLite have different types. Adjust as needed.
- **Missing data**: Check that all required fields have default values

### Feature Not Working
- Check that migrations ran successfully
- Verify the fields exist in the database
- Check browser console for JavaScript errors
- Check server logs for Python errors

## Database Schema Reference

### Assignment Table - New Fields
```sql
total_points FLOAT DEFAULT 100.0
allow_extra_credit BOOLEAN DEFAULT FALSE
max_extra_credit_points FLOAT DEFAULT 0.0
late_penalty_enabled BOOLEAN DEFAULT FALSE
late_penalty_per_day FLOAT DEFAULT 0.0
late_penalty_max_days INTEGER DEFAULT 0
grade_scale TEXT
assignment_category VARCHAR(50)
category_weight FLOAT DEFAULT 0.0
```

### Grade Table - New Fields
```sql
extra_credit_points FLOAT DEFAULT 0.0
late_penalty_applied FLOAT DEFAULT 0.0
days_late INTEGER DEFAULT 0
```

### GradeHistory Table - New Table
```sql
CREATE TABLE grade_history (
    id INTEGER PRIMARY KEY,
    grade_id INTEGER,
    student_id INTEGER,
    assignment_id INTEGER,
    previous_grade_data TEXT,
    new_grade_data TEXT NOT NULL,
    changed_by INTEGER NOT NULL,
    changed_at TIMESTAMP NOT NULL,
    change_reason TEXT,
    FOREIGN KEY (grade_id) REFERENCES grade(id),
    FOREIGN KEY (student_id) REFERENCES student(id),
    FOREIGN KEY (assignment_id) REFERENCES assignment(id),
    FOREIGN KEY (changed_by) REFERENCES user(id)
)
```

## Next Steps After Setup

1. **Test all features** with sample data
2. **Train teachers** on the new features
3. **Document** any custom configurations
4. **Backup** the database after successful migration
5. **Deploy** to production after thorough testing

## Support

If you encounter issues:
1. Check the migration script output for errors
2. Review the database schema
3. Check application logs
4. Verify all dependencies are installed
5. Ensure database connection is working

