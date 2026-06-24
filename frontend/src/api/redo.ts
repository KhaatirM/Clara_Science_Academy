import { apiFetch } from './client'
import type { ApiActionResponse, RedoDashboardResponse } from '../types/redo'

export async function fetchRedoDashboard(): Promise<RedoDashboardResponse> {
  return apiFetch<RedoDashboardResponse>('/api/spa/redo-dashboard')
}

export async function grantRedoRequest(requestId: number, redoDeadline: string): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`/api/spa/redo-requests/${requestId}/grant`, {
    method: 'POST',
    body: JSON.stringify({ redo_deadline: redoDeadline }),
  })
}

export async function rejectRedoRequest(requestId: number): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`/api/spa/redo-requests/${requestId}/reject`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function revokeRedo(redoId: number): Promise<ApiActionResponse> {
  return apiFetch<ApiActionResponse>(`/api/spa/redos/${redoId}/revoke`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}
