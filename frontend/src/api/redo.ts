import { apiFetch } from './client'
import type { ApiActionResponse, RedoDashboardResponse } from '../types/redo'
import type { AssignmentWorkspaceScope } from '../utils/assignmentWorkspaceScope'

function redoApiBase(scope: AssignmentWorkspaceScope) {
  return scope === 'teacher' ? '/api/spa/teacher' : '/api/spa'
}

export async function fetchRedoDashboard(
  scope: AssignmentWorkspaceScope = 'management',
): Promise<RedoDashboardResponse> {
  return apiFetch<RedoDashboardResponse>(`${redoApiBase(scope)}/redo-dashboard`)
}

export async function grantRedoRequest(
  requestId: number,
  redoDeadline: string,
  scope: AssignmentWorkspaceScope = 'management',
  options?: {
    additionalAttempts?: number
    allowReviewPreviousAttempts?: boolean
  },
): Promise<ApiActionResponse> {
  const body: {
    redo_deadline: string
    additional_attempts?: number
    allow_review_previous_attempts?: boolean
  } = {
    redo_deadline: redoDeadline,
  }
  if (options?.additionalAttempts != null && Number.isFinite(options.additionalAttempts)) {
    body.additional_attempts = Math.max(1, Math.min(20, Math.floor(options.additionalAttempts)))
  }
  if (options?.allowReviewPreviousAttempts != null) {
    body.allow_review_previous_attempts = Boolean(options.allowReviewPreviousAttempts)
  }
  return apiFetch<ApiActionResponse>(`${redoApiBase(scope)}/redo-requests/${requestId}/grant`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function rejectRedoRequest(
  requestId: number,
  scope: AssignmentWorkspaceScope = 'management',
): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`${redoApiBase(scope)}/redo-requests/${requestId}/reject`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function revokeRedo(
  redoId: number,
  scope: AssignmentWorkspaceScope = 'management',
): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`${redoApiBase(scope)}/redos/${redoId}/revoke`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function revokeReopening(
  reopeningId: number,
  scope: AssignmentWorkspaceScope = 'management',
): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`${redoApiBase(scope)}/reopenings/${reopeningId}/revoke`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}
