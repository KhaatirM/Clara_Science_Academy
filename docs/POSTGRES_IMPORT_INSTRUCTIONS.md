# PostgreSQL Directory Format Import Instructions

## What You Have

Your export file (`2025-11-20T14_32Z.dir.tar.gz`) is in **PostgreSQL custom format** (directory format), not a SQL dump. This format contains `.dat` files that require `pg_restore` to import.

## Option 1: Use pg_restore (Recommended if you have PostgreSQL)

### Step 1: Install PostgreSQL (if not installed)
1. Download PostgreSQL for Windows: https://www.postgresql.org/download/windows/
2. Install it (includes `pg_restore` command)

### Step 2: Extract the files
The files have already been extracted to:
```
C:\Users\admin\Documents\Clara_science_app\database_export\
```

### Step 3: Import to PostgreSQL
Open PowerShell or Command Prompt and run:

```powershell
# Create a new database
createdb clara_science_local

# Import the data (navigate to the database_export directory first)
cd C:\Users\admin\Documents\Clara_science_app\database_export
pg_restore -d clara_science_local -v "2025-11-20T14_32Z\csastudentdb_gaah"
```

Or use the full path:
```powershell
pg_restore -d clara_science_local -v "C:\Users\admin\Documents\Clara_science_app\database_export\2025-11-20T14_32Z\csastudentdb_gaah"
```

### Step 4: Copy to SQLite
After importing to PostgreSQL, run:
```powershell
# Set your PostgreSQL password
$env:PG_PASSWORD = "your_password"

# Run the copy script
python copy_postgres_to_sqlite.py
```

Or update the script with your credentials and run it.

## Option 2: Direct Connection (If you have production DB access)

If you have direct access to the production PostgreSQL database, you can copy data directly:

1. Update `copy_postgres_to_sqlite.py` with your production database credentials
2. Run: `python copy_postgres_to_sqlite.py`

This will copy all data directly from production to your local SQLite database.

## Option 3: Request a SQL Dump Instead

If the above options don't work, you can request a SQL dump format export instead:

```sql
pg_dump -Fp -f export.sql your_database_name
```

This creates a `.sql` file that can be easily converted to SQLite.

## Current Status

✅ Files extracted to: `database_export/2025-11-20T14_32Z/csastudentdb_gaah/`
✅ Contains: Multiple `.dat` files and `toc.dat` (table of contents)
⏳ Next: Import using `pg_restore` or direct connection

## Troubleshooting

### "pg_restore: command not found"
- Install PostgreSQL from the link above
- Make sure PostgreSQL bin directory is in your PATH

### "database already exists"
- Either drop it: `dropdb clara_science_local`
- Or use a different name: `createdb clara_science_local2`

### Connection errors
- Check PostgreSQL is running: `pg_isready`
- Verify credentials
- Check firewall settings

