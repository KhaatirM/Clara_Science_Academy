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
}

export interface QuizQuestionTypeOption {
  value: string
  label: string
}

export interface QuizAssignmentFormMeta extends AssignmentFormCommon {
  question_types: QuizQuestionTypeOption[]
  question_banks_url?: string
  save_to_bank_url?: string
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
) {
  const qs = classId ? `?class_id=${classId}` : ''
  return apiFetch<DiscussionAssignmentFormMeta>(`${assignmentCreateApiBase(scope)}/discussion${qs}`)
}

export async function fetchQuizAssignmentForm(
  classId?: number | null,
  scope: AssignmentCreateScope = 'management',
) {
  const qs = classId ? `?class_id=${classId}` : ''
  return apiFetch<QuizAssignmentFormMeta>(`${assignmentCreateApiBase(scope)}/quiz${qs}`)
}
