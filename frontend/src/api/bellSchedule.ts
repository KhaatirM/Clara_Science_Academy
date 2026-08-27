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
