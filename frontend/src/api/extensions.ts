import { apiFetch } from './client'
import type { ApiActionResponse, ExtensionsHubResponse } from '../types/extensions'

export async function fetchExtensionsHub(): Promise<ExtensionsHubResponse> {
  return apiFetch<ExtensionsHubResponse>('/api/spa/extensions')
}

export async function reviewExtensionRequest(
  requestId: number,
  action: 'approve' | 'reject',
  reviewNotes = '',
): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`/api/spa/extensions/${requestId}/review`, {
    method: 'POST',
    body: JSON.stringify({ action, review_notes: reviewNotes }),
  })
}

export async function bulkReviewExtensionRequests(
  requestIds: number[],
  action: 'approve' | 'reject',
  reviewNotes = '',
): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>('/api/spa/extensions/bulk-review', {
    method: 'POST',
    body: JSON.stringify({ request_ids: requestIds, action, review_notes: reviewNotes }),
  })
}
