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
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    body: formData,
  })
  const data = (await response.json()) as CreateFormResponse
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
