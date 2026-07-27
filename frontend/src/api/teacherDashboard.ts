import { apiFetch } from './client'
import type { TeacherDashboardHomeResponse } from '../types/teacherDashboard'

export async function fetchTeacherDashboardHome() {
  return apiFetch<TeacherDashboardHomeResponse>('/api/spa/teacher/dashboard/home')
}
