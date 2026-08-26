import { apiFetch } from './client'
import { getCsrfToken } from './client'
import type { AssignmentWorkspaceScope } from '../utils/assignmentWorkspaceScope'
import { assignmentWorkspaceApiBase } from '../utils/assignmentWorkspaceScope'

export interface AssignmentViewResponse {
  type: 'individual' | 'group'
  legacy_only?: boolean
  legacy_view_url?: string
  legacy_grade_url?: string
  legacy_reason?: string | null
  assignment: Record<string, unknown>
  class: {
    id: number | null
    name: string
    subject?: string | null
    grade_level?: string | number | null
    teacher_name?: string
    [key: string]: unknown
  }
  stats: Record<string, number | null>
  attachments?: { index: number; name: string; is_pdf: boolean; view_url: string; download_url: string }[]
  attachment?: { name: string; is_pdf: boolean; view_url: string; download_url: string } | null
  groups?: { id: number; name: string; members: { id: number; display_name: string }[] }[]
  void_scope?: Record<string, unknown>
  students?: { id: number; display_name: string; grade_level?: number | null }[]
  voided_student_ids?: number[]
  actions?: {
    show_reopen?: boolean
    show_redo?: boolean
    show_unvoid?: boolean
    grade_disabled?: boolean
    grade_disabled_label?: string | null
    grade_via_submissions?: boolean
    grade_label?: string
    is_quiz?: boolean
    max_attempts?: number | null
  }
  links: Record<string, string>
  discussion?: {
    threads: {
      id: number
      title: string
      is_pinned: boolean
      reply_count: number
      student: { display_name: string }
    }[]
    participants: {
      student: { display_name: string }
      threads: number
      replies: number
      total_posts: number
    }[]
    requirements: { min_initial_posts: number; min_replies: number }
  }
}

export interface GradeStudentRow {
  student: { id: number; display_name: string; grade_level?: number | null; email?: string | null }
  grade: {
    score: number | null
    points_earned?: number | null
    percentage?: number | null
    comment: string
    is_voided: boolean
    grade_id?: number | null
  }
  submission?: {
    submission_type: string
    submission_notes: string
    submitted_at?: string | null
    submission_notes_type?: string
    submission_notes_other?: string
  } | null
  extension?: { extended_due_date: string | null; reason: string } | null
  group_id?: number
  submission_type?: string
  submission_notes?: string
}

export interface AssignmentGradeResponse {
  type: 'individual' | 'group'
  legacy_only?: boolean
  legacy_grade_url?: string
  legacy_reason?: string | null
  assignment: Record<string, unknown>
  class: { id: number | null; name: string }
  students?: GradeStudentRow[]
  groups?: { id: number; name: string; members: GradeStudentRow[] }[]
  stats: Record<string, number>
  links: Record<string, string>
  quiz_grade?: QuizGradePayload
  grade_via_submissions?: boolean
}

export interface AssignmentGradeStatisticsResponse {
  assignment: { id: number; title: string; class_name: string }
  total_points: number
  stats: {
    total_students: number
    graded_count: number
    ungraded_count: number
    average_score: number
    average_percentage: number
    median_score: number
    highest_score: number
    lowest_score: number
    passing_count: number
    failing_count: number
    voided_count?: number
  }
  letter_grades: Record<string, number>
  grade_distribution: Record<string, number>
}

export interface QuizGradePayload {
  grading_mode: 'standard' | 'per_question'
  questions: { id: number; text: string; type: string; max_points: number }[]
  answers_by_student: Record<
    string,
    {
      question_id: number
      question_text: string
      max_points: number
      answer_text: string
      points_earned: number | null
    }[]
  >
}

export interface AssignmentEditForm {
  assignment_id: number
  is_group?: boolean
  class_id: number
  class_name: string
  assignment_type: string
  title: string
  description: string
  due_date: string
  open_date?: string | null
  close_date?: string | null
  quarter: string
  status: string
  assignment_context: string
  assignment_category?: string
  category_weight?: number
  total_points: number
  allow_extra_credit?: boolean
  max_extra_credit_points?: number
  late_penalty_enabled?: boolean
  late_penalty_per_day?: number
  late_penalty_max_days?: number
  status_revert_enabled?: boolean
  status_override_until?: string | null
  attachments?: { id: number | null; name: string }[]
  allow_individual?: boolean
  quiz?: {
    time_limit_minutes: number | null
    max_attempts: number
    shuffle_questions: boolean
    show_correct_answers: boolean
    allow_save_and_continue: boolean
    max_save_attempts: number
    save_timeout_minutes: number
    google_form_linked?: boolean
    google_form_url?: string
  }
  discussion?: { allow_student_edit_posts: boolean }
}

