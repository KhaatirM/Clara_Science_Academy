import { apiFetch } from './client'
import type { AssignmentsClassResponse, AssignmentsHubResponse } from '../types/assignments'

export async function fetchAssignmentsHub(schoolYearId?: number | null): Promise<AssignmentsHubResponse> {
  const params = new URLSearchParams()
  if (schoolYearId) params.set('school_year_id', String(schoolYearId))
  const qs = params.toString()
  return apiFetch<AssignmentsHubResponse>(`/api/spa/assignments/hub${qs ? `?${qs}` : ''}`)
}

export async function fetchAssignmentsClass(
  classId: number,
  opts?: { view?: string; sort?: string; order?: string },
): Promise<AssignmentsClassResponse> {
  const params = new URLSearchParams()
  if (opts?.view) params.set('view', opts.view)
  if (opts?.sort) params.set('sort', opts.sort)
  if (opts?.order) params.set('order', opts.order)
  const qs = params.toString()
  return apiFetch<AssignmentsClassResponse>(
    `/api/spa/assignments/class/${classId}${qs ? `?${qs}` : ''}`,
  )
}
