import { apiFetch } from './client'
import type { CalendarPageResponse } from '../types/calendar'

export async function fetchCalendarPage(month?: number, year?: number) {
  const params = new URLSearchParams()
  if (month) params.set('month', String(month))
  if (year) params.set('year', String(year))
  const qs = params.toString() ? `?${params}` : ''
  return apiFetch<CalendarPageResponse>(`/api/spa/calendar${qs}`)
}

export async function addCalendarEvent(body: {
  event_title: string
  event_date: string
  event_category: string
  event_description?: string
}) {
  return apiFetch<{ success: boolean; message: string }>('/api/spa/calendar/events', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function addSchoolBreak(body: {
  name: string
  start_date: string
  end_date: string
  break_type: string
  description?: string
}) {
  return apiFetch<{ success: boolean; message: string }>('/api/spa/calendar/breaks', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function addTeacherWorkDays(body: {
  dates: string
  title: string
  attendance_requirement?: string
  description?: string
}) {
  return apiFetch<{ success: boolean; message: string }>('/api/spa/calendar/work-days', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function deleteSchoolBreak(id: number) {
  return apiFetch<{ success: boolean; message: string }>(`/api/spa/calendar/breaks/${id}`, {
    method: 'DELETE',
  })
}

export async function deleteTeacherWorkDay(id: number) {
  return apiFetch<{ success: boolean; message: string }>(`/api/spa/calendar/work-days/${id}`, {
    method: 'DELETE',
  })
}
