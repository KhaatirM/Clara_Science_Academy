import { apiFetch, getCsrfToken } from './client'
import type { ParentProvisionAllResponse, ParentsHubResponse } from '../types/parents'

export async function fetchParentsHub(): Promise<ParentsHubResponse> {
  return apiFetch<ParentsHubResponse>('/api/spa/parents')
}

export async function provisionAllParentLogins(): Promise<ParentProvisionAllResponse> {
  const form = new FormData()
  const token = getCsrfToken()
  if (token) form.set('csrf_token', token)

  const response = await fetch('/management/parents/provision-all', {
    method: 'POST',
    body: form,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...(token ? { 'X-CSRFToken': token } : {}),
    },
  })

  const data = (await response.json().catch(() => ({}))) as ParentProvisionAllResponse
  if (!response.ok || !data.success) {
    throw new Error(data.message || 'Bulk provisioning failed')
  }
  return data
}
