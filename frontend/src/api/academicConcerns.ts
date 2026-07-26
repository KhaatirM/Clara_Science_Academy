import { apiFetch } from './client'
import type {
  AcademicConcernsHubResponse,
  AcademicConcernStudentDetailsResponse,
} from '../types/academicConcerns'

export async function fetchAcademicConcerns(scope: 'management' | 'teacher') {
  return apiFetch<AcademicConcernsHubResponse>(`/api/spa/academic-concerns?scope=${scope}`)
}

export async function fetchAcademicConcernStudent(
  studentId: number,
  scope: 'management' | 'teacher',
) {
  return apiFetch<AcademicConcernStudentDetailsResponse>(
    `/api/spa/academic-concerns/${studentId}?scope=${scope}`,
  )
}

export const ACADEMIC_CONCERNS_OPEN_EVENT = 'clara:open-academic-concerns'

export function openAcademicConcernsModal() {
  window.dispatchEvent(new CustomEvent(ACADEMIC_CONCERNS_OPEN_EVENT))
}
