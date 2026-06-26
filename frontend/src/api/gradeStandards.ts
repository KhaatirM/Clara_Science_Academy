import { apiFetch } from './client'
import type {
  GradeStandardsEditorResponse,
  GradeStandardsHubResponse,
  GradeStandardsSavePayload,
  GradeStandardsSaveResponse,
} from '../types/gradeStandards'

export type GradeLevelRoute = 'grade1' | 'grade3'

export async function fetchGradeStandardsHub(grade: GradeLevelRoute): Promise<GradeStandardsHubResponse> {
  return apiFetch<GradeStandardsHubResponse>(`/api/spa/grade-standards/${grade}/hub`)
}

export async function fetchGradeStandardsEditor(
  grade: GradeLevelRoute,
  classId: number,
  params?: { quarter?: string; view?: string; studentId?: number },
): Promise<GradeStandardsEditorResponse> {
  const search = new URLSearchParams()
  if (params?.quarter) search.set('quarter', params.quarter)
  if (params?.view) search.set('view', params.view)
  if (params?.studentId) search.set('student_id', String(params.studentId))
  const qs = search.toString()
  return apiFetch<GradeStandardsEditorResponse>(
    `/api/spa/grade-standards/${grade}/classes/${classId}${qs ? `?${qs}` : ''}`,
  )
}

export async function saveGradeStandardsMarks(
  grade: GradeLevelRoute,
  classId: number,
  payload: GradeStandardsSavePayload,
): Promise<GradeStandardsSaveResponse> {
  return apiFetch<GradeStandardsSaveResponse>(`/api/spa/grade-standards/${grade}/classes/${classId}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
