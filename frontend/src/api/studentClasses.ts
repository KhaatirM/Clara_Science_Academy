import { apiFetch } from './client'
import type { StudentClassesResponse } from '../types/studentClasses'
import type { StudentClassDetailResponse } from '../types/studentClassView'

export async function fetchStudentClasses() {
  return apiFetch<StudentClassesResponse>('/api/spa/student/classes')
}

export async function fetchStudentClassDetail(classId: number | string) {
  return apiFetch<StudentClassDetailResponse>(`/api/spa/student/classes/${classId}`)
}