export interface AssignmentSubmissionsResponse {
  assignment: {
    id: number
    title: string
    assignment_type: string
    due_date: string | null
    class_id: number
    total_points?: number
  }
  ui_mode?: 'pdf' | 'quiz' | 'discussion' | 'default'
  grading_on_submissions?: boolean
  show_grade_link?: boolean
  has_open_ended?: boolean
  requirements?: { min_initial_posts: number; min_replies: number } | null
  class: { id: number | null; name: string }
  stats: Record<string, number>
  rows: Record<string, unknown>[]
  links: { view_spa: string; grade_spa: string; submissions_spa?: string }
}

export interface SubmissionsStudentBrief {
  id: number
  display_name: string
  grade_level?: number | null
  email?: string | null
}

export interface SubmissionsGradeInfo {
  score?: number | null
  points_earned?: number | null
  percentage?: number | null
  comment?: string
}

export interface PdfSubmissionRow {
  student: SubmissionsStudentBrief
  status: string
  submission_id: number | null
  submission_type: string | null
  submitted_at: string | null
  submission_notes?: string | null
  file_name: string | null
  download_url: string | null
  grade: SubmissionsGradeInfo | null
  is_voided: boolean
}

export interface QuizQuestionRow {
  order: number
  question_id: number
  question_text: string
  type: string
  max_points: number
  answer_display: string
  is_correct: boolean | null
  points_earned: number | null
  needs_manual_grade: boolean
}

export interface QuizAttemptDetail {
  attempt_num: number
  submitted_at: string | null
  parsed_score: { earned: number; total: number; percentage: number } | null
}

export interface QuizSubmissionRow {
  student: SubmissionsStudentBrief
  status: string
  submitted_at: string | null
  quiz_attempts: number
  quiz_attempt_details?: QuizAttemptDetail[]
  auto_points: number
  has_submission: boolean
  questions: QuizQuestionRow[]
  grade: SubmissionsGradeInfo | null
  is_voided: boolean
}

export interface DiscussionSubmissionRow {
  student: SubmissionsStudentBrief
  status: string
  participation: {
    threads_count: number
    replies_count: number
    total_posts: number
    min_initial_posts: number
    min_replies: number
    initial_posts_met: boolean
    replies_met: boolean
    peer_threads_replied: number
    requirements_met: boolean
  }
  threads: { id: number; title: string; content: string; created_at: string | null; is_pinned: boolean }[]
  replies: {
    id: number
    content: string
    created_at: string | null
    thread_title: string
    is_peer_thread: boolean
  }[]
  grade: SubmissionsGradeInfo | null
  is_voided: boolean
}

export async function fetchIndividualAssignmentView(
  assignmentId: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  return apiFetch<AssignmentViewResponse>(
    `${assignmentWorkspaceApiBase(scope)}/individual/${assignmentId}/view`,
  )
}

export async function fetchGroupAssignmentView(
  assignmentId: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  return apiFetch<AssignmentViewResponse>(`${assignmentWorkspaceApiBase(scope)}/group/${assignmentId}/view`)
}

export async function fetchIndividualAssignmentGrade(
  assignmentId: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  return apiFetch<AssignmentGradeResponse>(
    `${assignmentWorkspaceApiBase(scope)}/individual/${assignmentId}/grade`,
  )
}

export async function fetchIndividualAssignmentGradeStatistics(
  assignmentId: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  return apiFetch<AssignmentGradeStatisticsResponse>(
    `${assignmentWorkspaceApiBase(scope)}/individual/${assignmentId}/grade/statistics`,
  )
}

export async function fetchGroupAssignmentGrade(
  assignmentId: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  return apiFetch<AssignmentGradeResponse>(`${assignmentWorkspaceApiBase(scope)}/group/${assignmentId}/grade`)
}

