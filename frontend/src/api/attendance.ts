import { apiFetch } from './client'
import type {
  AttendanceAnalyticsResponse,
  AttendanceHubResponse,
  AttendanceReportsResponse,
  AttendanceSaveResponse,
  SchoolDayEntry,
} from '../types/attendance'

export interface AttendanceReportsQuery {
  start_date?: string
  end_date?: string
  student_ids?: number[]
  class_ids?: number[]
  status?: string
  page?: number
}

export interface AttendanceAnalyticsQuery {
  start_date?: string
  end_date?: string
  risk?: string
}

function appendIdList(params: URLSearchParams, key: string, ids?: number[]) {
  ids?.forEach((id) => params.append(key, String(id)))
}

export async function fetchAttendanceReports(
  query: AttendanceReportsQuery = {},
): Promise<AttendanceReportsResponse> {
  const params = new URLSearchParams()
  if (query.start_date) params.set('start_date', query.start_date)
  if (query.end_date) params.set('end_date', query.end_date)
  if (query.status) params.set('status', query.status)
  if (query.page && query.page > 1) params.set('page', String(query.page))
  appendIdList(params, 'student_ids', query.student_ids)
  appendIdList(params, 'class_ids', query.class_ids)
  const qs = params.toString()
  return apiFetch<AttendanceReportsResponse>(`/api/spa/attendance/reports${qs ? `?${qs}` : ''}`)
}

export async function fetchAttendanceAnalytics(
  query: AttendanceAnalyticsQuery = {},
): Promise<AttendanceAnalyticsResponse> {
  const params = new URLSearchParams()
  if (query.start_date) params.set('start_date', query.start_date)
  if (query.end_date) params.set('end_date', query.end_date)
  if (query.risk && query.risk !== 'all') params.set('risk', query.risk)
  const qs = params.toString()
  return apiFetch<AttendanceAnalyticsResponse>(`/api/spa/attendance/analytics${qs ? `?${qs}` : ''}`)
}

export async function fetchAttendanceHub(params?: {
  date?: string
  class_date?: string
}): Promise<AttendanceHubResponse> {
  const search = new URLSearchParams()
  if (params?.date) search.set('date', params.date)
  if (params?.class_date) search.set('class_date', params.class_date)
  const qs = search.toString()
  return apiFetch<AttendanceHubResponse>(`/api/spa/attendance/hub${qs ? `?${qs}` : ''}`)
}

export async function saveSchoolDayAttendance(
  attendanceDate: string,
  entries: SchoolDayEntry[],
): Promise<AttendanceSaveResponse> {
  return apiFetch<AttendanceSaveResponse>('/api/spa/attendance/school-day', {
    method: 'POST',
    body: JSON.stringify({ attendance_date: attendanceDate, entries }),
  })
}

export async function markClassAllPresent(
  classId: number,
  date: string,
): Promise<AttendanceSaveResponse> {
  return apiFetch<AttendanceSaveResponse>(`/api/spa/attendance/class/${classId}/mark-all-present`, {
    method: 'POST',
    body: JSON.stringify({ date }),
  })
}
