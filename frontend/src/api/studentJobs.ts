import { apiFetch } from './client'
import type {
  CleaningInspectionPayload,
  CreateStudentJobsTeamPayload,
  StudentJobsHubResponse,
  StudentJobsInspectionDetail,
  StudentJobsInspectionHistoryResponse,
  StudentJobsStudentOption,
} from '../types/studentJobs'

export async function fetchStudentJobsHub(): Promise<StudentJobsHubResponse> {
  return apiFetch<StudentJobsHubResponse>('/api/spa/student-jobs/hub')
}

export async function createStudentJobsTeam(payload: CreateStudentJobsTeamPayload) {
  return apiFetch<{ success: boolean; team_id?: number; message?: string; error?: string }>(
    '/api/spa/student-jobs/teams',
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export async function archiveStudentJobsTeam(teamId: number) {
  return apiFetch<{ success: boolean; message?: string; error?: string }>(
    `/api/spa/student-jobs/teams/${teamId}/archive`,
    { method: 'POST' },
  )
}

export async function fetchInspectionHistory(page = 1, perPage = 10) {
  return apiFetch<StudentJobsInspectionHistoryResponse>(
    `/api/spa/student-jobs/inspections?page=${page}&per_page=${perPage}`,
  )
}

export async function fetchAllInspectionsForExport() {
  return apiFetch<StudentJobsInspectionHistoryResponse>(
    '/api/spa/student-jobs/inspections?export=true&per_page=5000',
  )
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

export async function createTeamDuty(
  teamId: number,
  payload: { name: string; area?: string; description?: string; scoring_type?: string },
) {
  return apiFetch<{ success: boolean; duty_id?: number; message?: string; error?: string }>(
    `/api/spa/student-jobs/teams/${teamId}/duties`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export async function updateTeamDuty(
  dutyId: number,
  payload: { name?: string; area?: string; description?: string; scoring_type?: string },
) {
  return apiFetch<{ success: boolean; message?: string; error?: string }>(
    `/api/spa/student-jobs/duties/${dutyId}`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export async function deleteTeamDuty(dutyId: number) {
  return apiFetch<{ success: boolean; message?: string; error?: string }>(
    `/api/spa/student-jobs/duties/${dutyId}`,
    { method: 'DELETE' },
  )
}

export async function updateTeamMember(
  memberId: number,
  payload: { role?: string; assignment_description?: string; task_id?: number | null },
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
  return apiFetch<{ success: boolean; inspection: StudentJobsInspectionDetail; error?: string }>(
    `/api/spa/student-jobs/inspections/${inspectionId}`,
  )
}

export async function archiveInspection(inspectionId: number, archived = true) {
  return apiFetch<{ success: boolean; message?: string; error?: string }>(
    `/api/spa/student-jobs/inspections/${inspectionId}/archive`,
    { method: 'POST', body: JSON.stringify({ archived }) },
  )
}

export async function deleteInspection(inspectionId: number) {
  return apiFetch<{ success: boolean; message?: string; error?: string }>(
    `/api/spa/student-jobs/inspections/${inspectionId}`,
    { method: 'DELETE' },
  )
}
