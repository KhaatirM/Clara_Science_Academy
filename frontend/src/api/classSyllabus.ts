import { apiFetch, getCsrfToken } from './client'
import type { ClassSyllabusResponse } from '../types/classSyllabus'

export async function fetchClassSyllabus(classId: number) {
  return apiFetch<ClassSyllabusResponse>(`/api/spa/classes/${classId}/syllabus`)
}

export async function uploadClassSyllabus(classId: number, file: File) {
  const body = new FormData()
  body.append('file', file)
  const headers = new Headers()
  const csrf = getCsrfToken()
  if (csrf) headers.set('X-CSRFToken', csrf)

  const response = await fetch(`/api/spa/classes/${classId}/syllabus`, {
    method: 'POST',
    body,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
  })
  const data = (await response.json().catch(() => ({}))) as ClassSyllabusResponse & {
    error?: string
    message?: string
  }
  if (!response.ok) {
    throw new Error(data.error || data.message || `Upload failed (${response.status})`)
  }
  return data
}

export async function deleteClassSyllabus(classId: number) {
  return apiFetch<{ success: boolean; message?: string }>(`/api/spa/classes/${classId}/syllabus`, {
    method: 'DELETE',
  })
}

export function classSyllabusDownloadUrl(classId: number) {
  return `/api/spa/classes/${classId}/syllabus/download`
}
