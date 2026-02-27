# Group Assignments: Types, Collaboration & Submission

## How do the 3 options (PDF/Paper, Quiz, Discussion) categorize as group assignments?

Group assignments use the **same three types** as individual assignments. When you create a group assignment, you first choose the type on the **Create Group Assignment** screen:

| Type | Description | Group assignment flow |
|------|-------------|------------------------|
| **PDF/Paper** | File attachments, instructions, reports/essays | One submission per **group**. One student uploads the file on behalf of the group. |
| **Quiz** | Multiple question types, auto-grading | **Not fully supported:** Creation/DB exist; no student "take group quiz" flow—only individual quizzes work. | Group or individual answers: teacher can allow “individual submissions” (each student answers) or one set of answers per group. |
| **Discussion** | Structured prompts, threads, participation | Discussion threads can be used per group or per assignment; students participate in the discussion (group participation tracking). |

So “group” is **who does the work** (groups of students), not a fourth type. Each of the three types can be created as either an **individual** assignment or a **group** assignment.

---

## How do students collaborate on the website and submit?

### 1. **Groups are set up by teachers/admins**

- Classes have **Student Groups** (e.g. Group A, Group B). Students are assigned to a group via **Student Group Members**.
- A group assignment can apply to **all groups** in the class or to **selected groups** only.

### 2. **PDF/Paper group assignments**

- **Collaboration:** Not in-app. Students are expected to work together **outside** the app (e.g. Google Docs, meeting in person, shared drive).
- **Submission:** **One submission per group.** Any member of the group can submit:
  - They upload **one file** (and optional notes) for the whole group.
  - The system stores this as a **GroupSubmission** (group_id, submitted_by = that student).
- **Where:** Students see the assignment on their dashboard (with a “Group” badge). They click **Submit**, upload the file in the submission modal; the app should POST to `/student/submit/group/<assignment_id>` so the backend treats it as a group submission.

### 3. **Quiz group assignments**

- **Current status:** **Creation only.** Teachers can create a group quiz; the DB has GroupQuizQuestion, GroupQuizOption, GroupQuizAnswer. There is **no student route** that loads a group quiz or saves GroupQuizAnswer. The student "Take Quiz" flow only works with **individual** Assignment quizzes. So quiz does **not** currently function as a real group assignment for students.
- **If implemented later:** Collaboration would be in-app (group or per-student answers); submission would store GroupQuizAnswer tied to group_id and/or student_id.
- **Collaboration (if implemented):** Depends on teacher settings:
  - **“Allow individual submissions”** (optional): Each student in the group can submit their own answers (GroupQuizAnswer has both group_id and student_id).
  - Otherwise: One set of answers per group (group submits together).
- **Submission:** Students take the quiz from the dashboard (“Take Quiz”). Answers are stored in **GroupQuizAnswer** (and optionally tied to group and/or student).

### 4. **Discussion group assignments**

- **Collaboration:** In-app. Students participate in **discussion threads** (prompts, replies). The system can track “group participation” and peer interaction.
- **Submission:** There is no single “Submit” file; participation in the discussion (posts, replies) is the deliverable. Students click **Discuss** to open the discussion.

---

## Summary table

| Type        | Where collaboration happens      | How submission works on the website                          |
|------------|-----------------------------------|--------------------------------------------------------------|
| **PDF/Paper** | Outside the app (Docs, etc.)     | One person in the group uploads one file via Submit → group submission. |
| **Quiz**      | Not implemented for students     | Group quiz creation exists; no student "take group quiz" or GroupQuizAnswer submission flow. |
| **Discussion**| In-app (threads, posts)          | No file upload; participation in the discussion is the submission.   |

---

## Technical notes

- **GroupSubmission:** One row per group per (group) assignment; `submitted_by` = student who uploaded; `group_id` = their group.
- **GroupGrade:** One grade per **student** per group assignment (so every group member gets the same grade for that assignment, or it can be individualized later).
- **GroupQuizAnswer:** Can be keyed by group and/or student depending on “allow individual submissions”.
- Student dashboard must use **group submit** URL for group PDF/paper assignments so the backend creates/updates **GroupSubmission** instead of an individual **Submission**.
