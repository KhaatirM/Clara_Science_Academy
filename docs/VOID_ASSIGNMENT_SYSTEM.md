# Assignment Voiding System - Complete Implementation

## ✅ Features Implemented

### 1. **Void Assignment for All Students**
Administrators and teachers can void entire assignments, removing them from grade calculations.

### 2. **Void Assignment for Specific Students**
Target specific students (useful for late enrollments, special circumstances).

### 3. **Automatic Quarter Grade Recalculation**
When voiding, quarter grades are immediately recalculated for affected students.

### 4. **Works for Both Assignment Types**
- ✅ Individual assignments
- ✅ Group assignments

## 🎯 Who Can Void Assignments

### **School Administrators/Directors**
- Can void ANY assignment in ANY class
- Access via: **Assignments & Grades** → Select class → Click void button on assignment column

### **Teachers**
- Can void assignments ONLY in THEIR OWN classes
- Same interface as administrators
- Authorization checked automatically

## 📋 User Interface

### **Access Points:**

**Management Dashboard:**
1. Go to **Assignments & Grades**
2. Select a class
3. View grades table
4. Each assignment column header has a void button (🚫 icon)

**Teacher Dashboard:**
1. Go to **My Classes** → Select class
2. View grades table  
3. Same void buttons on assignment columns

### **Void Modal Features:**

Click the void button (🚫) on any assignment header to open modal:

```
┌──────────────────────────────────────┐
│ 🚫 Void Assignment                   │
├──────────────────────────────────────┤
│ ⚠️ Warning: This excludes assignment │
│    from grade calculations. Quarter  │
│    grades recalculate immediately.   │
│                                      │
│ Assignment: Math Quiz #3             │
│                                      │
│ Void for:                           │
│ ○ All Students                       │
│   Void for every student in class    │
│                                      │
│ ○ Specific Students                  │
│   Choose which students              │
│                                      │
│ [Student checkboxes appear when      │
│  "Specific Students" is selected]    │
│                                      │
│ Reason:                              │
│ ┌──────────────────────────────┐   │
│ │ Assignment canceled...        │   │
│ └──────────────────────────────┘   │
│                                      │
│   [Cancel]  [Void Assignment]        │
└──────────────────────────────────────┘
```

## 🔄 What Happens When You Void

### **Immediate Actions:**
1. ✅ Grade marked as `is_voided = True`
2. ✅ Records who voided it (`voided_by = user.id`)
3. ✅ Records when (`voided_at = timestamp`)
4. ✅ Records why (`voided_reason = "Assignment canceled"`)
5. ✅ **Quarter grade recalculated immediately** (excludes voided assignment)
6. ✅ Quarter grade updated in QuarterGrade table
7. ✅ Page reloads showing updated grades

### **Effects on Reports:**
- ❌ Voided assignment excluded from quarter average
- ❌ Voided assignment excluded from report cards
- ❌ Voided assignment excluded from GPA calculations
- ✅ Still visible in database (audit trail)
- ✅ Can be un-voided if needed (using existing void-grade endpoint)

## 💡 Use Cases

### **Use Case 1: Cancel Assignment for Everyone**
**Scenario:** Teacher decides to cancel a difficult quiz that confused all students.

**Steps:**
1. Go to class grades view
2. Click void button on "Difficult Quiz" column
3. Select: **All Students**
4. Reason: "Quiz canceled due to technical issues"
5. Click "Void Assignment"

**Result:**
- All 25 student grades for this quiz marked as voided
- Quarter averages recalculated for all 25 students
- Quarter grades updated in database
- Report cards will NOT include this assignment

### **Use Case 2: Void for Late Enrollment**
**Scenario:** Student enrolled on September 15, but there's an August 20 assignment they shouldn't be responsible for.

**Steps:**
1. Go to class grades view
2. Click void button on "August Assignment"
3. Select: **Specific Students**
4. Check: "John Smith" (late enrollee)
5. Reason: "Student enrolled after assignment was due"
6. Click "Void Assignment"

**Result:**
- Only John Smith's grade for this assignment voided
- John's quarter average recalculated (excluding this assignment)
- Other students unaffected

### **Use Case 3: Group Assignment Issue**
**Scenario:** One group had technical problems with a group project.

**Steps:**
1. Go to class grades view
2. Click void button on "Group Project" column
3. Select: **Specific Students**
4. Check all members of the affected group
5. Reason: "Technical issues prevented submission"
6. Click "Void Assignment"

