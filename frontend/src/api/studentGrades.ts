import { apiFetch } from './client'
import type { StudentGradesResponse } from '../types/studentGrades'

export async function fetchStudentGrades() {
  return apiFetch<StudentGradesResponse>('/api/spa/student/grades')
}
