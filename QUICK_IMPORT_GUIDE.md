# Quick PostgreSQL Import Guide

## Step 1: Find PostgreSQL Installation

PostgreSQL tools need to be in your PATH or you need to use the full path. Common locations:

- `C:\Program Files\PostgreSQL\15\bin` (or 14, 16, etc.)
- `C:\Program Files\PostgreSQL\*\bin`

## Step 2: Add PostgreSQL to PATH (Optional but Recommended)

1. Find your PostgreSQL installation folder
2. Add the `bin` folder to your system PATH
3. Restart PowerShell

Or use the full path in commands below.

## Step 3: Import the Database

### Option A: Using the PowerShell Script (Easiest)

```powershell
.\import_with_pg_restore.ps1
```

This script will:
- Find PostgreSQL automatically
- Create the database
- Import the data
- Guide you through the process

### Option B: Manual Commands

1. **Find the database directory:**
   ```powershell
   Get-ChildItem -Path database_export -Recurse -Filter "toc.dat"
   ```
   Note the full path to the directory containing `toc.dat`

2. **Create the database:**
   ```powershell
   # Using full path (replace with your PostgreSQL version)
   & "C:\Program Files\PostgreSQL\15\bin\createdb.exe" -U postgres clara_science_local
   ```

3. **Import the data:**
   ```powershell
   # Replace the path with the directory containing toc.dat
   & "C:\Program Files\PostgreSQL\15\bin\pg_restore.exe" -U postgres -d clara_science_local -v "database_export\2025-11-20T14_32Z\csastudentdb_gaah"
   ```

   You'll be prompted for the postgres user password.

## Step 4: Copy to SQLite

After successful import to PostgreSQL:

1. **Set your PostgreSQL password** (if needed):
   ```powershell
   $env:PGPASSWORD = "your_postgres_password"
   ```

2. **Update the copy script** with your credentials:
   Edit `copy_postgres_to_sqlite.py` and set:
   ```python
   pg_user = 'postgres'
   pg_password = 'your_password'
   pg_host = 'localhost'
   pg_port = '5432'
   pg_database = 'clara_science_local'
   ```

3. **Run the copy script:**
   ```powershell
   python copy_postgres_to_sqlite.py
   ```

## Troubleshooting

### "pg_restore: command not found"
- Use the full path to pg_restore.exe
- Or add PostgreSQL bin to your PATH

### "password authentication failed"
- Make sure PostgreSQL is running
- Check your postgres user password
- You may need to set `PGPASSWORD` environment variable

### "database already exists"
- Drop it first: `dropdb -U postgres clara_science_local`
- Or use a different database name

### "connection refused"
- Make sure PostgreSQL service is running
- Check it's listening on the correct port (default: 5432)

