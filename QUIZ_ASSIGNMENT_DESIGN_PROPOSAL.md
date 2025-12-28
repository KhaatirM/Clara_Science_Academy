# Quiz Assignment Design Proposal
## Google Forms Integration & Versatile Structure

---

## 🎯 Core Principles

1. **Flexibility First**: Support both native quiz creation AND Google Forms import
2. **Seamless Integration**: Easy import/export between Google Forms and native quizzes
3. **Teacher-Friendly**: Simple, intuitive interface for quiz creation
4. **Comprehensive Question Types**: Support all major question formats
5. **Auto-Grading**: Automatic grading where possible, manual review for subjective questions

---

## 📐 Database Structure Recommendations

### Current Structure (Good Foundation)
- ✅ `Assignment` model with `assignment_type = 'quiz'`
- ✅ `QuizQuestion` model (question_text, question_type, points, order)
- ✅ `QuizOption` model (for multiple choice/true-false)
- ✅ `QuizAnswer` model (student responses)
- ✅ `QuizProgress` model (save & continue functionality)

### Recommended Additions

#### 1. Add to `Assignment` Model:
```python
# Google Forms Integration
google_form_id = db.Column(db.String(255), nullable=True)  # Google Form ID
google_form_url = db.Column(db.String(500), nullable=True)  # Full URL to Google Form
google_form_linked = db.Column(db.Boolean, default=False, nullable=False)  # Is it linked to Google Form?

# Quiz-Specific Settings
quiz_settings = db.Column(db.Text, nullable=True)  # JSON: time_limit, shuffle_questions, show_correct_answers, etc.
allow_multiple_attempts = db.Column(db.Boolean, default=False, nullable=False)
max_attempts = db.Column(db.Integer, default=1, nullable=False)
show_results_immediately = db.Column(db.Boolean, default=True, nullable=False)
```

#### 2. Enhance `QuizQuestion` Model:
```python
# Add these fields:
explanation = db.Column(db.Text, nullable=True)  # Explanation shown after answering
required = db.Column(db.Boolean, default=True, nullable=False)  # Is question required?
image_url = db.Column(db.String(500), nullable=True)  # Optional image for question
google_question_id = db.Column(db.String(255), nullable=True)  # ID from Google Forms (if imported)
```

#### 3. New Model: `QuizAttempt`
```python
class QuizAttempt(db.Model):
    """Track individual quiz attempts when multiple attempts are allowed."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)
    time_taken_minutes = db.Column(db.Integer, nullable=True)
    score = db.Column(db.Float, nullable=True)  # Calculated score
    total_points = db.Column(db.Float, nullable=True)
    
    student = db.relationship('Student', backref='quiz_attempts')
    assignment = db.relationship('Assignment', backref='quiz_attempts')
```

---

## 🔄 Quiz Creation Flow

### Option 1: Native Quiz Builder (Recommended for Starting)
1. **Basic Info** → Title, Description, Class, Due Date, Quarter
2. **Quiz Settings** → Time limit, attempts, randomization, feedback options
3. **Question Builder** → Add/edit/reorder questions
4. **Preview & Publish**

### Option 2: Google Forms Import (Phase 2)
1. **Basic Info** → Title, Description, Class, Due Date, Quarter
2. **Google Forms Link** → Paste Google Form URL or select from linked account
3. **Import & Sync** → Import questions and settings
4. **Review & Customize** → Edit imported quiz if needed
5. **Sync Options** → One-time import OR two-way sync

### Option 3: Hybrid Approach (Most Flexible)
Allow teachers to:
- Create quiz natively in the system
- Import from Google Forms
- **Link existing Google Form** (keep it in Google, just track submissions here)
- **Export native quiz to Google Forms**

---

## 🎨 User Interface Design

### Quiz Creation Form Structure:

