import { apiFetch } from './client'
import type { ApiActionResponse, ExtensionsHubResponse } from '../types/extensions'
import type { AssignmentWorkspaceScope } from '../utils/assignmentWorkspaceScope'

function extensionsApiBase(scope: AssignmentWorkspaceScope) {
  return scope === 'teacher' ? '/api/spa/teacher/extensions' : '/api/spa/extensions'
}

export async function fetchExtensionsHub(
  scope: AssignmentWorkspaceScope = 'management',
): Promise<ExtensionsHubResponse> {
  return apiFetch<ExtensionsHubResponse>(extensionsApiBase(scope))
}

export async function reviewExtensionRequest(
  requestId: number,
  action: 'approve' | 'reject',
  reviewNotes = '',
  scope: AssignmentWorkspaceScope = 'management',
): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`${extensionsApiBase(scope)}/${requestId}/review`, {
    method: 'POST',
    body: JSON.stringify({ action, review_notes: reviewNotes }),
  })
}

export async function bulkReviewExtensionRequests(
  requestIds: number[],
  action: 'approve' | 'reject',
  reviewNotes = '',
  scope: AssignmentWorkspaceScope = 'management',
): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`${extensionsApiBase(scope)}/bulk-review`, {
    method: 'POST',
    body: JSON.stringify({ request_ids: requestIds, action, review_notes: reviewNotes }),
  })
}
