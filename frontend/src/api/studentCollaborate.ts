import { apiFetch } from './client'
import type { StudentCollaborateResponse } from '../types/studentCollaborate'

export async function fetchStudentCollaborate() {
  return apiFetch<StudentCollaborateResponse>('/api/spa/student/collaborate')
}

export async function submitCollaborateFeedback(payload: {
  feedback360_id: number
  answers: Record<string, string | number>
  is_anonymous: boolean
}) {
  return apiFetch<{ success: boolean; message: string }>('/api/spa/student/collaborate/feedback', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function submitCollaborateJournal(payload: {
  group_assignment_id: number
  group_id: number
  reflection_text: string
  collaboration_rating: number
  learning_rating: number
  challenges_faced?: string
  lessons_learned?: string
}) {
  return apiFetch<{ success: boolean; message: string }>('/api/spa/student/collaborate/journal', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function submitCollaborateConflict(payload: {
  group_assignment_id: number
  group_id: number
  conflict_type: string
  severity_level: string
  conflict_description: string
}) {
  return apiFetch<{ success: boolean; message: string }>('/api/spa/student/collaborate/conflict', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
