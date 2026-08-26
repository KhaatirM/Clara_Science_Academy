import { getCsrfToken } from './client'

export interface CreateFormResponse {
  success?: boolean
  message?: string
  error?: string
  redirect_url?: string
}

export async function postAssignmentForm(url: string, formData: FormData): Promise<CreateFormResponse> {
  const token = getCsrfToken()
  if (token) formData.append('csrf_token', token)
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  }
  if (token) headers['X-CSRFToken'] = token

  const response = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: formData,
  })

  const raw = await response.text()
  let data: CreateFormResponse = {}
  try {
    data = raw ? (JSON.parse(raw) as CreateFormResponse) : {}
  } catch {
    throw new Error(
      response.ok
        ? 'Server returned an unexpected response. Try again.'
        : `Request failed (${response.status}). Check that you are still signed in and try again.`,
    )
  }
  if (!response.ok || data.success === false) {
    throw new Error(data.message || data.error || `Request failed (${response.status})`)
  }
  return data
}

export function appendIfChecked(form: FormData, name: string, checked: boolean) {
  if (checked) form.append(name, 'on')
}

export function appendDatetime(form: FormData, name: string, value: string) {
  if (value.trim()) form.append(name, value)
}
