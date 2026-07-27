import { apiFetch } from './client'
import type {
  ReportCardActionResponse,
  ReportCardClassOption,
  ReportCardDetailResponse,
  ReportCardGenerateFormResponse,
  ReportCardGeneratePayload,
  ReportCardGenerateResponse,
  ReportCardHistoryResponse,
  ReportCardStudentDetails,
  ReportCardsCategoryResponse,
  ReportCardStandardsChecklist,
  ReportCardStandardsMarksSummary,
  ReportCardsHubResponse,
  ReportCardsPendingResponse,
  ReportCardsSearchResponse,
} from '../types/reportCards'

export async function fetchReportCardsHub(): Promise<ReportCardsHubResponse> {
  return apiFetch<ReportCardsHubResponse>('/api/spa/report-cards/hub')
}

export async function fetchPendingReportCards(): Promise<ReportCardsPendingResponse> {
  return apiFetch<ReportCardsPendingResponse>('/api/spa/report-cards/pending')
}

export type ReportCardsSearchParams = {
  page?: number
  per_page?: number
  school_year_id?: number
  quarter?: string
  student_id?: number
  class_id?: number
  q?: string
}

export async function searchReportCards(
  params: ReportCardsSearchParams = {},
): Promise<ReportCardsSearchResponse> {
  const search = new URLSearchParams()
  if (params.page) search.set('page', String(params.page))
  if (params.per_page) search.set('per_page', String(params.per_page))
  if (params.school_year_id) search.set('school_year_id', String(params.school_year_id))
  if (params.quarter) search.set('quarter', params.quarter)
  if (params.student_id) search.set('student_id', String(params.student_id))
  if (params.class_id) search.set('class_id', String(params.class_id))
  if (params.q) search.set('q', params.q)
  const qs = search.toString()
  return apiFetch<ReportCardsSearchResponse>(`/api/spa/report-cards/search${qs ? `?${qs}` : ''}`)
}

export async function fetchReportCardsCategory(
  category: string,
): Promise<ReportCardsCategoryResponse> {
  return apiFetch<ReportCardsCategoryResponse>(`/api/spa/report-cards/categories/${category}`)
}

export async function fetchReportCardGenerateForm(params?: {
  studentId?: number
  category?: string
  schoolYearId?: number
}): Promise<ReportCardGenerateFormResponse> {
  const search = new URLSearchParams()
  if (params?.studentId) search.set('student_id', String(params.studentId))
  if (params?.category) search.set('category', params.category)
  if (params?.schoolYearId) search.set('school_year_id', String(params.schoolYearId))
  const qs = search.toString()
  return apiFetch<ReportCardGenerateFormResponse>(
    `/api/spa/report-cards/generate-form${qs ? `?${qs}` : ''}`,
  )
}

export async function fetchReportCardStudentDetails(
  studentId: number,
): Promise<ReportCardStudentDetails> {
  const data = await apiFetch<{ success: boolean; student: ReportCardStudentDetails }>(
    `/api/spa/report-cards/students/${studentId}/details`,
  )
  return data.student
}

export async function fetchReportCardStudentClasses(
  studentId: number,
  schoolYearId: number,
  quarters: string[],
): Promise<{
  classes: ReportCardClassOption[]
  grade_at_year_display?: string | null
  standards_checklist?: ReportCardStandardsChecklist | null
  standards_marks_summary?: ReportCardStandardsMarksSummary | null
  school_year?: { id: number; name: string; is_active: boolean } | null
  includes_inactive_enrollments?: boolean
}> {
  const search = new URLSearchParams()
  search.set('school_year_id', String(schoolYearId))
  quarters.forEach((q) => search.append('quarters', q))
  return apiFetch(`/api/spa/report-cards/students/${studentId}/classes?${search}`)
}

export async function fetchReportCardComments(
  studentId: number,
  schoolYearId: number,
  classIds: number[],
): Promise<Record<string, string>> {
  const search = new URLSearchParams()
  search.set('student_id', String(studentId))
  search.set('school_year_id', String(schoolYearId))
  classIds.forEach((id) => search.append('class_ids', String(id)))
  const data = await apiFetch<{ comments_by_class: Record<string, string> }>(
    `/api/spa/report-cards/comments?${search}`,
  )
  return data.comments_by_class || {}
}

export async function submitReportCardGenerate(
  payload: ReportCardGeneratePayload,
): Promise<ReportCardGenerateResponse> {
  return apiFetch<ReportCardGenerateResponse>('/api/spa/report-cards/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function fetchReportCardDetail(reportCardId: number): Promise<ReportCardDetailResponse> {
  return apiFetch<ReportCardDetailResponse>(`/api/spa/report-cards/${reportCardId}`)
}

export async function fetchReportCardHistory(studentId: number): Promise<ReportCardHistoryResponse> {
  return apiFetch<ReportCardHistoryResponse>(`/api/spa/report-cards/students/${studentId}/history`)
}

export async function deleteReportCard(reportCardId: number): Promise<ReportCardActionResponse> {
  return apiFetch<ReportCardActionResponse>(`/api/spa/report-cards/${reportCardId}`, {
    method: 'DELETE',
  })
}

export async function approveReportCard(reportCardId: number): Promise<ReportCardActionResponse> {
  return apiFetch<ReportCardActionResponse>(`/api/spa/report-cards/${reportCardId}/approve`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function revokeReportCard(reportCardId: number): Promise<ReportCardActionResponse> {
  return apiFetch<ReportCardActionResponse>(`/api/spa/report-cards/${reportCardId}/revoke`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export function reportCardPdfUrl(reportCardId: number): string {
  return `/api/spa/report-cards/${reportCardId}/pdf`
}
