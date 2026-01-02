# Route Migration Plan

## Current State
- **managementroutes.py**: 160 routes (ACTIVE - imported in app.py)
- **management_routes/**: 17 routes (INCOMPLETE - not imported)
- **teacherroutes.py**: 121 routes (ACTIVE - imported in app.py)  
- **teacher_routes/**: 84 routes (MOSTLY COMPLETE - imported in app.py)

## Migration Strategy

### Phase 1: Management Routes Migration
1. Migrate all routes from `managementroutes.py` to appropriate `management_routes/` modules:
   - Dashboard routes → `management_routes/dashboard.py`
   - Student management → `management_routes/students.py`
   - Teacher management → `management_routes/teachers.py`
   - Class management → `management_routes/classes.py`
   - Assignment management → `management_routes/assignments.py`
   - Attendance → `management_routes/attendance.py`
   - Calendar → `management_routes/calendar.py`
   - Communications → `management_routes/communications.py`
   - Reports → `management_routes/reports.py`
   - Administration → `management_routes/administration.py`

### Phase 2: Update app.py
- Change import from `managementroutes` to `management_routes`
- Verify all routes work

### Phase 3: Teacher Routes Migration
- Complete migration of remaining routes from `teacherroutes.py` to `teacher_routes/`

### Phase 4: Cleanup
- Delete `managementroutes.py`
- Delete `teacherroutes.py`
- Verify no broken imports

## Route Count Summary
- Management: 160 routes to migrate (143 missing)
- Teacher: ~37 routes still in old file (84 already migrated)

