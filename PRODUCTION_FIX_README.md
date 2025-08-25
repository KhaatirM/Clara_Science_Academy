# Production Database Fix for Teacher Dashboard

## Problem
The teacher dashboard is failing on the production server (Render) with this error:
```
psycopg2.errors.UndefinedColumn: column teacher_staff.middle_initial does not exist
```

This happens because the production PostgreSQL database doesn't have the new columns we added to the `teacher_staff` table.

## Solution
We need to add the missing columns to the production database. Here are two ways to do this:

## Option 1: Run the Python Migration Script (Recommended)

1. **Deploy the migration script** to your Render environment
2. **Run the script** in your Render shell or add it to your deployment process
3. **The script will automatically**:
   - Connect to your production database
   - Check which columns are missing
   - Add all required columns
   - Verify the changes

### Steps:
1. Make sure `migrate_production_database.py` is in your codebase
2. Ensure `psycopg2-binary` is in your `requirements.txt`
3. Deploy to Render
4. Run the script in your Render shell:
   ```bash
   python migrate_production_database.py
   ```

## Option 2: Run SQL Commands Manually

If you prefer to run SQL commands directly:

1. **Access your Render database** (via Render dashboard or psql)
2. **Run the SQL commands** from `production_migration.sql`
3. **Verify the changes** by checking the table structure

### Steps:
1. Go to your Render dashboard
2. Find your database service
3. Click "Connect" and choose "psql"
4. Copy and paste the contents of `production_migration.sql`

## Required Columns to Add

The following columns need to be added to the `teacher_staff` table:

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `middle_initial` | VARCHAR(1) | Middle initial |
| `dob` | VARCHAR(20) | Date of birth |
| `staff_ssn` | VARCHAR(20) | Social Security Number |
| `assigned_role` | VARCHAR(100) | Assigned role (e.g., "Math Teacher") |
| `subject` | VARCHAR(200) | Primary subject(s) taught |
| `employment_type` | VARCHAR(20) | Full Time, Part Time |
| `grades_taught` | TEXT | JSON string of grades taught |
| `resume_filename` | VARCHAR(255) | Resume file name |
| `other_document_filename` | VARCHAR(255) | Other document file name |
| `image` | VARCHAR(255) | Profile image file name |

## Verification

After running the migration, verify that all columns exist by running:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'teacher_staff' 
ORDER BY ordinal_position;
```

## Expected Result

Once the migration is complete:
- ✅ Teacher dashboard will load without errors
- ✅ All new teacher/staff fields will be accessible
- ✅ Edit functionality will work properly
- ✅ No more "column does not exist" errors

## Troubleshooting

If you encounter issues:

1. **Check your DATABASE_URL** environment variable in Render
2. **Ensure psycopg2-binary is installed** in your requirements.txt
3. **Verify database permissions** - your database user needs ALTER TABLE privileges
4. **Check Render logs** for any connection or permission errors

## Notes

- The migration script uses `IF NOT EXISTS` to avoid errors if columns already exist
- All new columns are nullable to avoid breaking existing data
- The script will automatically detect which columns are missing
- This is a safe migration that won't affect existing data
