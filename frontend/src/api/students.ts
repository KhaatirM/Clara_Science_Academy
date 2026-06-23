import { apiFetch, getCsrfToken } from './client'
import type { StudentDetail, StudentFilters, StudentListResponse, StudentSaveResponse } from '../types/students'

function filtersToParams(filters: StudentFilters): string {
  const params = new URLSearchParams()
  if (filters.search) params.set('search', filters.search)
  if (filters.search_type) params.set('search_type', filters.search_type)
  if (filters.grade_level) params.set('grade_level', filters.grade_level)
  if (filters.status) params.set('status', filters.status)
  if (filters.alert_filter) params.set('alert_filter', filters.alert_filter)
  if (filters.sort) params.set('sort', filters.sort)
  if (filters.order) params.set('order', filters.order)
  if (filters.page > 1) params.set('page', String(filters.page))
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

async function postStudentForm(url: string, formData: FormData): Promise<StudentSaveResponse> {
  const token = getCsrfToken()
  if (token) formData.set('csrf_token', token)

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(token ? { 'X-CSRFToken': token } : {}),
    },
  })

  const data = (await response.json().catch(() => ({}))) as StudentSaveResponse
  if (!response.ok || !data.success) {
    throw new Error(data.message || `Save failed (${response.status})`)
  }
  return data
}

export async function fetchStudentList(filters: StudentFilters): Promise<StudentListResponse> {
  return apiFetch<StudentListResponse>(`/api/spa/students${filtersToParams(filters)}`)
}

export async function fetchStudentDetail(id: number): Promise<StudentDetail> {
  return apiFetch<StudentDetail>(`/management/view-student/${id}`)
}

export async function submitStudentAddForm(formData: FormData): Promise<StudentSaveResponse> {
  return postStudentForm('/management/add-student', formData)
}

export async function submitStudentEditForm(
  studentId: number,
  formData: FormData,
): Promise<StudentSaveResponse> {
  return postStudentForm(`/management/edit-student/${studentId}`, formData)
}

export async function markStudentsRepeating(ids: number[]): Promise<{ message: string }> {
  const form = new FormData()
  ids.forEach((id) => form.append('student_ids', String(id)))
  const csrf = getCsrfToken()
  if (csrf) form.append('csrf_token', csrf)

  const response = await fetch('/management/students/mark-repeating', {
    method: 'POST',
    body: form,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(csrf ? { 'X-CSRFToken': csrf } : {}),
    },
  })

  const data = (await response.json().catch(() => ({}))) as { message?: string; error?: string }
  if (!response.ok) {
    throw new Error(data.message || data.error || 'Could not mark students as repeating')
  }
  return { message: data.message || 'Students marked as repeating.' }
}

export async function removeStudent(id: number): Promise<{ message: string }> {
  const form = new FormData()
  const csrf = getCsrfToken()
  if (csrf) form.append('csrf_token', csrf)

  const response = await fetch(`/management/remove-student/${id}`, {
    method: 'POST',
    body: form,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(csrf ? { 'X-CSRFToken': csrf } : {}),
    },
  })

  const data = (await response.json().catch(() => ({}))) as {
    success?: boolean
    message?: string
    error?: string
  }
  if (!response.ok || data.success === false) {
    throw new Error(data.message || data.error || 'Could not remove student')
  }
  return { message: data.message || 'Student removed.' }
}