```
┌─────────────────────────────────────────────────────────┐
│  CREATE QUIZ ASSIGNMENT                                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  [TABS]                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│  │  Build   │ │  Import  │ │  Link    │                │
│  │  Native  │ │  Google  │ │  Google  │                │
│  │          │ │  Form    │ │  Form    │                │
│  └──────────┘ └──────────┘ └──────────┘                │
│                                                           │
│  Basic Information:                                       │
│  ├─ Quiz Title *                                          │
│  ├─ Description                                           │
│  ├─ Class *                                               │
│  ├─ Due Date *                                            │
│  └─ Quarter *                                             │
│                                                           │
│  Quiz Settings:                                           │
│  ├─ Time Limit (minutes) [ ] No limit                    │
│  ├─ Attempts [ ] Multiple [Max: 1]                       │
│  ├─ Question Order [ ] Shuffle questions                 │
│  ├─ Answer Feedback [ ] Show immediately                 │
│  └─ Show Correct Answers [ ] After submission            │
│                                                           │
│  Questions Section:                                       │
│  ├─ [+ Add Question] Button                              │
│  │                                                       │
│  └─ Question List (Drag to reorder)                      │
│     ├─ Q1: Multiple Choice (2 points)                    │
│     ├─ Q2: True/False (1 point)                          │
│     └─ Q3: Short Answer (3 points)                       │
│                                                           │
│  [Cancel] [Save Draft] [Publish Quiz]                    │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Question Types to Support

### 1. **Multiple Choice** (Auto-gradeable)
- Question text
- 2-10 answer options
- One or multiple correct answers
- Points per question
- Explanation (shown after submission)

### 2. **True/False** (Auto-gradeable)
- Question text
- Correct answer (True/False)
- Points per question
- Explanation

### 3. **Short Answer** (Manual or keyword-based grading)
- Question text
- Acceptable answers (keywords or exact match)
- Case sensitivity option
- Points per question

### 4. **Essay/Long Answer** (Manual grading only)
- Question text
- Character/word limit (optional)
- Rubric reference (optional)
- Points per question

### 5. **Matching** (Auto-gradeable, Phase 2)
- Items on left, options on right
- Drag-and-drop matching

### 6. **Fill in the Blank** (Keyword-based grading)
- Question with blanks: "The capital of France is ____"
- Acceptable answers for each blank

---

## 🔗 Google Forms Integration Strategy

### Level 1: Import Google Form (One-Time)
1. Teacher pastes Google Form URL
2. System authenticates via Google OAuth (reuse existing tokens)
3. Fetch form structure via Google Forms API
4. Convert Google Form questions → Native QuizQuestion/QuizOption
5. Store `google_form_id` for reference

**API Endpoint**: `GET https://forms.googleapis.com/v1/forms/{formId}`

### Level 2: Link Google Form (Two-Way Sync)
1. Link existing Google Form
2. Track submissions from Google Forms
3. Sync grades back to internal system
4. Optional: Auto-create quiz in system based on Form responses

### Level 3: Export to Google Form
1. Convert native quiz → Google Form format
2. Create new Google Form via API
3. Share form with students
4. Import responses back

**API Endpoint**: `POST https://forms.googleapis.com/v1/forms`

### Required Google API Scopes:
```python
GOOGLE_FORMS_SCOPES = [
    'https://www.googleapis.com/auth/forms.body',  # Read/write form structure
    'https://www.googleapis.com/auth/forms.responses.readonly',  # Read responses
    'https://www.googleapis.com/auth/drive',  # Create forms in Drive
]
```

---

## 📝 Suggested Implementation Phases

### **Phase 1: Native Quiz Builder** (Start Here)
✅ Priority: HIGH
- Basic quiz creation form
- Support Multiple Choice, True/False, Short Answer, Essay
- Question reordering (drag & drop)
- Basic auto-grading for MC/True-False
- Quiz settings (time limit, attempts)
- Student quiz-taking interface
- Teacher grading interface

