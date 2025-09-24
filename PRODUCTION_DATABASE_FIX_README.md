# Production Database Fix - Missing Assignment Columns

## Problem
The production database on Render is missing the following columns in the `assignment` table:
- `allow_save_and_continue` (BOOLEAN)
- `max_save_attempts` (INTEGER) 
- `save_timeout_minutes` (INTEGER)

This is causing PostgreSQL errors when accessing the management dashboard:
```
(psycopg2.errors.UndefinedColumn) column assignment.allow_save_and_continue does not exist
```

## Solution Options

### Option 1: Run Python Script (Recommended)
1. **Access Render Shell**:
   - Go to your Render dashboard
   - Navigate to your web service
   - Click on "Shell" tab
   - This opens a terminal in the production environment

2. **Run the Fix Script**:
   ```bash
   python fix_production_assignment_columns_postgres.py
   ```

3. **Verify Success**:
   - The script will show which columns were added
   - Check the output for success messages

### Option 2: Run SQL Script Directly
1. **Access PostgreSQL Database**:
   - Go to your Render dashboard
   - Navigate to your PostgreSQL database
   - Click on "Connect" or "Query" tab

2. **Execute SQL**:
   - Copy and paste the contents of `fix_assignment_columns_production.sql`
   - Run the script
   - Check the output for success messages

### Option 3: Manual Column Addition
If the above methods don't work, manually add the columns:

```sql
-- Add missing columns
ALTER TABLE assignment ADD COLUMN allow_save_and_continue BOOLEAN DEFAULT FALSE;
ALTER TABLE assignment ADD COLUMN max_save_attempts INTEGER DEFAULT 3;
ALTER TABLE assignment ADD COLUMN save_timeout_minutes INTEGER DEFAULT 30;
```

## Verification
After running any of the above solutions, verify the fix by:

1. **Check Columns Exist**:
   ```sql
   SELECT column_name, data_type, column_default
   FROM information_schema.columns 
   WHERE table_name = 'assignment' 
   AND column_name IN ('allow_save_and_continue', 'max_save_attempts', 'save_timeout_minutes')
   ORDER BY column_name;
   ```

2. **Test Application**:
   - Try logging in as a School Administrator
   - Access the management dashboard
   - Should work without errors

## Expected Results
After the fix, you should see:
- ✅ `allow_save_and_continue`: boolean (default: false)
- ✅ `max_save_attempts`: integer (default: 3)
- ✅ `save_timeout_minutes`: integer (default: 30)

## Troubleshooting

### If Python Script Fails:
- Ensure `psycopg2` is installed in production
- Check that `DATABASE_URL` environment variable is set
- Verify database connection permissions

### If SQL Script Fails:
- Check PostgreSQL user permissions
- Ensure the user has `ALTER TABLE` privileges
- Try running individual `ALTER TABLE` statements

### If Manual Addition Fails:
- Check if columns already exist
- Verify table name is correct (`assignment`)
- Check for any existing constraints or indexes

## Prevention
To prevent this issue in the future:
1. Always test database migrations locally first
2. Use Flask-Migrate for schema changes
3. Run migrations in production after deployment
4. Verify column existence before accessing in code

## Files Created
- `fix_production_assignment_columns_postgres.py` - Python script to fix the issue
- `fix_assignment_columns_production.sql` - SQL script to fix the issue
- `PRODUCTION_DATABASE_FIX_README.md` - This documentation

## Support
If you continue to have issues:
1. Check Render logs for detailed error messages
2. Verify database connection settings
3. Ensure all environment variables are properly set
4. Contact support if needed
