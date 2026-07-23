import { apiFetch } from './client'
import type { TeacherClassesResponse } from '../types/teacherClasses'
import type { TeacherClassViewResponse } from '../types/teacherClassView'

export async function fetchTeacherClasses() {
  return apiFetch<TeacherClassesResponse>('/api/spa/teacher/classes')
}

export async function fetchTeacherClassView(classId: number | string) {
  return apiFetch<TeacherClassViewResponse>(`/api/spa/teacher/classes/${classId}`)
}
