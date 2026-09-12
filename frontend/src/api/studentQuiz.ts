import { apiFetch } from './client'
import type { QuizSubmitResponse, StudentQuizResponse } from '../types/studentQuiz'

export async function fetchStudentQuiz(
  assignmentId: number,
  opts: { retake?: boolean; attemptSubmissionId?: number | null } = {},
) {
  const params = new URLSearchParams()
  if (opts.retake) params.set('retake', 'true')
  if (opts.attemptSubmissionId != null) params.set('attempt', String(opts.attemptSubmissionId))
  const qs = params.toString()
  return apiFetch<StudentQuizResponse>(
    `/api/spa/student/quiz/${assignmentId}${qs ? `?${qs}` : ''}`,
  )
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
  opts?: { keepalive?: boolean },
) {
  return apiFetch<{
    success: boolean
    message?: string
    timer_remaining_seconds?: number | null
    timer_is_paused?: boolean
  }>(`/student/save-quiz-progress/${assignmentId}`, {
    method: 'POST',
    body: JSON.stringify(payload),
    keepalive: Boolean(opts?.keepalive),
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
