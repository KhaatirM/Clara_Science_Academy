import { apiFetch } from './client'
import { getCsrfToken } from './client'

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
    is_quiz?: boolean
    max_attempts?: number | null
  }
  links: Record<string, string>
}

export interface GradeStudentRow {
  student: { id: number; display_name: string; grade_level?: number | null }
  grade: {
    score: number | null
    points_earned?: number | null
    percentage?: number | null
    comment: string
    is_voided: boolean
  }
  submission?: { submission_type: string; submission_notes: string } | null
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
}

export async function fetchIndividualAssignmentView(assignmentId: number) {
  return apiFetch<AssignmentViewResponse>(`/api/spa/assignments/individual/${assignmentId}/view`)
}

export async function fetchGroupAssignmentView(assignmentId: number) {
  return apiFetch<AssignmentViewResponse>(`/api/spa/assignments/group/${assignmentId}/view`)
}

export async function fetchIndividualAssignmentGrade(assignmentId: number) {
  return apiFetch<AssignmentGradeResponse>(`/api/spa/assignments/individual/${assignmentId}/grade`)
}

export async function fetchGroupAssignmentGrade(assignmentId: number) {
  return apiFetch<AssignmentGradeResponse>(`/api/spa/assignments/group/${assignmentId}/grade`)
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
) {
  return apiFetch<{ success: boolean; message: string }>(
    `/management/grade/assignment/${assignmentId}/student/${studentId}`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export async function saveGroupAssignmentGrades(assignmentId: number, formData: FormData) {
  const token = getCsrfToken()
  if (token) formData.append('csrf_token', token)
  const response = await fetch(`/management/group-assignment/${assignmentId}/grade`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    body: formData,
  })
  const data = (await response.json()) as { success?: boolean; message?: string }
  if (!response.ok || data.success === false) {
    throw new Error(data.message || `Save failed (${response.status})`)
  }
  return data
}