**Estimated Time**: 2-3 weeks

### **Phase 2: Google Forms Import** 
✅ Priority: MEDIUM
- Google Forms API integration
- Import form structure → Native quiz
- Map Google question types → Native question types
- Handle edge cases (unsupported question types)

**Estimated Time**: 1-2 weeks

### **Phase 3: Google Forms Link (Read-Only)**
✅ Priority: MEDIUM
- Link existing Google Form
- Track submissions via Google Forms API
- Import grades/scores to internal system
- Display form URL to students

**Estimated Time**: 1 week

### **Phase 4: Advanced Features**
✅ Priority: LOW
- Export native quiz → Google Form
- Two-way sync
- Matching questions
- Fill-in-the-blank
- Question banks
- Question randomization

**Estimated Time**: 2-3 weeks

---

## 🎯 Recommended Starting Point

**Start with Phase 1: Native Quiz Builder**

### Why?
1. ✅ Teachers have full control
2. ✅ No external dependencies
3. ✅ Faster to implement
4. ✅ Easier to test and debug
5. ✅ Can add Google Forms integration later

### Core Features for MVP:
1. **Quiz Creation Form**
   - Basic assignment info (reuse existing assignment form structure)
   - Quiz-specific settings section
   - Question builder with add/edit/delete/reorder

2. **Question Builder Component**
   - Question type selector
   - Rich text editor for question text
   - Dynamic options (for multiple choice)
   - Points assignment
   - Required/optional toggle

3. **Student Quiz Interface**
   - Clean, distraction-free interface
   - Question navigation
   - Timer (if time limit set)
   - Save progress
   - Submit quiz

4. **Grading System**
   - Auto-grade multiple choice/true-false
   - Manual grading for short answer/essay
   - Bulk grading interface for teachers

---

## 🔐 Security & Permissions

1. **Quiz Access**: Only enrolled students can take quiz
2. **Time Limits**: Enforced server-side, prevent late submissions
3. **Multiple Attempts**: Track and limit attempts per student
4. **Answer Visibility**: Control when correct answers are shown
5. **Question Shuffling**: Randomize on server, not client-side
6. **Google OAuth**: Reuse existing Google authentication system

---

## 📊 Data Flow Example

### Creating a Native Quiz:
```
Teacher fills form → POST /create-quiz
  ↓
Create Assignment record
  ↓
For each question → Create QuizQuestion + QuizOptions
  ↓
Calculate total_points from all questions
  ↓
Return success → Redirect to quiz view
```

### Student Taking Quiz:
```
Student clicks "Take Quiz" → GET /quiz/{id}/take
  ↓
Check QuizProgress (resume or start new)
  ↓
Load questions (shuffled if enabled)
  ↓
Student answers → Save to QuizAnswer (via AJAX)
  ↓
Student submits → Calculate score
  ↓
Create/Update Grade record
  ↓
Show results (if enabled)
```

---

## 🚀 Next Steps

1. **Review & Approve** this design proposal
2. **Decide on Phase 1 scope** - which features are essential for MVP?
3. **Create detailed wireframes** for quiz builder interface
4. **Set up development branch** for quiz feature
5. **Implement database migrations** for new fields
6. **Build quiz creation form** UI
7. **Implement question builder** component
8. **Create student quiz-taking interface**
9. **Build grading system**

---

## ❓ Questions to Consider

1. **Question Ordering**: Drag-and-drop or simple up/down arrows?
2. **Question Images**: Allow file uploads or just URLs?
3. **Question Banks**: Need ability to save/reuse questions?
4. **Partial Credit**: Award partial points for multiple-choice with multiple correct answers?
5. **Question Feedback**: Immediate feedback per question or only after submission?
6. **Google Forms Sync**: One-time import or ongoing sync?
7. **Export Options**: Export quiz to PDF for paper versions?

---

**Ready to proceed?** Let's start with Phase 1 implementation! 🎉

