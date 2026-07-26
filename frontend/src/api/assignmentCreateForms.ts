import { apiFetch } from './client'
import type { AssignmentCreateScope } from '../utils/assignmentCreateScope'
import { assignmentCreateApiBase } from '../utils/assignmentCreateScope'

export interface ClassBrief {
  id: number
  name: string
  subject?: string | null
}

export interface AssignmentFormCommon {
  current_quarter: string
  classes: ClassBrief[]
  preselected_class: ClassBrief | null
  back_url: string
  type_selector_url: string
  post_url: string
  meta?: { can_manage?: boolean; scope?: string }
}

export interface PdfAssignmentFormMeta extends AssignmentFormCommon {
  context: 'homework' | 'in-class'
  default_due_date: string | null
  in_class_due_date: string
}

export interface DiscussionAssignmentFormMeta extends AssignmentFormCommon {
  defaults: {
    min_initial_posts: number
    min_replies: number
    total_points: number
  }
  edit?: {
    id: number
    title: string
    class_id: number
    discussion_prompt: string
    description: string
    min_initial_posts: number
    min_replies: number
    require_peer_response: boolean
    allow_student_threads: boolean
    allow_student_edit_posts: boolean
    total_points: number
    quarter: string
    assignment_context: string
    due_date: string
    open_date: string
    close_date: string
    use_rubric: boolean
    rubric_criteria: string
  } | null
}

export interface QuizQuestionTypeOption {
  value: string
  label: string
}

export interface QuizAssignmentFormMeta extends AssignmentFormCommon {
  question_types: QuizQuestionTypeOption[]
  question_banks_url?: string
  save_to_bank_url?: string
  edit?: {
    id: number
    title: string
    class_id: number
    description: string
    due_date: string
    quarter: string
    assignment_context: string
    assignment_category: string
    category_weight: number
    allow_extra_credit: boolean
    max_extra_credit_points: number
    open_date: string
    close_date: string
    time_limit: string
    attempts: string
    shuffle_questions: boolean
    show_correct_answers: boolean
    link_google_form: boolean
    google_form_url: string
    allow_save_and_continue: boolean
    max_save_attempts: string
    save_timeout_minutes: string
    blocks: Array<
      | { type: 'section'; title: string }
      | {
          type: 'question'
          question_text: string
          question_type: string
          points: number
          options: Array<{ option_text: string; is_correct: boolean }>
        }
    >
    is_draft?: boolean
  } | null
}

export async function fetchPdfAssignmentForm(
  context: string,
  classId?: number | null,
  scope: AssignmentCreateScope = 'management',
) {
  const params = new URLSearchParams({ context })
  if (classId) params.set('class_id', String(classId))
  return apiFetch<PdfAssignmentFormMeta>(`${assignmentCreateApiBase(scope)}/pdf?${params}`)
}

export async function fetchDiscussionAssignmentForm(
  classId?: number | null,
  scope: AssignmentCreateScope = 'management',
  editId?: number | null,
) {
  const params = new URLSearchParams()
  if (classId) params.set('class_id', String(classId))
  if (editId) params.set('edit', String(editId))
  const qs = params.toString()
  return apiFetch<DiscussionAssignmentFormMeta>(
    `${assignmentCreateApiBase(scope)}/discussion${qs ? `?${qs}` : ''}`,
  )
}

export async function fetchQuizAssignmentForm(
  classId?: number | null,
  scope: AssignmentCreateScope = 'management',
  editId?: number | null,
) {
  const params = new URLSearchParams()
  if (classId) params.set('class_id', String(classId))
  if (editId) params.set('edit', String(editId))
  const qs = params.toString()
  return apiFetch<QuizAssignmentFormMeta>(`${assignmentCreateApiBase(scope)}/quiz${qs ? `?${qs}` : ''}`)
}
