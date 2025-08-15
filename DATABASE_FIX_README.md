# Database Fix for Missing academic_period_id Column

## Problem
Your production database on Render is missing the `academic_period_id` column in the `assignment` table, causing this error:

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) column assignment.academic_period_id does not exist
```

## Root Cause
The issue occurs because:
1. Your local development uses SQLite, but production uses PostgreSQL
2. The migration file exists but hasn't been run on the production database
3. The `assignment` table is missing several columns that the SQLAlchemy model expects

## Solution Options

### Option 1: Run the Python Script (Recommended)
Use the comprehensive Python script that will check and fix all missing columns:

```bash
# On your local machine, commit and push this script
python fix_production_database.py
```

### Option 2: Run SQL Script Directly
If you have direct database access, run the SQL script:

```sql
-- Connect to your PostgreSQL database and run:
\i fix_database.sql
```

### Option 3: Manual Database Migration
Run the existing Alembic migration on your production database:

```bash
# On your production server
cd /opt/render/project/src
source .venv/bin/activate
alembic upgrade head
```

## What the Scripts Do

### fix_production_database.py
- Checks if required tables exist (`school_year`, `academic_period`, `assignment`)
- Creates missing tables if needed
- Adds missing columns to the `assignment` table:
  - `academic_period_id` (with foreign key constraint)
  - `semester`
  - `is_locked`
  - `created_at`
- Verifies all changes were successful

### fix_database.sql
- SQL script that can be run directly on PostgreSQL
- Adds missing columns with proper constraints
- Shows verification queries

## Required Tables and Columns

The `assignment` table should have these columns:
- `id` (Primary Key)
- `title` (VARCHAR)
- `description` (TEXT)
- `class_id` (Foreign Key to class table)
- `due_date` (TIMESTAMP)
- `quarter` (VARCHAR)
- `semester` (VARCHAR) - **MISSING**
- `academic_period_id` (Foreign Key to academic_period table) - **MISSING**
- `school_year_id` (Foreign Key to school_year table)
- `is_locked` (BOOLEAN) - **MISSING**
- `created_at` (TIMESTAMP) - **MISSING**
- File attachment fields (already present)

## Deployment Steps

1. **Commit and push the fix scripts to GitHub:**
   ```bash
   git add fix_production_database.py fix_database.sql DATABASE_FIX_README.md
   git commit -m "Add database fix scripts for missing academic_period_id column"
   git push origin main
   ```

2. **Deploy to Render:**
   - Render will automatically pull the changes
   - The script will be available in your project

3. **Run the fix script:**
   - SSH into your Render instance or use the Render shell
   - Navigate to your project directory
   - Run: `python fix_production_database.py`

4. **Verify the fix:**
   - Try logging in again
   - The management dashboard should load without errors

## Alternative: Quick Fix via Render Shell

If you want to fix this immediately:

1. Go to your Render dashboard
2. Open the shell for your web service
3. Run these commands:

```bash
cd /opt/render/project/src
source .venv/bin/activate
python fix_production_database.py
```

## Verification

After running the fix, verify the table structure:

```sql
-- Check assignment table columns
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'assignment' 
ORDER BY ordinal_position;

-- Check foreign key constraints
SELECT tc.constraint_name, kcu.column_name, ccu.table_name 
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'assignment';
```

## Notes

- The `academic_period_id` column is nullable, so existing assignments won't break
- Foreign key constraints ensure data integrity
- The script is idempotent - it can be run multiple times safely
- All changes are wrapped in transactions for safety

## Support

If you encounter issues:
1. Check the script output for specific error messages
2. Verify your database connection settings in `config.py`
3. Ensure you have the necessary permissions on your PostgreSQL database
