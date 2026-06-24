import { apiFetch } from './client'

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
  meta?: { can_manage?: boolean }
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
}

export interface QuizQuestionTypeOption {
  value: string
  label: string
}

export interface QuizAssignmentFormMeta extends AssignmentFormCommon {
  question_types: QuizQuestionTypeOption[]
}

export async function fetchPdfAssignmentForm(context: string, classId?: number | null) {
  const params = new URLSearchParams({ context })
  if (classId) params.set('class_id', String(classId))
  return apiFetch<PdfAssignmentFormMeta>(`/api/spa/assignments/create/pdf?${params}`)
}

export async function fetchDiscussionAssignmentForm(classId?: number | null) {
  const qs = classId ? `?class_id=${classId}` : ''
  return apiFetch<DiscussionAssignmentFormMeta>(`/api/spa/assignments/create/discussion${qs}`)
}

export async function fetchQuizAssignmentForm(classId?: number | null) {
  const qs = classId ? `?class_id=${classId}` : ''
  return apiFetch<QuizAssignmentFormMeta>(`/api/spa/assignments/create/quiz${qs}`)
}
