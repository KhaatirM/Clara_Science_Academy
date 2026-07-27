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
): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`${redoApiBase(scope)}/redo-requests/${requestId}/grant`, {
    method: 'POST',
    body: JSON.stringify({ redo_deadline: redoDeadline }),
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
