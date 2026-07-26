import { apiFetch } from './client'
import type { QuizSubmitResponse, StudentQuizResponse } from '../types/studentQuiz'

export async function fetchStudentQuiz(assignmentId: number, retake = false) {
  const qs = retake ? '?retake=true' : ''
  return apiFetch<StudentQuizResponse>(`/api/spa/student/quiz/${assignmentId}${qs}`)
}

export async function submitStudentQuiz(
  assignmentId: number,
  answers: Record<string, string>,
  quizOpenedAt?: string | null,
) {
  return apiFetch<QuizSubmitResponse>(`/api/spa/student/quiz/${assignmentId}/submit`, {
    method: 'POST',
    body: JSON.stringify({
      answers,
      quiz_opened_at: quizOpenedAt || undefined,
    }),
  })
}

export async function saveQuizProgress(
  assignmentId: number,
  payload: {
    answers: Record<string, string>
    progress_percentage: number
    questions_answered: number
    pause_timer?: boolean
  },
) {
  return apiFetch<{
    success: boolean
    message?: string
    timer_remaining_seconds?: number | null
    timer_is_paused?: boolean
  }>(`/student/save-quiz-progress/${assignmentId}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function loadQuizProgress(assignmentId: number) {
  return apiFetch<{
    success: boolean
    message?: string
    progress?: {
      answers: Record<string, string>
      progress_percentage: number
      questions_answered: number
      timer_remaining_seconds?: number | null
      timer_is_paused?: boolean
    }
  }>(`/student/load-quiz-progress/${assignmentId}`)
}

export async function quizKeepalive(assignmentId: number) {
  return apiFetch<{ success?: boolean }>(`/student/quiz-keepalive/${assignmentId}`)
}
