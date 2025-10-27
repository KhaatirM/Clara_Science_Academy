# Student Jobs - Score Persistence and Weekly Reset

## Summary
Implemented score persistence for team inspections with automatic weekly reset every Friday at 4:00 PM EST.

## Features

### 1. **Score Persistence**
- Team scores are stored in the database when inspections are conducted
- Scores remain visible until the weekly reset time
- Scores persist across page reloads and navigation

### 2. **Weekly Reset**
- **Reset Time**: Every Friday at 4:00 PM Eastern Time
- **Reset Behavior**: All team scores automatically return to 100 points
- **Reset Logic**: After Friday 4 PM, scores show 100 until a new inspection is conducted

### 3. **Score Display**
- Team cards show the most recent inspection score
- Score persists until:
  - Friday at 4 PM EST (automatic reset)
  - A new inspection is conducted
- Color coding based on score:
  - Green: 80+ points
  - Yellow: 60-79 points
  - Red: Below 60 points

## Technical Implementation

### Backend (`managementroutes.py`)
```python
# Check if it's past Friday 4 PM EST
est = tz('US/Eastern')
now_est = datetime.now(est)
current_day = now_est.weekday()  # 0=Monday, 4=Friday
current_hour = now_est.hour

# Determine if reset is needed
needs_reset = False
if current_day == 4 and current_hour >= 16:  # Friday after 4 PM
    needs_reset = True
elif current_day > 4:  # Saturday or Sunday
    needs_reset = True

# Return appropriate score
if needs_reset:
    current_score = 100
elif recent_inspections:
    current_score = recent_inspections[0].final_score
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

**Week Start**: Monday (scores from 100 unless prior inspection exists)
**Reset Time**: Friday at 4:00 PM EST
**Week End**: Scores reset to 100 after Friday 4 PM until next inspection

## Usage

1. **Recording Inspection**: When an inspection is saved, the score updates immediately
2. **Viewing Score**: Score persists on the team card header
3. **After Reset**: On Friday after 4 PM, all scores show 100 until new inspections
4. **History**: Past inspections are always available via the "History" button

## Benefits

1. **Accountability**: Scores persist throughout the week for students to see
2. **Fresh Start**: Automatic reset each week provides a clean slate
3. **Transparency**: All scores are stored and viewable in inspection history
4. **Motivation**: Visible scores throughout the week encourage good performance

