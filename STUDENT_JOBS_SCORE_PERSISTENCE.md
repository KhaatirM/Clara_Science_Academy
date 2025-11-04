# Student Jobs - Score Persistence and Weekly Reset

## Summary
Implemented score persistence for team inspections with automatic weekly reset every Monday at 12:00 AM EST (midnight).

## Features

### 1. **Score Persistence**
- Team scores are stored in the database when inspections are conducted
- Scores remain visible until the weekly reset time
- Scores persist across page reloads and navigation

### 2. **Weekly Reset**
- **Reset Time**: Every Monday at 12:00 AM (midnight) Eastern Time
- **Reset Behavior**: All team scores automatically return to 100 points
- **Reset Logic**: At the start of each week (Monday midnight), scores reset to 100 until a new inspection is conducted

### 3. **Score Display**
- Team cards show the most recent inspection score
- Score persists until:
  - Monday at 12:00 AM EST (automatic reset)
  - A new inspection is conducted
- Color coding based on score:
  - Green: 80+ points
  - Yellow: 60-79 points
  - Red: Below 60 points

## Technical Implementation

### Backend (`managementroutes.py`)
```python
# Calculate the start of the current week (Monday at 12:00 AM EST)
est = tz('US/Eastern')
now_est = datetime.now(est)
current_weekday = now_est.weekday()  # 0=Monday, 6=Sunday
days_since_monday = current_weekday
current_week_start = now_est.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)

# Get most recent inspection and check if it's from this week
if recent_inspections:
    latest_inspection = recent_inspections[0]
    inspection_datetime = est.localize(latest_inspection.inspection_date) if latest_inspection.inspection_date.tzinfo is None else latest_inspection.inspection_date.astimezone(est)
    
    if inspection_datetime < current_week_start:
        # Inspection is from last week - reset to 100
        current_score = 100
    else:
        # Inspection is from this week - use its score
        current_score = latest_inspection.final_score
else:
    current_score = 100
```

### Template (`templates/management/student_jobs.html`)
- Displays score from database via `team_entry.current_score`
- Dynamically updates when new inspection is completed
- Persists across page navigation

## Dependencies
- **pytz**: Added to `requirements.txt` for timezone handling
- Required for accurate EST time calculations

## Reset Schedule

**Week Start**: Monday at 12:00 AM (midnight) EST
**Reset Time**: Every Monday at 12:00 AM EST
**Reset Behavior**: All scores reset to 100 at the start of each week

## Usage

1. **Recording Inspection**: When an inspection is saved, the score updates immediately
2. **Viewing Score**: Score persists on the team card header throughout the week
3. **After Reset**: Every Monday at midnight, all scores reset to 100 until new inspections are conducted
4. **History**: Past inspections are always available via the "History" button

## Benefits

1. **Accountability**: Scores persist throughout the week for students to see
2. **Fresh Start**: Automatic reset each week provides a clean slate
3. **Transparency**: All scores are stored and viewable in inspection history
4. **Motivation**: Visible scores throughout the week encourage good performance

