import { apiFetch, getCsrfToken } from './client'

export type AnnouncementBroadcastOption = {
  value: string
  label: string
  description?: string
  class_id?: number
  is_current?: boolean
}

export type AnnouncementPanelItem = {
  id: number
  title: string
  message: string
  timestamp: string | null
  target_group: string
  target_label: string
  class_id: number | null
  is_important: boolean
  sender_name: string
}

export type AnnouncementComposePayload = {
  success: boolean
  current_class: { id: number; name: string } | null
  can_broadcast_all_students: boolean
  default_broadcast: string
  broadcast_options: AnnouncementBroadcastOption[]
  past_announcements: AnnouncementPanelItem[]
  message?: string
}

export async function fetchAnnouncementCompose(classId?: number | null) {
  const qs = classId ? `?class_id=${classId}` : ''
  return apiFetch<AnnouncementComposePayload>(`/communications/api/announcement-compose${qs}`)
}

export async function createAnnouncement(payload: {
  title: string
  message: string
  broadcast: string
  is_important: boolean
}) {
  const body = new FormData()
  body.append('title', payload.title)
  body.append('message', payload.message)
  if (payload.is_important) body.append('is_important', 'on')

  if (payload.broadcast === 'all_students') {
    body.append('target_group', 'all_students')
  } else if (payload.broadcast.startsWith('class:')) {
    body.append('target_group', 'class')
    body.append('class_id', payload.broadcast.slice('class:'.length))
  } else {
    throw new Error('Select a broadcast audience')
  }

  const headers = new Headers()
  const csrf = getCsrfToken()
  if (csrf) headers.set('X-CSRFToken', csrf)

  const response = await fetch('/communications/create-announcement', {
    method: 'POST',
    body,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
  })
  const data = (await response.json().catch(() => ({}))) as {
    success?: boolean
    message?: string
    announcement?: AnnouncementPanelItem
  }
  if (!response.ok || !data.success) {
    throw new Error(data.message || `Could not send announcement (${response.status})`)
  }
  return data
}
