# Production Database Fix - Missing Grade and Assignment Columns

## Problem
The production PostgreSQL database is missing several columns that are defined in the models, causing 500 errors when users try to login:

1. **Grade table missing columns:**
   - `extra_credit_points` (DOUBLE PRECISION)
   - `late_penalty_applied` (DOUBLE PRECISION)
   - `days_late` (INTEGER)

2. **Assignment table missing columns:**
   - `total_points` (DOUBLE PRECISION)

## Error Messages
```
(psycopg2.errors.UndefinedColumn) column grade.extra_credit_points does not exist
(psycopg2.errors.UndefinedColumn) column assignment.total_points does not exist
```

## Solution

### Option 1: Run Python Script on Production (Recommended)

1. **Access Render Shell:**
   - Go to your Render dashboard
   - Navigate to your web service
   - Click on "Shell" tab
   - This opens a terminal in the production environment

2. **Run the Migration Script:**
   ```bash
   cd /opt/render/project/src
   python add_missing_grade_and_assignment_columns.py
   ```

3. **Verify Success:**
   - The script will show which columns were added
   - Check the output for success messages like:
     - `[OK] Successfully added 'extra_credit_points' column to 'grade' table`
     - `[OK] Successfully added 'total_points' column to 'assignment' table`

### Option 2: Run SQL Script Directly

If you have direct PostgreSQL database access:

1. **Access PostgreSQL Database:**
   - Go to your Render dashboard
   - Navigate to your PostgreSQL database
   - Click on "Connect" or "Query" tab

2. **Execute SQL:**
   ```sql
   -- Add missing columns to grade table
   ALTER TABLE grade ADD COLUMN IF NOT EXISTS extra_credit_points DOUBLE PRECISION DEFAULT 0.0 NOT NULL;
   ALTER TABLE grade ADD COLUMN IF NOT EXISTS late_penalty_applied DOUBLE PRECISION DEFAULT 0.0 NOT NULL;
   ALTER TABLE grade ADD COLUMN IF NOT EXISTS days_late INTEGER DEFAULT 0 NOT NULL;
   
   -- Add missing column to assignment table
   ALTER TABLE assignment ADD COLUMN IF NOT EXISTS total_points DOUBLE PRECISION DEFAULT 100.0 NOT NULL;
   ```

### Option 3: Manual Column Addition

If the above methods don't work, manually add the columns one by one:

```sql
-- Grade table columns
ALTER TABLE grade ADD COLUMN extra_credit_points DOUBLE PRECISION DEFAULT 0.0 NOT NULL;
ALTER TABLE grade ADD COLUMN late_penalty_applied DOUBLE PRECISION DEFAULT 0.0 NOT NULL;
ALTER TABLE grade ADD COLUMN days_late INTEGER DEFAULT 0 NOT NULL;

-- Assignment table column
ALTER TABLE assignment ADD COLUMN total_points DOUBLE PRECISION DEFAULT 100.0 NOT NULL;
```

## Verification

After running any of the above solutions, verify the fix by:

1. **Check Columns Exist:**
   ```sql
   -- Check grade table columns
   SELECT column_name, data_type, column_default
   FROM information_schema.columns 
   WHERE table_name = 'grade' 
   AND column_name IN ('extra_credit_points', 'late_penalty_applied', 'days_late')
   ORDER BY column_name;
   
   -- Check assignment table column
   SELECT column_name, data_type, column_default
   FROM information_schema.columns 
   WHERE table_name = 'assignment' 
   AND column_name = 'total_points';
   ```

2. **Test the Application:**
   - Try logging in as a student
   - Try logging in as a School Administrator
   - Check that dashboards load without 500 errors

## Notes

- The migration script is **idempotent** - it checks if columns exist before adding them, so it's safe to run multiple times
- All columns have default values, so existing data will not be affected
- The script uses PostgreSQL-specific syntax (`DOUBLE PRECISION` instead of `FLOAT`)

## After Fix

Once the columns are added, the application should work normally. Users will be able to:
- Login without errors
- Access student dashboards
- Access management dashboards
- View and manage assignments
- View and manage grades

