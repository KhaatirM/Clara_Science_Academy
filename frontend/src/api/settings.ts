import { apiFetch } from './client'
import type { BugReportsResponse, SettingsHubResponse } from '../types/settings'

export async function fetchSettingsHub(): Promise<SettingsHubResponse> {
  return apiFetch<SettingsHubResponse>('/api/spa/settings/hub')
}

export async function updateTheme(theme: string) {
  return apiFetch<{ success: boolean; theme?: string; message?: string }>('/api/spa/settings/theme', {
    method: 'POST',
    body: JSON.stringify({ theme }),
  })
}

export async function fetchBugReports(): Promise<BugReportsResponse> {
  return apiFetch<BugReportsResponse>('/api/spa/bug-reports')
}

export async function submitBugReport(payload: {
  title: string
  description: string
  contact_email?: string
  severity: string
  page_url?: string
}) {
  return apiFetch<{ success: boolean; message: string; report_id?: number }>('/api/spa/bug-reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateBugReportStatus(reportId: number, status: string) {
  return apiFetch<{ success: boolean; message: string; status?: string }>(
    `/api/spa/bug-reports/${reportId}/status`,
    { method: 'POST', body: JSON.stringify({ status }) },
  )
}
