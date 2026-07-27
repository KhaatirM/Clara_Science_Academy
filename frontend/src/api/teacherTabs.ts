import type { BugReportsResponse } from '../types/settings'
import { apiFetch } from './client'
import type {
  TeacherAssignmentsHubResponse,
  TeacherAttendanceResponse,
  TeacherCalendarResponse,
  TeacherScheduleResponse,
  TeacherSettingsResponse,
  TeacherStudentsResponse,
} from '../types/teacherTabs'

function normalizeTeacherAssignmentsHubMeta(
  payload: TeacherAssignmentsHubResponse,
): TeacherAssignmentsHubResponse['meta'] {
  const schoolYears = payload.school_years ?? []
  const activeFromList = schoolYears.find((y) => y.is_active) ?? null
  const defaultSchoolYearId =
    payload.meta?.default_school_year_id ??
    payload.meta?.active_school_year_id ??
    activeFromList?.id ??
    null
  const activeSchoolYearId =
    payload.meta?.active_school_year_id ?? activeFromList?.id ?? defaultSchoolYearId
  const activeSchoolYearName =
    payload.meta?.active_school_year_name ??
    activeFromList?.name ??
    schoolYears.find((y) => y.id === activeSchoolYearId)?.name ??
    null
  const hasActiveSchoolYear =
    payload.meta?.has_active_school_year ??
    (activeFromList != null ||
      (defaultSchoolYearId != null &&
        schoolYears.some((y) => y.id === defaultSchoolYearId && y.is_active)))

  return {
    default_school_year_id: defaultSchoolYearId,
    active_school_year_id: activeSchoolYearId,
    active_school_year_name: activeSchoolYearName,
    has_active_school_year: hasActiveSchoolYear,
    can_select_school_year: payload.meta?.can_select_school_year ?? false,
  }
}

export function fetchTeacherAssignmentsClass(
  classId: number,
  opts?: { view?: string; sort?: string; order?: string },
) {
  const params = new URLSearchParams()
  if (opts?.view) params.set('view', opts.view)
  if (opts?.sort) params.set('sort', opts.sort)
  if (opts?.order) params.set('order', opts.order)
  const qs = params.toString()
  return apiFetch<import('../types/assignments').AssignmentsClassResponse>(
    `/api/spa/teacher/assignments-grades/${classId}${qs ? `?${qs}` : ''}`,
  )
}

export function fetchTeacherStudents() {
  return apiFetch<TeacherStudentsResponse>('/api/spa/teacher/students')
}

export function fetchTeacherAssignmentsHub() {
  return apiFetch<TeacherAssignmentsHubResponse>('/api/spa/teacher/assignments-grades').then(
    (payload) => {
      const meta = normalizeTeacherAssignmentsHubMeta(payload)
      return {
        ...payload,
        items: payload.items ?? [],
        school_years: payload.school_years ?? [],
        meta,
        hub: payload.hub ?? {
          extension_request_count: payload.stats?.extension_requests ?? 0,
          redo_request_count: payload.stats?.redo_requests ?? 0,
        },
        stats: payload.stats ?? {
          total_classes: payload.items?.length ?? 0,
          total_assignments: 0,
          total_students: 0,
          extension_requests: payload.hub?.extension_request_count ?? 0,
          redo_requests: payload.hub?.redo_request_count ?? 0,
        },
      }
    },
  )
}

export function fetchTeacherAttendanceHub() {
  return apiFetch<TeacherAttendanceResponse>('/api/spa/teacher/attendance')
}

export function fetchTeacherSchedule() {
  return apiFetch<TeacherScheduleResponse>('/api/spa/teacher/schedule')
}

export function fetchTeacherCalendar(month?: number, year?: number) {
  const params = new URLSearchParams()
  if (month) params.set('month', String(month))
  if (year) params.set('year', String(year))
  const qs = params.toString()
  return apiFetch<TeacherCalendarResponse>(`/api/spa/teacher/calendar${qs ? `?${qs}` : ''}`)
}

export function fetchTeacherSettingsHub() {
  return apiFetch<TeacherSettingsResponse>('/api/spa/teacher/settings/hub')
}

export function updateTeacherTheme(theme: string) {
  return apiFetch<{ success: boolean; message?: string; theme?: string }>(
    '/api/spa/teacher/settings/theme',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme }),
    },
  )
}

export function fetchTeacherBugReports() {
  return apiFetch<BugReportsResponse>('/api/spa/teacher/bug-reports')
}

export function submitTeacherBugReport(payload: {
  title: string
  description: string
  contact_email?: string
  severity: string
  page_url?: string
}) {
  return apiFetch<{ success: boolean; message: string }>('/api/spa/teacher/bug-reports', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
