import { apiFetch } from './client'
import type { ActionResponse, ClosureDashboardResponse, ClosureScheduleResponse } from '../types/schoolYearClosure'

export async function fetchClosureScheduleForm() {
  return apiFetch<ClosureScheduleResponse>('/api/spa/school-year/closure/schedule')
}

export async function scheduleClosure(body: {
  school_year_id: number
  closure_date: string
  notes?: string
  confirm: string
}) {
  return apiFetch<ActionResponse>('/api/spa/school-year/closure', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function fetchClosureDashboard(closureId: number) {
  return apiFetch<ClosureDashboardResponse>(`/api/spa/school-year/closure/${closureId}`)
}

export async function runClosureAction(
  closureId: number,
  action: string,
  body: Record<string, unknown> = {},
) {
  return apiFetch<ActionResponse>(`/api/spa/school-year/closure/${closureId}/${action}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function grantClosureExtension(closureId: number, body: Record<string, unknown>) {
  return apiFetch<ActionResponse>(`/api/spa/school-year/closure/${closureId}/extensions`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function revokeClosureExtension(closureId: number, extensionId: number) {
  return apiFetch<ActionResponse>(
    `/api/spa/school-year/closure/${closureId}/extensions/${extensionId}/revoke`,
    { method: 'POST', body: JSON.stringify({}) },
  )
}

export async function createNextSchoolYear(body: {
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
