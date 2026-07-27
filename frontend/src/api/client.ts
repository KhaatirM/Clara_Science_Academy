import type { SessionResponse } from '../types/session'

let csrfToken: string | null = null

export function setCsrfToken(token: string | null) {
  csrfToken = token
}

export function getCsrfToken(): string | null {
  return csrfToken
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text()
  if (!text) {
    throw new Error(`Empty response (${response.status})`)
  }
  try {
    return JSON.parse(text) as T
  } catch {
    throw new Error(`Invalid JSON (${response.status})`)
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (csrfToken && init.method && init.method !== 'GET') {
    headers.set('X-CSRFToken', csrfToken)
  }

  const response = await fetch(path, {
    cache: 'no-store',
    ...init,
    headers,
    credentials: 'same-origin',
  })

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || ''
    const body = await response.text().catch(() => '')

    if (contentType.includes('application/json') && body) {
      try {
        const data = JSON.parse(body) as { error?: string; message?: string }
        throw new Error(data.error || data.message || `Request failed (${response.status})`)
      } catch (err) {
        if (err instanceof Error && err.message !== `Invalid JSON (${response.status})`) {
          throw err
        }
      }
    }

    if (response.status === 404) {
      throw new Error(
        'Server endpoint not found. Restart Flask (python app.py) after pulling the latest code.',
      )
    }

    throw new Error(body?.startsWith('<!DOCTYPE') ? `Request failed (${response.status})` : body || `Request failed (${response.status})`)
  }

  return parseJson<T>(response)
}

export async function fetchSession(): Promise<SessionResponse> {
  const response = await fetch('/api/spa/me', { credentials: 'same-origin' })

  if (response.status === 401) {
    const data = (await response.json()) as SessionResponse
    window.location.href = data.login_url || '/login'
    return data
  }

  if (!response.ok) {
    throw new Error(`Session request failed (${response.status})`)
  }

  const data = (await response.json()) as SessionResponse
  if (data.user?.csrf_token) {
    setCsrfToken(data.user.csrf_token)
  }
  return data
}
