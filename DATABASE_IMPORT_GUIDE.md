# Database Import Guide

## Where to Place Your Database Export File

### Option 1: Project Root (Recommended)
Place your downloaded file (`2025-11-20T14_32Z.dir.tar.gz`) in the project root directory:
```
C:\Users\admin\Documents\Clara_science_app\2025-11-20T14_32Z.dir.tar.gz
```

### Option 2: Downloads Folder
If the file is in your Downloads folder, the import script will find it automatically:
```
C:\Users\admin\Downloads\2025-11-20T14_32Z.dir.tar.gz
```

### Option 3: Custom Location
You can place it anywhere and provide the full path when running the import script.

## Import Methods

### Method 1: Automated Import Script (Recommended for SQLite)

1. **Place the file** in the project root or Downloads folder

2. **Run the import script**:
   ```bash
   python import_database_export.py
   ```
   
   Or with a specific path:
   ```bash
   python import_database_export.py "C:\path\to\your\2025-11-20T14_32Z.dir.tar.gz"
   ```

3. **The script will**:
   - Extract the tar.gz file
   - Convert PostgreSQL format to SQLite (if needed)
   - Import into `instance/app.db`
   - Create a backup of existing database if one exists

### Method 2: Manual PostgreSQL Import (If you have PostgreSQL installed)

If you have PostgreSQL installed locally:

1. **Extract the tar.gz file**:
   ```bash
   tar -xzf 2025-11-20T14_32Z.dir.tar.gz
   ```

2. **Import to PostgreSQL**:
   ```bash
   createdb clara_science_local
   psql clara_science_local < path/to/extracted/dump.sql
   ```

3. **Update your config** to use PostgreSQL:
   ```python
   # In config.py or .env file
   DATABASE_URL = 'postgresql://username:password@localhost/clara_science_local'
   ```

### Method 3: Using pgloader (Best for Complex Conversions)

If you have `pgloader` installed:

1. **Install pgloader** (if not installed):
   - Windows: Download from https://github.com/dimitri/pgloader/releases
   - Or use WSL: `sudo apt-get install pgloader`

2. **Load directly from PostgreSQL to SQLite**:
   ```bash
   pgloader postgresql://user:pass@host/dbname sqlite:///instance/app.db
   ```

## File Structure After Extraction

The tar.gz file likely contains:
- A `.sql` dump file (PostgreSQL format)
- Or a directory with database files

The import script will automatically detect and handle both formats.

## Database Location

Your local SQLite database will be created at:
```
C:\Users\admin\Documents\Clara_science_app\instance\app.db
```

This is the default location configured in `config.py`.

## Troubleshooting

### Issue: "File not found"
- Make sure the file path is correct
- Check that the file exists in the specified location
- Use absolute path if relative path doesn't work

### Issue: "Conversion errors"
- PostgreSQL to SQLite conversion may require manual adjustments
- Some PostgreSQL-specific features don't translate directly
- Consider using Method 2 (PostgreSQL) or Method 3 (pgloader)

### Issue: "Database locked"
- Close any applications using the database
- Make sure Flask app is not running
- Try again after a few seconds

### Issue: "Encoding errors"
- Ensure the SQL dump is UTF-8 encoded
- The script handles UTF-8 by default

## After Import

1. **Run migrations** to add new fields:
   ```bash
   python add_total_points_column.py
   python add_enhancement_fields_migration.py
   ```

2. **Verify the import**:
   ```bash
   python -c "from app import create_app; from extensions import db; from models import Assignment; app = create_app(); app.app_context().push(); print(f'Assignments: {Assignment.query.count()}')"
   ```

3. **Start the server**:
   ```bash
   python app_entry.py
   ```

## Next Steps

After successfully importing:
1. Test the application with real data
2. Verify all features work correctly
3. Test the new grading enhancements
4. Create test assignments with the new features

