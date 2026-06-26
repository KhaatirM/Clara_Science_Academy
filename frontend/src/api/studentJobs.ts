import { apiFetch } from './client'
import type {
  CleaningInspectionPayload,
  StudentJobsHubResponse,
  StudentJobsStudentOption,
} from '../types/studentJobs'

export async function fetchStudentJobsHub(): Promise<StudentJobsHubResponse> {
  return apiFetch<StudentJobsHubResponse>('/api/spa/student-jobs/hub')
}

export async function fetchStudentJobsStudents(): Promise<StudentJobsStudentOption[]> {
  const data = await apiFetch<{ success: boolean; students: StudentJobsStudentOption[] }>(
    '/api/spa/student-jobs/students',
  )
  return data.students
}

export async function addTeamMembers(teamId: number, studentIds: number[]) {
  return apiFetch<{ success: boolean; message?: string; error?: string }>(
    `/api/spa/student-jobs/teams/${teamId}/members`,
    { method: 'POST', body: JSON.stringify({ student_ids: studentIds }) },
  )
}

export async function removeTeamMembers(teamId: number, memberIds: number[]) {
  return apiFetch<{ success: boolean; message?: string; error?: string }>(
    `/api/spa/student-jobs/teams/${teamId}/members/remove`,
    { method: 'POST', body: JSON.stringify({ member_ids: memberIds }) },
  )
}

export async function updateTeamMember(
  memberId: number,
  payload: { role?: string; assignment_description?: string },
) {
  return apiFetch<{ success: boolean; message?: string; error?: string }>(
    `/api/spa/student-jobs/members/${memberId}`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export async function saveStudentJobsInspection(payload: CleaningInspectionPayload) {
  return apiFetch<{ success: boolean; message?: string; inspection_id?: number }>(
    '/api/spa/student-jobs/inspections',
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export async function fetchInspectionDetail(inspectionId: number) {
  return apiFetch<{ success: boolean; inspection: Record<string, unknown> }>(
    `/api/spa/student-jobs/inspections/${inspectionId}`,
  )
}