export async function fetchAssignmentEditForm(
  assignmentId: number,
  isGroup: boolean,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const path = isGroup
    ? `${assignmentWorkspaceApiBase(scope)}/group/${assignmentId}/edit`
    : `${assignmentWorkspaceApiBase(scope)}/individual/${assignmentId}/edit`
  return apiFetch<AssignmentEditForm>(path)
}

export async function saveAssignmentEdit(
  assignmentId: number,
  isGroup: boolean,
  body: Record<string, unknown>,
  scope: AssignmentWorkspaceScope = 'management',
  files: File[] = [],
  removeAttachmentIds: number[] = [],
) {
  const path = isGroup
    ? `${assignmentWorkspaceApiBase(scope)}/group/${assignmentId}/edit`
    : `${assignmentWorkspaceApiBase(scope)}/individual/${assignmentId}/edit`

  const form = new FormData()
  for (const [key, value] of Object.entries(body)) {
    if (value === null || value === undefined) continue
    if (typeof value === 'object') {
      form.append(key, JSON.stringify(value))
    } else if (typeof value === 'boolean') {
      form.append(key, value ? 'true' : 'false')
    } else {
      form.append(key, String(value))
    }
  }
  for (const id of removeAttachmentIds) {
    form.append('remove_attachment_ids', String(id))
  }
  if (isGroup && removeAttachmentIds.length > 0) {
    form.append('clear_attachment', 'true')
  }
  for (const file of files) {
    form.append('assignment_files', file)
  }
  const csrf = getCsrfToken()
  if (csrf) form.append('csrf_token', csrf)

  return apiFetch<{ success: boolean; message: string }>(path, {
    method: 'POST',
    body: form,
  })
}

export async function fetchAssignmentSubmissions(
  assignmentId: number,
  isGroup: boolean,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const path = isGroup
    ? `${assignmentWorkspaceApiBase(scope)}/group/${assignmentId}/submissions`
    : `${assignmentWorkspaceApiBase(scope)}/individual/${assignmentId}/submissions`
  return apiFetch<AssignmentSubmissionsResponse>(path)
}

export async function saveIndividualStudentGrade(
  assignmentId: number,
  studentId: number,
  payload: {
    score: string
    comment?: string
    submission_type?: string
    submission_notes_type?: string
    submission_notes?: string
  },
  scope: AssignmentWorkspaceScope = 'management',
) {
  const base = scope === 'teacher' ? '/teacher' : '/management'
  const data = await apiFetch<{ success: boolean; message: string; error?: string }>(
    `${base}/grade/assignment/${assignmentId}/student/${studentId}`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
  if (data.success === false) {
    throw new Error(data.error || data.message || 'Save failed')
  }
  return data
}

export async function saveGroupAssignmentGrades(
  assignmentId: number,
  formData: FormData,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const token = getCsrfToken()
  if (token) formData.append('csrf_token', token)
  const base = scope === 'teacher' ? '/teacher' : '/management'
  const path =
    scope === 'teacher'
      ? `${base}/grade/group-assignment/${assignmentId}`
      : `${base}/group-assignment/${assignmentId}/grade`
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    body: formData,
  })
  const data = (await response.json()) as { success?: boolean; message?: string; error?: string; graded_count?: number }
  if (!response.ok || data.success === false) {
    throw new Error(data.error || data.message || `Save failed (${response.status})`)
  }
  if (typeof data.graded_count === 'number' && data.graded_count === 0) {
    throw new Error('No grades were saved. Check group membership and score fields.')
  }
  return data
}

export async function saveQuizOpenEndedGrades(
  assignmentId: number,
  entries: {
    student_id: number
    comment?: string
    questions: { question_id: number; points: string | number }[]
  }[],
  scope: AssignmentWorkspaceScope = 'management',
) {
  const path =
    scope === 'teacher'
      ? `${assignmentWorkspaceApiBase(scope)}/individual/${assignmentId}/quiz-open-ended-grades`
      : `/api/spa/assignments/individual/${assignmentId}/grade/quiz`
  return apiFetch<{ success: boolean; message: string }>(path, {
    method: 'POST',
    body: JSON.stringify({ entries }),
  })
}
