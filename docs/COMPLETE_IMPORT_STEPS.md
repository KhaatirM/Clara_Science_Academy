# Complete Database Import Steps

## Step 1: Import to PostgreSQL

Run the import script. You'll be prompted for your PostgreSQL password:

```powershell
.\RUN_IMPORT.ps1
```

**OR** set the password as an environment variable first:

```powershell
$env:PGPASSWORD = "your_postgres_password"
.\RUN_IMPORT.ps1
```

This will:
- Create database `clara_science_local`
- Import all data from the export

## Step 2: Copy from PostgreSQL to SQLite

After the import succeeds, copy the data to SQLite:

```powershell
# Set password (if not already set)
$env:PGPASSWORD = "your_postgres_password"

# Copy to SQLite
python copy_postgres_to_sqlite.py
```

This will copy all tables from PostgreSQL to your local SQLite database at `instance/app.db`.

## Step 3: Run Migrations

Add the new fields for the grading enhancements:

```powershell
# Add total_points field
python add_total_points_column.py

# Add enhancement fields (extra credit, late penalty, etc.)
python add_enhancement_fields_migration.py
```

## Step 4: Verify and Test

1. **Start the server:**
   ```powershell
   python app_entry.py
   ```

2. **Test the application:**
   - Log in with your credentials
   - Check that data is visible
   - Test creating assignments with custom points
   - Test the new grading features

## Troubleshooting

### "password authentication failed"
- Make sure PostgreSQL service is running
- Verify your password is correct
- Check that the postgres user exists

### "database already exists"
- The script will drop and recreate it, or
- Manually drop it: `dropdb -U postgres clara_science_local`

### "connection refused"
- Make sure PostgreSQL service is running
- Check it's listening on port 5432

### Import takes a long time
- This is normal for large databases
- Be patient, it may take several minutes

## Quick Command Summary

```powershell
# 1. Set password (one time)
$env:PGPASSWORD = "your_password"

# 2. Import to PostgreSQL
.\RUN_IMPORT.ps1

# 3. Copy to SQLite
python copy_postgres_to_sqlite.py

# 4. Run migrations
python add_total_points_column.py
python add_enhancement_fields_migration.py

# 5. Start server
python app_entry.py
```

