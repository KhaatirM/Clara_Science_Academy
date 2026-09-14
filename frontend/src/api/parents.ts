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

export async function downloadParentLoginLetter(userId: number, resetPassword: boolean): Promise<void> {
  const token = getCsrfToken()
  const response = await fetch(`/api/spa/parents/${userId}/login-letter`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/pdf',
      'Content-Type': 'application/json',
      ...(token ? { 'X-CSRFToken': token } : {}),
    },
    body: JSON.stringify({ reset_password: resetPassword }),
  })

  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { message?: string }
    throw new Error(data.message || 'Could not generate the login letter')
  }

  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = /filename="([^"]+)"/.exec(disposition)
  const filename = match?.[1] || 'Family-Portal-Login.pdf'
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
