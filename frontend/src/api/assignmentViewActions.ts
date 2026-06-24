import { getCsrfToken } from './client'

async function postForm(url: string, formData: FormData) {
  const token = getCsrfToken()
  if (token) formData.append('csrf_token', token)
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    body: formData,
  })
  const data = (await response.json()) as { success?: boolean; message?: string; error?: string }
  if (!response.ok || data.success === false) {
    throw new Error(data.message || data.error || `Request failed (${response.status})`)
  }
  return data
}

export async function grantIndividualExtensions(payload: {
  assignmentId: number
  classId: number
  extendedDueDate: string
  reason: string
  studentIds: number[]
}) {
  const form = new FormData()
  form.append('assignment_id', String(payload.assignmentId))
  form.append('class_id', String(payload.classId))
  form.append('extended_due_date', payload.extendedDueDate)
  form.append('reason', payload.reason)
  payload.studentIds.forEach((id) => form.append('student_ids', String(id)))
  return postForm(`/management/assignment/${payload.assignmentId}/grant-extensions`, form)
}

export async function grantGroupExtensions(payload: {
  assignmentId: number
  extendedDueDate: string
  reason: string
  studentIds: number[]
}) {
  const form = new FormData()
  form.append('extended_due_date', payload.extendedDueDate)
  form.append('reason', payload.reason)
  payload.studentIds.forEach((id) => form.append('student_ids', String(id)))
  return postForm(`/management/group-assignment/${payload.assignmentId}/grant-extensions`, form)
}

export async function grantAssignmentRedo(payload: {
  assignmentId: number
  redoDeadline: string
  reason: string
  studentIds: number[]
}) {
  const form = new FormData()
  form.append('redo_deadline', payload.redoDeadline)
  form.append('reason', payload.reason)
  payload.studentIds.forEach((id) => form.append('student_ids[]', String(id)))
  return postForm(`/management/grant-redo/${payload.assignmentId}`, form)
}

export interface ReopenStatusStudent {
  student_id: number
  name: string
  has_reopening: boolean
  needs_reopening: boolean
  grade_is_voided: boolean
  additional_attempts?: number
  submissions_count?: number
  reason_needs_reopening?: string
}

export async function fetchReopenStatus(assignmentId: number) {
  const response = await fetch(`/management/assignment/${assignmentId}/reopen-status`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
  })
  const data = (await response.json()) as {
    success?: boolean
    message?: string
    students?: ReopenStatusStudent[]
    assignment_type?: string
    max_attempts?: number | null
  }
  if (!response.ok || !data.success) {
    throw new Error(data.message || `Failed to load reopen status (${response.status})`)
  }
  return data
}

export async function reopenAssignment(payload: {
  assignmentId: number
  studentIds: number[]
  reason: string
  additionalAttempts: number
}) {
  const form = new FormData()
  form.append('reason', payload.reason)
  form.append('additional_attempts', String(payload.additionalAttempts))
  payload.studentIds.forEach((id) => form.append('student_ids', String(id)))
  return postForm(`/management/assignment/${payload.assignmentId}/reopen`, form)
}

export async function unvoidAssignment(payload: {
  assignmentId: number
  type: 'individual' | 'group'
  unvoidAll: boolean
  studentIds: number[]
}) {
  const form = new FormData()
  form.append('assignment_type', payload.type)
  form.append('unvoid_all', payload.unvoidAll ? 'true' : 'false')
  if (!payload.unvoidAll) {
    payload.studentIds.forEach((id) => form.append('student_ids', String(id)))
  }
  return postForm(`/management/unvoid-assignment/${payload.assignmentId}`, form)
}
