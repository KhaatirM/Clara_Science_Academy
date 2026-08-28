import { apiFetch } from './client'
import type { BellGridPayload, BellPeriodDto, BellScheduleDto } from '../types/bellSchedule'

export interface ManagementBellScheduleResponse {
  bell_schedule: BellScheduleDto | null
  school_year: { id: number; name: string } | null
  selected_grade: number | null
  grades: Array<{ grade: number | null; label: string }>
  kind_options: Array<{ value: string; label: string }>
  weekday_options: Array<{ value: number; label: string }>
  links: { pdf_grade_template: string }
}

export async function fetchManagementBellSchedule(grade?: number | null) {
  const qs =
    grade === undefined
      ? ''
      : grade === null
        ? '?grade=all'
        : `?grade=${grade}`
  return apiFetch<ManagementBellScheduleResponse>(`/api/spa/management/bell-schedule${qs}`)
}

export async function saveManagementBellSchedule(payload: {
  title: string
  grade_level: number | null
  periods: BellPeriodDto[]
}) {
  return apiFetch<{
    success: boolean
    message?: string
    bell_schedule?: BellScheduleDto
    selected_grade?: number | null
  }>('/api/spa/management/bell-schedule', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function fetchGradeMasterSchedule(grade: number) {
  return apiFetch<
    BellGridPayload & {
      grade: number
      grade_label: string
      class_count: number
    }
  >(`/api/spa/management/schedule/grade/${grade}`)
}

export function gradeSchedulePdfUrl(grade: number) {
  return `/api/spa/management/schedule/grade/${grade}.pdf`
}

export async function fetchSchedulePlanner(grade: number) {
  return apiFetch<import('../types/schedulePlanner').SchedulePlannerResponse>(
    `/api/spa/management/schedule/planner?grade=${grade}`,
  )
}

export async function assignClassToPeriod(
  classId: number,
  periodId: number,
  daysOfWeek?: number[],
) {
  return apiFetch<{
    success: boolean
    class_id: number
    period_id: number
    days_of_week?: number[]
    schedule_text?: string
  }>('/api/spa/management/schedule/assign', {
    method: 'POST',
    body: JSON.stringify({
      class_id: classId,
      period_id: periodId,
      ...(daysOfWeek ? { days_of_week: daysOfWeek } : {}),
    }),
  })
}

export async function updateAssignmentDays(
  classId: number,
  periodId: number,
  daysOfWeek: number[],
) {
  return apiFetch<{
    success: boolean
    class_id: number
    period_id: number
    days_of_week: number[]
    schedule_text?: string
  }>('/api/spa/management/schedule/assignment-days', {
    method: 'PATCH',
    body: JSON.stringify({
      class_id: classId,
      period_id: periodId,
      days_of_week: daysOfWeek,
    }),
  })
}

export async function resetBellSchedulePeriods(gradeLevel: number | null) {
  return apiFetch<{
    success: boolean
    message?: string
    bell_schedule?: import('../types/bellSchedule').BellScheduleDto
  }>('/api/spa/management/bell-schedule/reset', {
    method: 'POST',
    body: JSON.stringify({ grade_level: gradeLevel }),
  })
}

export async function unassignClassFromGradeSchedule(classId: number, gradeLevel: number) {
  return apiFetch<{ success: boolean; class_id: number }>(
    '/api/spa/management/schedule/unassign',
    { method: 'POST', body: JSON.stringify({ class_id: classId, grade_level: gradeLevel }) },
  )
}
