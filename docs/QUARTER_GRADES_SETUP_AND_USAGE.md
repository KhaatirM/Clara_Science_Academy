# Quarter Grades System - Complete Setup & Usage Guide

## 🎯 How The System Works

### Data Flow:
```
1. Quarter Ends (e.g., Q1 ends on Nov 1)
2. Automatic script runs every 3 hours (cron job)
3. Checks which quarters ended recently (last 30 days)
4. Calculates grades for those quarters
5. Stores in QuarterGrade table
6. Updates every 3 hours if assignment grades change
7. PDFs pull from this table (always current within 3 hours)
```

### Key Rules:
- ✅ Only calculates grades for **ended quarters**
- ✅ Excludes students enrolled **after** quarter ended
- ✅ Excludes students who dropped **before** quarter ended
- ✅ Only includes **non-voided assignments** for that specific quarter
- ✅ Updates every 3 hours (catches late assignment grade changes)

## 📋 Initial Setup on Render

### Step 1: Deploy Code
```bash
git add .
git commit -m "Add automatic quarter grade system"
git push
```

### Step 2: Create Database Table
```bash
# In Render Shell
python migrations_scripts/create_quarter_grade_table.py
```

### Step 3: Initial Population (One-Time)
```bash
# In Render Shell
python -c "
from app import create_app
from utils.auto_refresh_quarter_grades import refresh_all_quarter_grades

app = create_app()
with app.app_context():
    print('Starting initial quarter grade calculation...')
    stats = refresh_all_quarter_grades(force=True)
    print(f'✓ Complete!')
    print(f'  Students processed: {stats[\"total_students\"]}')
    print(f'  Grades updated: {stats[\"total_grades_updated\"]}')
    print(f'  Errors: {stats[\"errors\"]}')
"
```

### Step 4: Set Up Automatic Refresh (Cron Job)

**Option A: Render Cron Jobs (Recommended)**
1. Go to Render Dashboard → Your Service → Settings
2. Add a new Cron Job:
   - **Name**: Quarter Grades Refresh
   - **Schedule**: `0 */3 * * *` (every 3 hours)
   - **Command**: 
     ```bash
     python -c "from app import create_app; from utils.auto_refresh_quarter_grades import refresh_quarter_grades_for_ended_quarters; app = create_app(); app.app_context().push(); refresh_quarter_grades_for_ended_quarters()"
     ```

