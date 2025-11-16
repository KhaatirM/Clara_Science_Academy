# Render Shell Migration Instructions

## Deadline Reminders Migration

To set up the deadline reminders feature on Render, you need to run the migration script in Render Shell.

### Step 1: Access Render Shell

1. Go to your Render dashboard
2. Select your service
3. Click on "Shell" tab
4. This will open a terminal session

### Step 2: Run the Migration Script

Run the following command in Render Shell:

```bash
python create_deadline_reminder_tables.py
```

### What This Script Does:

1. ✅ Creates `deadline_reminder` table (if it doesn't exist)
2. ✅ Creates `reminder_notification` table (if it doesn't exist)
3. ✅ Adds `selected_student_ids` column to `deadline_reminder` table (if it doesn't exist)

### Expected Output:

```
Creating deadline_reminder table...
✅ Successfully created deadline_reminder table!
Creating reminder_notification table...
✅ Successfully created reminder_notification table!
Adding selected_student_ids column to deadline_reminder table...
✅ Successfully added 'selected_student_ids' column!
============================================================
✅ Deadline reminder tables migration complete!
============================================================
```

### Alternative: If Tables Already Exist

If you only need to add the `selected_student_ids` column, you can run:

```bash
python add_selected_students_to_deadline_reminder.py
```

### Verification

After running the migration, the deadline reminders feature should work. You can verify by:
1. Going to the deadline reminders page
2. The error message "Deadline reminders feature is not yet available" should no longer appear

