import { apiFetch } from './client'
import type { BugReportsResponse } from '../types/settings'
import type { StudentJobsHubResponse } from '../types/studentJobs'
import type {
  StudentCalendarResponse,
  StudentScheduleResponse,
  StudentSettingsResponse,
} from '../types/studentTabs'

export async function fetchStudentSchedule() {
  return apiFetch<StudentScheduleResponse>('/api/spa/student/schedule')
}

export async function fetchStudentCalendar(month: number, year: number) {
  return apiFetch<StudentCalendarResponse>(
    `/api/spa/student/calendar?month=${month}&year=${year}`,
  )
}

export async function fetchStudentJobsHub() {
  return apiFetch<StudentJobsHubResponse & { can_manage?: boolean }>('/api/spa/student/jobs')
}

export async function fetchStudentSettingsHub() {
  return apiFetch<StudentSettingsResponse>('/api/spa/student/settings/hub')
}

export async function updateStudentTheme(theme: string) {
  return apiFetch<{ success: boolean; theme?: string; message?: string }>(
    '/api/spa/student/settings/theme',
    { method: 'POST', body: JSON.stringify({ theme }) },
  )
}

export async function updateStudentLowGradeThreshold(threshold: number) {
  return apiFetch<{ success: boolean; threshold?: number; message?: string }>(
    '/api/spa/student/settings/low-grade-threshold',
    { method: 'POST', body: JSON.stringify({ threshold }) },
  )
}

export async function fetchStudentBugReports() {
  return apiFetch<BugReportsResponse>('/api/spa/student/bug-reports')
}

export async function submitStudentBugReport(payload: {
  title: string
  description: string
  contact_email?: string
  severity: string
  page_url?: string
}) {
  return apiFetch<{ success: boolean; message: string }>('/api/spa/student/bug-reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
