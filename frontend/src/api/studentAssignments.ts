import { apiFetch, getCsrfToken } from './client'
import type { StudentAssignmentsResponse } from '../types/studentAssignments'

export type StudentAssignmentsQuery = {
  class_id?: number | ''
  status?: string
  start_date?: string
  end_date?: string
}

export async function fetchStudentAssignments(query: StudentAssignmentsQuery = {}) {
  const params = new URLSearchParams()
  if (query.class_id) params.set('class_id', String(query.class_id))
  if (query.status) params.set('status', query.status)
  if (query.start_date) params.set('start_date', query.start_date)
  if (query.end_date) params.set('end_date', query.end_date)
  const qs = params.toString()
  return apiFetch<StudentAssignmentsResponse>(`/api/spa/student/assignments${qs ? `?${qs}` : ''}`)
}

async function postStudentForm(url: string, formData: FormData) {
  const token = getCsrfToken()
  if (token) {
    formData.set('csrf_token', token)
  }
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(token ? { 'X-CSRFToken': token } : {}),
    },
    body: formData,
  })
  const data = (await response.json().catch(() => ({}))) as {
    success?: boolean
    message?: string
    error?: string
  }
  if (!response.ok || data.success === false) {
    throw new Error(data.message || data.error || `Request failed (${response.status})`)
  }
  return data
}

export async function requestStudentExtension(payload: {
  assignmentId: number
  reason: string
  requestedDueDate: string
}) {
  const form = new FormData()
  form.set('assignment_id', String(payload.assignmentId))
  form.set('reason', payload.reason)
  form.set('requested_due_date', payload.requestedDueDate)
  return postStudentForm('/student/request-extension', form)
}

export async function submitStudentAssignment(payload: {
  assignmentId: number
  isGroup: boolean
  file: File
  notes?: string
}) {
  const form = new FormData()
  form.set('assignment_id', String(payload.assignmentId))
  form.set('submission_file', payload.file)
  if (payload.notes) form.set('submission_notes', payload.notes)
  const url = payload.isGroup
    ? `/student/submit/group/${payload.assignmentId}`
    : `/student/submit/${payload.assignmentId}`
  return postStudentForm(url, form)
}

export async function requestStudentRedo(payload: { assignmentId: number; reason: string }) {
  const form = new FormData()
  form.set('assignment_id', String(payload.assignmentId))
  form.set('reason', payload.reason)
  return postStudentForm('/student/request-redo', form)
}
