import { apiFetch, getCsrfToken } from './client'
import type { ClassListResponse } from '../types/classes'
import type {
  ClassDetailResponse,
  ClassEditResponse,
  ClassFormOptionsResponse,
  ClassGradesResponse,
  ClassRosterResponse,
  ClassSaveResponse,
  CoreSetupFormResponse,
  CoreSetupPreviewResult,
  CreateClassPayload,
  GoogleClassroomOption,
  UpdateClassPayload,
} from '../types/classDetail'

export async function fetchClassList(schoolYearId?: number | null): Promise<ClassListResponse> {
  const params = new URLSearchParams()
  if (schoolYearId) params.set('school_year_id', String(schoolYearId))
  const qs = params.toString()
  return apiFetch<ClassListResponse>(`/api/spa/classes${qs ? `?${qs}` : ''}`)
}

export async function fetchClassFormOptions(): Promise<ClassFormOptionsResponse> {
  return apiFetch<ClassFormOptionsResponse>('/api/spa/classes/form-options')
}

export async function fetchClassDetail(classId: number): Promise<ClassDetailResponse> {
  return apiFetch<ClassDetailResponse>(`/api/spa/classes/${classId}`)
}

export async function fetchClassEditForm(classId: number): Promise<ClassEditResponse> {
  return apiFetch<ClassEditResponse>(`/api/spa/classes/${classId}/edit`)
}

export async function fetchClassRoster(classId: number): Promise<ClassRosterResponse> {
  return apiFetch<ClassRosterResponse>(`/api/spa/classes/${classId}/roster`)
}

export async function fetchClassGrades(classId: number, view = 'table'): Promise<ClassGradesResponse> {
  return apiFetch<ClassGradesResponse>(`/api/spa/classes/${classId}/grades?view=${view}`)
}

export async function createClass(payload: CreateClassPayload): Promise<ClassSaveResponse> {
  return apiFetch<ClassSaveResponse>('/api/spa/classes', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateClass(classId: number, payload: UpdateClassPayload): Promise<ClassSaveResponse> {
  return apiFetch<ClassSaveResponse>(`/api/spa/classes/${classId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function mutateRoster(
  classId: number,
  action: 'add' | 'remove',
  studentIds: number[],
): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/api/spa/classes/${classId}/roster`, {
    method: 'POST',
    body: JSON.stringify({ action, student_ids: studentIds }),
  })
}

export async function removeClass(classId: number): Promise<ClassSaveResponse> {
  const token = getCsrfToken()
  const response = await fetch(`/api/spa/classes/${classId}/remove`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(token ? { 'X-CSRFToken': token } : {}),
    },
    body: '{}',
  })
  const data = (await response.json().catch(() => ({}))) as ClassSaveResponse
  if (!response.ok || !data.success) {
    throw new Error(data.message || `Remove failed (${response.status})`)
  }
  return data
}

export async function fetchGoogleClassroomOptions(
  classId: number,
): Promise<{ success: boolean; message?: string; items?: GoogleClassroomOption[]; settings_url?: string }> {
  return apiFetch(`/api/spa/classes/${classId}/google-classroom/options`)
}

export async function googleClassroomAction(
  classId: number,
  action: 'create' | 'link' | 'unlink',
  googleClassroomId?: string,
): Promise<{ success: boolean; message: string; google_classroom_id?: string; settings_url?: string }> {
  return apiFetch(`/api/spa/classes/${classId}/google-classroom`, {
    method: 'POST',
    body: JSON.stringify({ action, google_classroom_id: googleClassroomId }),
  })
}

export async function fetchCoreSetupForm(): Promise<CoreSetupFormResponse> {
  return apiFetch<CoreSetupFormResponse>('/api/spa/classes/core-setup')
}

export async function previewCoreSetup(body: Record<string, unknown>): Promise<{
  success: boolean
  message?: string
  preview: CoreSetupPreviewResult | null
}> {
  return apiFetch('/api/spa/classes/core-setup/preview', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function createCoreSetup(body: Record<string, unknown>): Promise<{
  success: boolean
  message: string
  redirect?: string
}> {
  return apiFetch('/api/spa/classes/core-setup/create', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
