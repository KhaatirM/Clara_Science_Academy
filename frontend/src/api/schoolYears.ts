import { apiFetch, getCsrfToken } from './client'
import type { ActionResponse, SchoolYearsPageResponse } from '../types/schoolYears'

export async function fetchSchoolYearsPage() {
  return apiFetch<SchoolYearsPageResponse>('/api/spa/school-years')
}

export async function createSchoolYear(body: {
  name: string
  start_date: string
  end_date: string
  is_active?: boolean
  auto_generate_quarters?: boolean
}) {
  return apiFetch<ActionResponse>('/api/spa/school-years', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function setActiveSchoolYear(yearId: number) {
  return apiFetch<ActionResponse>(`/api/spa/school-years/${yearId}/set-active`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function editActiveSchoolYear(body: { start_date: string; end_date: string }) {
  return apiFetch<ActionResponse>('/api/spa/school-years/active', {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function editSchoolYear(yearId: number, body: { start_date: string; end_date: string }) {
  return apiFetch<ActionResponse>(`/api/spa/school-years/${yearId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function generateSchoolYearPeriods(yearId: number) {
  return apiFetch<ActionResponse>(`/api/spa/school-years/${yearId}/periods/generate`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function addSchoolYearPeriod(
  yearId: number,
  body: { name: string; period_type: string; start_date: string; end_date: string },
) {
  return apiFetch<ActionResponse>(`/api/spa/school-years/${yearId}/periods`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function editSchoolYearPeriod(
  periodId: number,
  body: { start_date: string; end_date: string },
) {
  return apiFetch<ActionResponse>(`/api/spa/school-years/periods/${periodId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function uploadCalendarPdf(form: FormData): Promise<{ message: string }> {
  const csrf = getCsrfToken()
  if (csrf) form.append('csrf_token', csrf)

  const response = await fetch('/api/spa/school-years/upload-calendar-pdf', {
    method: 'POST',
    body: form,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(csrf ? { 'X-CSRFToken': csrf } : {}),
    },
  })

  const data = (await response.json().catch(() => ({}))) as ActionResponse
  if (!response.ok || !data.success) {
    throw new Error(data.message || 'Could not upload calendar PDF')
  }
  return { message: data.message || 'Calendar PDF uploaded.' }
}
