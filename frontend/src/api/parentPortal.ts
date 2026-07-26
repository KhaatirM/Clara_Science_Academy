import { apiFetch } from './client'
import type {
  ParentBootstrap,
  ParentHomeResponse,
  ParentSettingsResponse,
  ParentTabResponse,
} from '../types/parentPortal'

export async function fetchParentBootstrap() {
  return apiFetch<ParentBootstrap>('/api/spa/parent/bootstrap')
}

export async function selectParentChild(studentId: number) {
  return apiFetch<ParentBootstrap>('/api/spa/parent/select-child', {
    method: 'POST',
    body: JSON.stringify({ student_id: studentId }),
  })
}

export async function fetchParentHome() {
  return apiFetch<ParentHomeResponse>('/api/spa/parent/home')
}

export async function fetchParentGrades() {
  return apiFetch<ParentTabResponse>('/api/spa/parent/grades')
}

export async function fetchParentAttendance() {
  return apiFetch<ParentTabResponse>('/api/spa/parent/attendance')
}

export async function fetchParentClasses() {
  return apiFetch<ParentTabResponse>('/api/spa/parent/classes')
}

export async function fetchParentReportCards() {
  return apiFetch<ParentTabResponse>('/api/spa/parent/report-cards')
}

export async function fetchParentSettings() {
  return apiFetch<ParentSettingsResponse>('/api/spa/parent/settings')
}

export async function updateParentTheme(theme: string) {
  return apiFetch<{ success?: boolean; message?: string; theme?: string }>(
    '/api/spa/parent/settings/theme',
    {
      method: 'POST',
      body: JSON.stringify({ theme }),
    },
  )
}

export function parentReportCardPdfUrl(reportCardId: number) {
  return `/api/spa/parent/report-cards/${reportCardId}/pdf`
}
