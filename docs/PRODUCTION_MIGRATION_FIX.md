# Production Database Migration - Email Columns Fix

## 🚨 **The Problem**

Your production database on Render is missing the new email columns:
- `user.email`
- `user.google_workspace_email`

**Error Message:**
```
psycopg2.errors.UndefinedColumn: column user.email does not exist
```

This is causing a **500 Internal Server Error** on your production site.

---

## ✅ **The Solution**

Run the migration script on your production server to add the missing columns.

---

## 🚀 **Quick Fix (2 Minutes)**

### **Option 1: Run Migration Script on Render**

1. **Open Render Dashboard**
   - Go to your Clara Science Academy service
   - Click on "Shell" tab

2. **Run the migration command:**
   ```bash
   python migrate_add_email_columns_production.py
   ```

3. **Wait for success message:**
   ```
   ✅ Migration completed successfully!
   ✅ Migration verification PASSED!
   ```

4. **Restart your service** (usually automatic)

5. **Test your site** - Should work now!

### **Option 2: Manual SQL (If Script Fails)**

If the Python script doesn't work, run SQL directly:

1. **Connect to your PostgreSQL database** on Render
2. **Run these SQL commands:**
   ```sql
   ALTER TABLE "user" ADD COLUMN email VARCHAR(120) UNIQUE;
   ALTER TABLE "user" ADD COLUMN google_workspace_email VARCHAR(120) UNIQUE;
   ```
3. **Restart your application**

---

## 📋 **Detailed Steps for Render**

### **Step 1: Access Render Shell**

1. Go to https://dashboard.render.com/
2. Click on your "Clara Science Academy" service
3. Click the **"Shell"** tab at the top
4. Wait for shell to connect

### **Step 2: Navigate to Project Directory**

The shell should already be in your project directory (`/opt/render/project/src`), but verify:

```bash
pwd
# Should show: /opt/render/project/src
```

### **Step 3: Run Migration Script**

```bash
python migrate_add_email_columns_production.py
```

**Expected Output:**
```
======================================================================
Production Database Migration: Add Email Columns to User Table
======================================================================

Current columns in 'user' table: id, username, password_hash, role, student_id, teacher_staff_id, is_temporary_password, password_changed_at, created_at, login_count

⚠️  Column 'email' does NOT exist - will be added
⚠️  Column 'google_workspace_email' does NOT exist - will be added

Adding 2 column(s) to 'user' table...

Adding 'email' column...
✅ Successfully added 'email' column
Adding 'google_workspace_email' column...
✅ Successfully added 'google_workspace_email' column

======================================================================
✅ Migration completed successfully!
======================================================================

Next steps:
1. Restart your application (it should restart automatically on Render)
2. Run 'python populate_google_workspace_emails.py' to populate emails
3. Test the application to ensure everything works

🔍 Verifying migration...

======================================================================
Verifying Migration...
======================================================================

✅ All required columns are present:
   ✅ email
   ✅ google_workspace_email

======================================================================
✅ Migration verification PASSED!
======================================================================
```

### **Step 4: Populate Google Workspace Emails (Optional)**

After migration succeeds, populate emails for existing users:

```bash
python populate_google_workspace_emails.py
```

### **Step 5: Verify Application Works**

1. Go to your production URL: https://clarascienceacademy.org/
2. Try to login
3. Navigate to different pages
4. Check that no errors appear

---

## 🔍 **Verification**

### **Check if Migration Worked**

Run verification command:

```bash
python migrate_add_email_columns_production.py verify
```

**Expected Output:**
```
✅ All required columns are present:
   ✅ email
   ✅ google_workspace_email

✅ Migration verification PASSED!
```

### **Check Database Directly**

If you have direct database access:

```sql
-- Check if columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'user' 
AND column_name IN ('email', 'google_workspace_email');
```

**Expected Result:**
```
column_name              | data_type
-------------------------+-----------
email                    | character varying
google_workspace_email   | character varying
```

---

## ⚠️ **Important Notes**

### **Why This Happened**

1. We updated `models.py` to add the email columns
2. The code was deployed to production
3. But the **database schema wasn't updated**
4. SQLAlchemy tried to query columns that don't exist
5. Result: 500 error

### **The Fix**