**Result:**
- Group members' grades voided
- Their quarter averages recalculated
- Other groups' grades unaffected

## 🔐 Security & Authorization

### **Permissions:**
- **Administrators**: Can void any assignment, any class
- **Teachers**: Can only void assignments in classes they teach
- **Students**: No void permissions

### **Authorization Checks:**
```python
# Teachers can only void their own class assignments
if not is_admin() and teacher and assignment.class_info.teacher_id != teacher.id:
    return jsonify({'success': False, 'message': 'Not authorized'}), 403
```

### **Audit Trail:**
Every void operation records:
- Who voided it (`voided_by`)
- When it was voided (`voided_at`)
- Why it was voided (`voided_reason`)

## 📊 Database Schema

### **Grade Table (Already Exists):**
```python
is_voided = Boolean (default: False)
voided_by = Integer (FK to User)
voided_at = DateTime
voided_reason = Text
```

### **GroupGrade Table (Already Exists):**
Same fields as Grade table

### **QuarterGrade Table (New):**
Automatically recalculates when assignments are voided

## 🛠️ Technical Details

### **Routes Added:**

**Management:**
- `POST /management/void-assignment/<assignment_id>`

**Teachers:**
- `POST /teacher/void-assignment/<assignment_id>`

### **Parameters:**
```
assignment_type: 'individual' or 'group'
student_ids: [] (array of student IDs, empty = void all)
void_all: 'true' or 'false'
reason: string (explanation for voiding)
csrf_token: string (security)
```

### **Response:**
```json
{
  "success": true,
  "message": "Voided assignment 'Math Quiz' for all students (25 grades)",
  "voided_count": 25
}
```

### **Quarter Grade Integration:**
```python
# After voiding, immediately update quarter grades
update_quarter_grade(
    student_id=student_id,
    class_id=class_id,
    school_year_id=school_year_id,
    quarter=quarter,
    force=True  # Force immediate recalculation
)
```

## 📁 Files Modified/Created

### Modified:
- `managementroutes.py` - Added void_assignment_for_students route
- `teacherroutes.py` - Added void_assignment_for_students route (with authorization)
- `templates/management/class_grades.html` - Added void buttons and modal

### Created:
- `management_routes/void_assignments.py` - Original blueprint (not used, merged into main routes)
- `VOID_ASSIGNMENT_SYSTEM.md` - This documentation

## 🧪 Testing Checklist

After deployment:
- [ ] **Admin - Void All Students:**
  - Go to Assignments & Grades → Select class
  - Click void button on an assignment
  - Select "All Students"
  - Enter reason
  - Submit
  - Verify all grades voided
  - Check quarter grades recalculated

- [ ] **Admin - Void Specific Students:**
  - Click void button
  - Select "Specific Students"
  - Check 2-3 students
  - Submit
  - Verify only those students' grades voided

- [ ] **Teacher - Void Assignment:**
  - Login as teacher
  - Go to My Classes → Select class
  - Click void on assignment
  - Select "All Students"
  - Verify works

- [ ] **Teacher - Authorization:**
  - Teacher should NOT be able to void assignments in other teachers' classes
  - Verify error message appears

- [ ] **Quarter Grades Update:**
  - Before voiding: Note student's Q1 average
  - Void an assignment
  - Check quarter_grade table
  - Verify percentage updated

- [ ] **Report Card Impact:**
  - Generate report card before voiding
  - Void an assignment
  - Generate report card again
  - Verify different grade shown

## 🎓 Training Notes

### For Administrators:
"When you need to remove an assignment from grade calculations (canceled assignment, technical issues, etc.), use the void button on the assignment column. You can void for all students or select specific students. Quarter grades will update automatically."

### For Teachers:
"If you need to cancel an assignment or exclude certain students from an assignment's grade, click the void button (🚫) on the assignment column header. This immediately recalculates quarter grades."

## ⚠️ Important Notes

1. **Voiding vs Deleting:**
   - Voiding keeps the grade in database (marked as voided)
   - Deleting removes completely
   - Voiding is PREFERRED (maintains audit trail)

2. **Un-voiding:**
   - Currently can un-void individual grades via existing `/void-grade` endpoint
   - Could add bulk un-void functionality in future

3. **Quarter Grade Impact:**
   - Voiding immediately triggers quarter grade recalculation
   - This can take a few seconds for large classes
   - Users see success message after completion

4. **Group Assignments:**
   - Voiding group assignment affects all members of the group
   - When selecting specific students, only their group's grade is voided
   - Other groups unaffected


