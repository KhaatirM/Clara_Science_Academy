import { apiFetch, getCsrfToken } from './client'
import type { TestSessionBrief } from '../types/studentQuiz'

export type TestStartResponse = {
  success: boolean
  session: TestSessionBrief
  time_limit_seconds: number | null
  snapshot_interval_seconds: number
}

export async function startTest(assignmentId: number) {
  return apiFetch<TestStartResponse>(`/api/spa/student/test/${assignmentId}/start`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function uploadTestSnapshot(sessionId: number, kind: 'screen' | 'camera', image: Blob) {
  const form = new FormData()
  form.append('kind', kind)
  form.append('image', image, `${kind}.jpg`)
  return apiFetch<{ success: boolean; status?: string }>(
    `/api/spa/student/test/session/${sessionId}/snapshot`,
    { method: 'POST', body: form },
  )
}

export async function sendTestEvents(
  sessionId: number,
  events: unknown[],
  answers: Record<string, string>,
) {
  return apiFetch<{ success: boolean; status?: string }>(
    `/api/spa/student/test/session/${sessionId}/events`,
    { method: 'POST', body: JSON.stringify({ events, answers }) },
  )
}

/** Uses keepalive so the request still completes while the tab is being hidden or closed. */
export function reportTestViolation(
  sessionId: number,
  reason: string,
  answers: Record<string, string>,
): Promise<unknown> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getCsrfToken()
  if (token) headers['X-CSRFToken'] = token
  let body = JSON.stringify({ reason, answers })
  // Browsers cap keepalive bodies at 64 KB; the server falls back to the last answers sent with events.
  if (body.length > 60000) body = JSON.stringify({ reason })
  return fetch(`/api/spa/student/test/session/${sessionId}/violation`, {
    method: 'POST',
    headers,
    body,
    credentials: 'same-origin',
    keepalive: true,
  }).catch(() => undefined)
}
