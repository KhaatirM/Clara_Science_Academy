# Grade Levels Migration Guide

## Problem
The application is crashing with the error `column class.grade_levels does not exist` because the production database (PostgreSQL) doesn't have the new `grade_levels` column that was added to the Class model.

## Solution
You need to add the `grade_levels` column to the `class` table in your production database.

## Migration Options

### Option 1: Through Web Interface (Recommended for Render)
1. Deploy the updated code to Render
2. Visit: `https://your-app-name.onrender.com/migrate/add-grade-levels`
3. The migration will run automatically and show a success message

### Option 2: Using the Python script
1. Deploy the updated code to Render
2. Run: `python add_grade_levels_via_app.py` in the Render shell

### Option 3: Direct SQL (if you have database access)
Run this SQL command directly on your production PostgreSQL database:

```sql
ALTER TABLE class ADD COLUMN grade_levels VARCHAR(100);
```

### Option 4: Using Flask-Migrate (if you have access to the deployment environment)
1. Run: `flask db migrate -m "Add grade_levels to class table"`
2. Run: `flask db upgrade`

## After Migration
Once the column is added to the database:

1. **Uncomment the grade_levels field in models.py:**
   ```python
   # Change this line:
   # grade_levels = db.Column(db.String(100), nullable=True)  # Temporarily commented out until migration is applied
   
   # To this:
   grade_levels = db.Column(db.String(100), nullable=True)  # Store as comma-separated string like "3,4,5"
   ```

2. **Update the helper methods in models.py:**
   ```python
   def get_grade_levels(self):
       """Return grade levels as a list of integers"""
       if not self.grade_levels:
           return []
       return [int(grade.strip()) for grade in self.grade_levels.split(',') if grade.strip()]
   
   def set_grade_levels(self, grade_list):
       """Set grade levels from a list of integers"""
       if grade_list:
           self.grade_levels = ','.join(map(str, sorted(grade_list)))
       else:
           self.grade_levels = None
   
   def get_grade_levels_display(self):
       """Return grade levels as a formatted string for display"""
       grades = self.get_grade_levels()
       if not grades:
           return "Not specified"
       if len(grades) == 1:
           return f"Grade {grades[0]}"
       elif len(grades) == 2:
           return f"Grades {grades[0]} & {grades[1]}"
       else:
           return f"Grades {', '.join(map(str, grades[:-1]))} & {grades[-1]}"
   ```

3. **Deploy the updated code**

## Current Status
- ✅ Model temporarily disabled to prevent crashes
- ✅ Migration files created
- ✅ Application should work without grade levels feature
- ⏳ Waiting for database migration to be applied
- ⏳ Need to re-enable grade_levels field after migration

## Testing
After applying the migration and re-enabling the field:
1. Go to Edit Class page
2. You should see the multi-select grade levels field
3. Select multiple grade levels (e.g., Grades 3, 4, 5)
4. Save the class
5. View the class to see the grade levels displayed
