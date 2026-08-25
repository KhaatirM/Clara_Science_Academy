import { apiFetch } from './client'

export async function fetchTechDashboard() {
  return apiFetch<any>('/api/spa/tech/dashboard')
}

export async function fetchTechSettingsHub() {
  return apiFetch<any>('/api/spa/tech/settings/hub')
}

export async function updateTechTheme(theme: string) {
  return apiFetch<any>('/api/spa/tech/settings/theme', {
    method: 'POST',
    body: JSON.stringify({ theme }),
  })
}

export async function fetchTechDevices(query: {
  type?: string
  q?: string
  assignment?: string
} = {}) {
  const params = new URLSearchParams()
  if (query.type) params.set('type', query.type)
  if (query.q) params.set('q', query.q)
  if (query.assignment) params.set('assignment', query.assignment)
  const qs = params.toString()
  return apiFetch<any>(`/api/spa/tech/devices${qs ? `?${qs}` : ''}`)
}

export async function uploadTechDevicesCsv(file: File) {
  const body = new FormData()
  body.append('csv_file', file)
  return apiFetch<any>('/api/spa/tech/devices/bulk-upload', {
    method: 'POST',
    body,
  })
}

export async function fetchTechDeviceForm(deviceId?: number) {
  if (deviceId) return apiFetch<any>(`/api/spa/tech/devices/${deviceId}/form`)
  return apiFetch<any>('/api/spa/tech/devices/form')
}

export async function saveTechDevice(body: Record<string, unknown>, deviceId?: number) {
  if (deviceId) {
    return apiFetch<any>(`/api/spa/tech/devices/${deviceId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  }
  return apiFetch<any>('/api/spa/tech/devices', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function deleteTechDevice(deviceId: number) {
  return apiFetch<any>(`/api/spa/tech/devices/${deviceId}`, { method: 'DELETE' })
}

export async function fetchTechRepairTickets(query: {
  status?: string
  category?: string
  q?: string
  device_id?: number
} = {}) {
  const params = new URLSearchParams()
  if (query.status) params.set('status', query.status)
  if (query.category) params.set('category', query.category)
  if (query.q) params.set('q', query.q)
  if (query.device_id != null) params.set('device_id', String(query.device_id))
  const qs = params.toString()
  return apiFetch<any>(`/api/spa/tech/devices/repair-tickets${qs ? `?${qs}` : ''}`)
}

export async function createTechRepairTicket(payload: {
  device_id: number
  title: string
  description: string
  category: string
  severity: string
}) {
  return apiFetch<any>('/api/spa/tech/devices/repair-tickets', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateTechRepairTicketStatus(
  ticketId: number,
  payload: { status: string; resolution_notes?: string },
) {
  return apiFetch<any>(`/api/spa/tech/devices/repair-tickets/${ticketId}/status`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function fetchTechActivityLog(query: Record<string, string | number | undefined>) {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([k, v]) => {
    if (v != null && v !== '') params.set(k, String(v))
  })
  const qs = params.toString()
  return apiFetch<any>(`/api/spa/tech/activity-log${qs ? `?${qs}` : ''}`)
}

export async function fetchTechAuditLogs(query: Record<string, string | number | undefined>) {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([k, v]) => {
    if (v != null && v !== '') params.set(k, String(v))
  })
  const qs = params.toString()
  return apiFetch<any>(`/api/spa/tech/audit-logs${qs ? `?${qs}` : ''}`)
}

export async function fetchTechErrorReports(query: Record<string, string | undefined>) {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([k, v]) => {
    if (v) params.set(k, v)
  })
  const qs = params.toString()
  return apiFetch<any>(`/api/spa/tech/error-reports${qs ? `?${qs}` : ''}`)
}

export async function fetchTechSystem() {
  return apiFetch<any>('/api/spa/tech/system')
}

export async function postTechSystemAction(
  path:
    | 'backup'
    | 'integrity'
    | 'clear-cache'
    | 'maintenance/start'
    | 'maintenance/stop'
    | 'config'
    | 'timezone'
    | 'site-theme',
  body?: Record<string, unknown>,
) {
  return apiFetch<any>(`/api/spa/tech/system/${path}`, {
    method: 'POST',
    body: JSON.stringify(body || {}),
  })
}

export async function fetchTechBugReports() {
  return apiFetch<any>('/api/spa/tech/bug-reports')
}

export async function submitTechBugReport(payload: {
  title: string
  description: string
  contact_email?: string
  severity: string
  page_url?: string
}) {
  return apiFetch<any>('/api/spa/tech/bug-reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateTechBugStatus(reportId: number, status: string) {
  return apiFetch<any>(`/api/spa/tech/bug-reports/${reportId}/status`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  })
}

export async function fetchTechUsers() {
  return apiFetch<any>('/api/spa/tech/users')
}

export async function fetchTechUser(userId: number) {
  return apiFetch<any>(`/api/spa/tech/users/${userId}`)
}

export async function resetTechUserPassword(userId: number) {
  return apiFetch<any>(`/api/spa/tech/users/${userId}/reset-password`, { method: 'POST', body: '{}' })
}

export async function impersonateTechUser(userId: number) {
  return apiFetch<any>(`/api/spa/tech/users/${userId}/impersonate`, { method: 'POST', body: '{}' })
}
