import { apiFetch } from './client'
import type {
  GradeStandardsEditorResponse,
  GradeStandardsHubResponse,
  GradeStandardsSavePayload,
  GradeStandardsSaveResponse,
} from '../types/gradeStandards'

export type GradeLevelRoute = 'grade1' | 'grade3'
export type GradeStandardsScope = 'management' | 'teacher'

function editorPath(
  grade: GradeLevelRoute,
  classId: number,
  scope: GradeStandardsScope,
  qs: string,
) {
  const base =
    scope === 'teacher'
      ? `/api/spa/teacher/classes/${classId}/standards/${grade}`
      : `/api/spa/grade-standards/${grade}/classes/${classId}`
  return qs ? `${base}?${qs}` : base
}

export async function fetchGradeStandardsHub(grade: GradeLevelRoute): Promise<GradeStandardsHubResponse> {
  return apiFetch<GradeStandardsHubResponse>(`/api/spa/grade-standards/${grade}/hub`)
}

export async function fetchGradeStandardsEditor(
  grade: GradeLevelRoute,
  classId: number,
  params?: { quarter?: string; view?: string; studentId?: number; scope?: GradeStandardsScope },
): Promise<GradeStandardsEditorResponse> {
  const search = new URLSearchParams()
  if (params?.quarter) search.set('quarter', params.quarter)
  if (params?.view) search.set('view', params.view)
  if (params?.studentId) search.set('student_id', String(params.studentId))
  const qs = search.toString()
  const scope = params?.scope ?? 'management'
  return apiFetch<GradeStandardsEditorResponse>(editorPath(grade, classId, scope, qs))
}

export async function saveGradeStandardsMarks(
  grade: GradeLevelRoute,
  classId: number,
  payload: GradeStandardsSavePayload,
  scope: GradeStandardsScope = 'management',
): Promise<GradeStandardsSaveResponse> {
  return apiFetch<GradeStandardsSaveResponse>(editorPath(grade, classId, scope, ''), {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
