# Production Database Migration Instructions

## Issue Summary

The production website on Render is encountering an error when users access the dashboard:

```
column grade.is_voided does not exist
```

This occurs because:
1. The database models (`models.py`) expect `is_voided`, `voided_by`, `voided_at`, and `voided_reason` columns
2. The production database tables are missing these columns
3. When SQLAlchemy queries Grade objects, it tries to select these columns and fails

## Solution

We've:
1. ✅ Uncommented the voided fields in the Grade and GroupGrade models in `models.py`
2. ✅ Created a migration script: `migrate_voided_fields_production.py`

## Next Steps: Deploy to Render

### Option 1: Run Migration via Render Shell (Recommended)

1. **Go to your Render Dashboard**: https://dashboard.render.com
2. **Select your service** (the one running your Flask app)
3. **Click on "Shell"** tab or "Connect" → "Shell"
4. **Run the migration**:
   ```bash
   cd /opt/render/project/src
   python migrate_voided_fields_production.py
   ```
5. **Verify success** - you should see output like:
   ```
   ✓ Connected to production database
   Migrating Grade table...
     ✓ Added 'grade.is_voided' column
     ✓ Added 'grade.voided_by' column
     ...
   ✅ Migration completed successfully!
   ```

### Option 2: Deploy and Run in Startup

If you want the migration to run automatically on deployment, you can add this to your `startup.py` or app initialization:

```python
# In your startup.py or app.py
def run_startup_migrations():
    """Run any pending database migrations on startup."""
    try:
        from migrate_voided_fields_production import migrate_database
        migrate_database()
    except Exception as e:
        print(f"Migration warning: {e}")

# Run migrations on startup (in your app initialization)
if __name__ == '__main__':
    run_startup_migrations()
    app.run()
```

**Note**: Only do this if the migration script is idempotent (which it is - it checks if columns exist before adding them).

### Option 3: Run as a One-Time Command

You can add this as a custom command in your Render service settings:
- **Go to**: Settings → Commands
- **Add command**: `python migrate_voided_fields_production.py`
- **Run once** and then remove the command

## Testing Locally First (Optional)

Before running on production, you can test the migration script locally:

1. Set up your local environment to connect to production database:
   ```bash
   export DATABASE_URL="your-production-database-url"
   ```

2. Run the migration:
   ```bash
   python migrate_voided_fields_production.py
   ```

## What the Migration Does

The script adds 4 columns to each of 2 tables:

### `grade` table:
- `is_voided` (BOOLEAN, default FALSE)
- `voided_by` (INTEGER, nullable)
- `voided_at` (TIMESTAMP, nullable)
- `voided_reason` (TEXT, nullable)

### `group_grade` table:
- `is_voided` (BOOLEAN, default FALSE)
- `voided_by` (INTEGER, nullable)
- `voided_at` (TIMESTAMP, nullable)
- `voided_reason` (TEXT, nullable)

## Important Notes

- ✅ The migration is **safe to run multiple times** - it checks if columns exist before adding them
- ✅ It uses `ALTER TABLE` which is non-destructive
- ✅ Default values ensure existing data works correctly (is_voided = FALSE)
- ⚠️ **Backup your database** before running any migration (Render does this automatically)

## Verification

After running the migration, verify it worked:

1. **Check Render logs** - no more "column does not exist" errors
2. **Try accessing the dashboard** - should load without errors
3. **Check database directly** (if you have access):
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'grade' AND column_name LIKE '%void%';
   ```

## Rollback Plan

If something goes wrong, you can remove the added columns:

```sql
-- Only run these if you need to rollback
ALTER TABLE grade DROP COLUMN is_voided;
ALTER TABLE grade DROP COLUMN voided_by;
ALTER TABLE grade DROP COLUMN voided_at;
ALTER TABLE grade DROP COLUMN voided_reason;

ALTER TABLE group_grade DROP COLUMN is_voided;
ALTER TABLE group_grade DROP COLUMN voided_by;
ALTER TABLE group_grade DROP COLUMN voided_at;
ALTER TABLE group_grade DROP COLUMN voided_reason;
```

Then re-comment the fields in models.py and redeploy.

## Contact

If you encounter any issues, check the Render logs and ensure:
- DATABASE_URL is set correctly
- The service has database access permissions
- The script is run from the correct directory

