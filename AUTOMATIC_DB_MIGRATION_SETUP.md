# Automatic Database Migration Setup for Render

## Overview
This setup ensures that your production database is automatically fixed whenever the application is deployed or restarted on Render.

## What Was Implemented

### 1. **Automatic Database Fix in App Startup** (`app.py`)
- Added `run_production_database_fix()` function that automatically runs when the app starts
- Only runs in production environment (when `RENDER` environment variable is present)
- Safely checks for existing columns before adding them
- Handles errors gracefully without breaking the application

### 2. **Build Script** (`build.sh`)
- Optional build script that can be configured in Render
- Runs database fix during the build process
- Ensures database is ready before application starts

### 3. **Render Configuration** (`render.yaml`)
- Configuration file for Render deployment
- Includes database fix in build command
- Sets up proper environment variables

### 4. **One-time Fix Script** (`run_db_fix_once.py`)
- Simple script for manual execution
- Can be run via Render shell if needed

## How It Works

### Automatic Fix (Recommended)
The database fix now runs **automatically** every time the application starts on Render:

1. **App Startup**: When Flask app starts, it calls `run_production_database_fix()`
2. **Environment Check**: Only runs if `DATABASE_URL` and `RENDER` environment variables are present
3. **Column Check**: Queries the database to see which columns are missing
4. **Safe Addition**: Adds only missing columns with proper defaults
5. **Error Handling**: Continues app startup even if database fix fails

### Build-time Fix (Alternative)
If you prefer to run the fix during build instead of startup:

1. **Configure Render**: Set build command to include database fix
2. **Build Process**: Database fix runs during deployment
3. **App Starts**: Application starts with database already fixed

## Setup Instructions

### Option 1: Automatic Fix (Already Implemented)
✅ **No additional setup needed!** The fix is already integrated into your app.

### Option 2: Build-time Fix
1. **Go to Render Dashboard**
2. **Navigate to your web service**
3. **Go to Settings → Build & Deploy**
4. **Update Build Command**:
   ```bash
   pip install -r requirements.txt && python fix_production_assignment_columns_postgres.py
   ```

### Option 3: Manual Fix (One-time)
If you need to run it manually:
1. **Go to Render Dashboard → Your Service → Shell**
2. **Run**:
   ```bash
   python run_db_fix_once.py
   ```

## Environment Variables Required

Make sure these are set in your Render service:
- ✅ `DATABASE_URL` - Your PostgreSQL connection string
- ✅ `RENDER` - Automatically set by Render (indicates production environment)

## What Gets Fixed

The automatic fix adds these missing columns to the `assignment` table:
- `allow_save_and_continue` (BOOLEAN, default: FALSE)
- `max_save_attempts` (INTEGER, default: 3)
- `save_timeout_minutes` (INTEGER, default: 30)

## Monitoring

### Check Logs
After deployment, check your Render logs for these messages:
- ✅ `🔧 Running production database fix...`
- ✅ `✓ All required columns already exist` (if already fixed)
- ✅ `✅ Production database fix completed successfully!`

### Verify Fix
Test your application:
1. **Login as School Administrator**
2. **Access Management Dashboard**
3. **Should work without PostgreSQL errors**

## Troubleshooting

### If Automatic Fix Doesn't Work:
1. **Check Environment Variables**: Ensure `DATABASE_URL` and `RENDER` are set
2. **Check Logs**: Look for error messages in Render logs
3. **Manual Fix**: Run the one-time fix script via Render shell
4. **Verify Dependencies**: Ensure `psycopg2` is in requirements.txt

### If Build-time Fix Fails:
1. **Check Build Command**: Ensure syntax is correct
2. **Check Dependencies**: Verify `psycopg2` is installed
3. **Check Permissions**: Ensure database user has ALTER TABLE permissions

## Files Created/Modified

- ✅ `app.py` - Added automatic database fix function
- ✅ `build.sh` - Build script with database fix
- ✅ `render.yaml` - Render configuration
- ✅ `run_db_fix_once.py` - Manual fix script
- ✅ `AUTOMATIC_DB_MIGRATION_SETUP.md` - This documentation

## Benefits

1. **Zero Manual Intervention**: Database fixes happen automatically
2. **Safe Operation**: Only adds missing columns, doesn't modify existing data
3. **Error Resilient**: App continues to work even if fix fails
4. **Production Only**: Only runs in production environment
5. **One-time Operation**: Once fixed, subsequent startups skip the fix

## Next Steps

1. **Deploy to Render**: Push your changes to trigger automatic fix
2. **Monitor Logs**: Check that database fix runs successfully
3. **Test Application**: Verify management dashboard works
4. **Remove Manual Scripts**: Optional - clean up manual fix scripts once confirmed working

Your application will now automatically handle database schema updates on every deployment! 🎉
