# 🚨 URGENT: Production Database Fix

## **Your Site is Down - Here's the 2-Minute Fix**

---

## ❌ **The Problem**

```
Error: column user.email does not exist
```

Your production database is missing the new email columns we added.

---

## ✅ **The Fix (2 Minutes)**

### **Step 1: Open Render Shell**

1. Go to https://dashboard.render.com/
2. Click your "Clara Science Academy" service
3. Click **"Shell"** tab
4. Wait for shell to connect

### **Step 2: Run This Command**

```bash
python migrate_add_email_columns_production.py
```

### **Step 3: Wait for Success**

You'll see:
```
✅ Successfully added 'email' column
✅ Successfully added 'google_workspace_email' column
✅ Migration completed successfully!
```

### **Step 4: Done!**

Your site will automatically restart and work again.

---

## 🎯 **That's It!**

**Time:** 2 minutes  
**Risk:** None (safe migration)  
**Result:** Site back online ✅

---

## 📞 **If Script Doesn't Work**

Run this SQL instead:

```sql
ALTER TABLE "user" ADD COLUMN email VARCHAR(120) UNIQUE;
ALTER TABLE "user" ADD COLUMN google_workspace_email VARCHAR(120) UNIQUE;
```

---

## ✅ **Verification**

After running, test:
1. Go to https://clarascienceacademy.org/
2. Try to login
3. Navigate to Students tab
4. Should work with no errors ✅

---

*Run the migration NOW to restore your site!*