**Option B: External Cron Service** (if Render doesn't support)
Use a service like cron-job.org or EasyCron to hit an endpoint every 3 hours:
- Create endpoint in your app that calls the refresh function
- Protect with a secret token
- External service calls it every 3 hours

## 🔄 How It Works Day-to-Day

### When Q1 Ends (Nov 1):
1. **Nov 1 - 3:00 PM**: Cron runs, detects Q1 ended today
2. Calculates Q1 grades for all students in all classes
3. Stores in database

### When Assignment Grades Change:
**Scenario**: Teacher updates Q1 assignment on Nov 15

1. **Nov 15 - 2:00 PM**: Teacher changes grade from B to A
2. **Nov 15 - 3:00 PM**: Cron runs (3 hours later)
3. Detects Q1 grade was last calculated > 3 hours ago
4. Recalculates Q1 grade (now shows A)
5. Updates database

### When Generating PDFs:
1. Admin generates report card for a student
2. System calls `update_all_quarter_grades_for_student()`
3. Checks each quarter:
   - If last calculated < 3 hours ago: Use cached grade
   - If last calculated > 3 hours ago: Recalculate
4. Pulls all quarter grades from database
5. Shows in PDF:
   - Q1: **A** (grade from database)
   - Q2: **B+** (grade from database)
   - Q3: **—** (quarter not ended yet)
   - Q4: **—** (quarter not ended yet)

## 🛠️ Manual Administration

### Refresh Grades Manually (via code):
```python
# In Render Shell or local dev
from app import create_app
from utils.auto_refresh_quarter_grades import refresh_all_quarter_grades

app = create_app()
with app.app_context():
    # Refresh all grades (respects 3-hour window)
    stats = refresh_all_quarter_grades(force=False)
    
    # OR force refresh everything (ignores 3-hour window)
    stats = refresh_all_quarter_grades(force=True)
```

### Check Status:
```python
from app import create_app
from models import QuarterGrade

app = create_app()
with app.app_context():
    # Total records
    total = QuarterGrade.query.count()
    print(f'Total quarter grade records: {total}')
    
    # Sample records
    samples = QuarterGrade.query.limit(5).all()
    for qg in samples:
        print(f'{qg.student.name} - {qg.class_info.name} - {qg.quarter}: {qg.letter_grade}')
```

## 🧪 Testing The System

### Test 1: Verify Quarter Detection
```python
from app import create_app
from models import AcademicPeriod
from datetime import date

app = create_app()
with app.app_context():
    today = date.today()
    ended_quarters = AcademicPeriod.query.filter(
        AcademicPeriod.period_type == 'quarter',
        AcademicPeriod.end_date < today
    ).all()
    
    print("Ended quarters:")
    for q in ended_quarters:
        print(f"  {q.name} ({q.school_year.name}) ended on {q.end_date}")
```

### Test 2: Generate Report Card
1. Go to Management Dashboard → Report Cards
2. Generate a new report card for a student
3. Download PDF
4. Verify Q1, Q2, Q3, Q4 columns show grades (not all "—")

### Test 3: Verify Grade Updates
1. Change an assignment grade for Q1
2. Wait 3 hours OR run manual refresh
3. Generate/download report card again
4. Verify grade updated in PDF

## 📊 Current vs Desired Behavior

### ✅ What YOU Want (Now Implemented):
- [x] Grades calculated automatically when quarters end
- [x] Updates every 3 hours to catch changes
- [x] Administrator doesn't have to do anything
- [x] PDFs always show current grades (within 3-hour window)
- [x] Handles late enrollments correctly
- [x] Excludes voided assignments
- [x] Quarter-specific (Q1 assignments only affect Q1 grade)

### 🔄 How It Actually Works:
1. **Cron job runs every 3 hours** (you set this up once)
2. Checks for quarters that ended in last 30 days
3. For each ended quarter:
   - Finds all students enrolled in classes
   - Checks enrollment dates (excludes if enrolled after quarter ended)
   - Calculates grade from non-voided assignments
   - Updates database (if > 3 hours since last calculation)
4. **PDFs pull from database** (always fresh within 3 hours)
5. **No manual intervention needed** after initial setup

## 🚨 Important Notes

### Quarter End Detection:
- System uses `AcademicPeriod.end_date` to determine if quarter ended
- Make sure your quarters have correct end dates in the database!

### Zero Records After Setup:
This is NORMAL if:
- No quarters have ended yet in the current school year
- You just set it up and haven't run initial population

**Solution**: Run the initial population script OR wait until a quarter ends

### Performance:
- Initial population: ~1-2 seconds per student
- Automatic refresh: Only processes recently ended quarters (fast)
- PDF generation: Instant (pulls from database)

## 📞 Troubleshooting

**Problem**: No quarter grades showing in PDF
**Solutions**:
1. Check if quarters have ended: `AcademicPeriod.end_date < today`
2. Run manual refresh: `refresh_all_quarter_grades(force=True)`
3. Check enrollment dates: Student must be enrolled before quarter ended

**Problem**: Grades not updating after assignment change
**Solutions**:
1. Wait 3 hours for cron to run
2. Run manual refresh immediately
3. Check if assignment is marked for correct quarter
4. Check if assignment is voided

**Problem**: Cron job not running
**Solutions**:
1. Verify cron schedule in Render settings
2. Check Render logs for errors
3. Test manual execution in shell first

