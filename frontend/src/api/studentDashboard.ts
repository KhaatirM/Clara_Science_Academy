import { apiFetch } from './client'
import type { StudentDashboardHomeResponse } from '../types/studentDashboard'

export async function fetchStudentDashboardHome() {
  return apiFetch<StudentDashboardHomeResponse>('/api/spa/student/dashboard/home')
}

export async function setStudentGoal(classId: number, targetGrade: number) {
  return apiFetch<{ success: boolean; message: string; goal_id?: number }>('/api/spa/student/goals', {
    method: 'POST',
    body: JSON.stringify({ class_id: classId, target_grade: targetGrade }),
  })
}

export async function deleteStudentGoal(goalId: number) {
  return apiFetch<{ success: boolean; message: string }>(`/api/spa/student/goals/${goalId}`, {
    method: 'DELETE',
  })
}
