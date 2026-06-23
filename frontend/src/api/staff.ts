import { apiFetch, getCsrfToken } from './client'
import type {
  CredentialModalPayload,
  StaffDetail,
  StaffFilters,
  StaffListResponse,
  StaffRosterResponse,
  StaffRosterTab,
  StaffSaveResponse,
} from '../types/staff'

function toQuery(filters: Partial<StaffFilters>): string {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value)
  })
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export async function fetchStaffList(filters: Partial<StaffFilters> = {}): Promise<StaffListResponse> {
  return apiFetch<StaffListResponse>(`/api/spa/staff${toQuery(filters)}`)
}

export async function fetchStaffRoster(
  tab: StaffRosterTab = 'current',
  q = '',
): Promise<StaffRosterResponse> {
  const params = new URLSearchParams({ tab })
  if (q) params.set('q', q)
  return apiFetch<StaffRosterResponse>(`/api/spa/staff/roster?${params.toString()}`)
}

export async function fetchStaffDetail(id: number): Promise<StaffDetail> {
  return apiFetch<StaffDetail>(`/management/view-teacher/${id}`)
}

export async function removeStaff(id: number): Promise<{ success: boolean; message: string }> {
  const token = getCsrfToken()
  const headers: HeadersInit = {
    Accept: 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  }
  if (token) headers['X-CSRFToken'] = token

  const response = await fetch(`/management/remove-teacher-staff/${id}`, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
  })

  const data = (await response.json()) as { success: boolean; message: string }
  if (!response.ok) {
    throw new Error(data.message || `Remove failed (${response.status})`)
  }
  return data
}

export async function submitStaffForm(
  editing: boolean,
  staffId: number | null,
  formData: FormData,
): Promise<StaffSaveResponse> {
  const token = getCsrfToken()
  const url = editing
    ? `/management/edit-teacher-staff/${staffId}`
    : '/management/add-teacher-staff'

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

  const data = (await response.json()) as StaffSaveResponse
  if (!response.ok || !data.success) {
    throw new Error(data.message || `Save failed (${response.status})`)
  }
  return data
}

export type { CredentialModalPayload }