The migration script adds the missing columns to match the updated model.

### **This is Normal**

This is a standard part of deploying database schema changes:
1. Update model in code ✅
2. Deploy code ✅
3. **Run migration on database** ← You're here
4. Application works ✅

---

## 🛡️ **Safety Features**

The migration script is **production-safe**:

✅ **Checks before adding** - Won't fail if columns already exist  
✅ **Verification step** - Confirms migration worked  
✅ **Clear error messages** - Tells you exactly what went wrong  
✅ **Rollback safe** - Uses separate transactions  
✅ **No data loss** - Only adds columns, doesn't modify existing data  

---

## 🔧 **Troubleshooting**

### **Issue: "Permission denied" Error**

**Solution:**
- Make sure you're running as the correct user on Render
- Render should have database permissions by default
- Try the manual SQL option instead

### **Issue: "Database connection failed"**

**Solution:**
1. Check that your `DATABASE_URL` environment variable is set correctly
2. Verify database is running on Render
3. Check Render dashboard for database status

### **Issue: "Column already exists" Error**

**This is GOOD!** It means:
- The column was already added
- You can skip this migration
- Your database is up to date

### **Issue: Script hangs or times out**

**Solution:**
1. Cancel the script (Ctrl+C)
2. Use the manual SQL option
3. Run SQL commands directly in Render's PostgreSQL console

---

## 📝 **Manual SQL Commands (Backup Option)**

If the Python script doesn't work, use these SQL commands:

### **Connect to Database**

In Render Dashboard:
1. Go to your PostgreSQL database
2. Click "Connect" → "External Connection"
3. Use the provided connection string with a PostgreSQL client

Or use Render's built-in SQL console.

### **Run These Commands:**

```sql
-- Add email column
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS email VARCHAR(120) UNIQUE;

-- Add google_workspace_email column
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS google_workspace_email VARCHAR(120) UNIQUE;

-- Verify columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'user' 
AND column_name IN ('email', 'google_workspace_email');
```

**Expected Output:**
```
column_name            | data_type          | is_nullable
-----------------------+--------------------+-------------
email                  | character varying  | YES
google_workspace_email | character varying  | YES
```

---

## 🎯 **After Migration**

### **Immediate Next Steps**

1. **Verify site works:**
   - Go to https://clarascienceacademy.org/
   - Login as administrator
   - Navigate to Students tab
   - No errors should appear ✅

2. **Populate emails for existing users:**
   ```bash
   python populate_google_workspace_emails.py
   ```

3. **Test Google Sign-In:**
   - Place `client_secret.json` on production
   - Test with a user who has Google Workspace email
   - Verify login works

### **Long-Term**

- All new users will have emails auto-generated ✅
- Existing users now have email columns ✅
- Google Sign-In ready to use ✅

---

## 📞 **Quick Reference**

### **Commands to Run on Render Shell**

```bash
# 1. Run migration
python migrate_add_email_columns_production.py

# 2. Verify migration
python migrate_add_email_columns_production.py verify

# 3. Populate emails (optional, for existing users)
python populate_google_workspace_emails.py

# 4. Check current emails (optional)
python populate_google_workspace_emails.py show
```

### **What Each Command Does**

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `migrate_add_email_columns_production.py` | Adds missing columns | **Run this first!** |
| `migrate_add_email_columns_production.py verify` | Checks if columns exist | After migration |
| `populate_google_workspace_emails.py` | Fills in emails for existing users | After migration (optional) |
| `populate_google_workspace_emails.py show` | Shows current email settings | Anytime |

---

## ✅ **Summary**

**The Problem:**
- Production database missing `email` and `google_workspace_email` columns
- Causing 500 errors across the site

**The Solution:**
- Run `python migrate_add_email_columns_production.py` on Render
- Adds both columns safely
- Site will work immediately after

**Time Required:** 2-3 minutes

**Risk Level:** Low (script is production-safe)

---

## 🚀 **Run This Now**

```bash
# On Render Shell:
python migrate_add_email_columns_production.py
```

That's it! Your site will be back online immediately after the migration completes.

---

*Production Migration Guide*
*Clara Science Academy - Email Columns Fix*
*Priority: URGENT - Run immediately to restore site functionality*

