import { apiFetch, getCsrfToken } from './client'

export type DriveStatus = {
  connected: boolean
  connect_url: string
  settings_path: string
  message?: string | null
}

export type DriveEntry = {
  id: string
  name: string
  mime_type: string
  is_folder: boolean
  size: number | null
  modified_time?: string | null
  icon_link?: string | null
}

export type DriveBrowseResponse = {
  folder_id: string
  folder_name: string
  parent_id: string | null
  folders: DriveEntry[]
  files: DriveEntry[]
}

export async function fetchDriveStatus(scope?: 'teacher' | 'management') {
  const qs = scope ? `?scope=${scope}` : ''
  return apiFetch<DriveStatus>(`/api/spa/drive/status${qs}`)
}

export async function browseDrive(folderId = 'root') {
  const qs = new URLSearchParams({ folder_id: folderId })
  return apiFetch<DriveBrowseResponse>(`/api/spa/drive/browse?${qs}`)
}

export async function downloadDriveFileAsBrowserFile(fileId: string, fallbackName?: string) {
  const headers = new Headers({ Accept: '*/*' })
  const token = getCsrfToken()
  if (token) headers.set('X-CSRFToken', token)

  const response = await fetch(`/api/spa/drive/files/${encodeURIComponent(fileId)}/content`, {
    method: 'GET',
    credentials: 'same-origin',
    headers,
    cache: 'no-store',
  })
  if (!response.ok) {
    let message = `Download failed (${response.status})`
    try {
      const data = (await response.json()) as { error?: string }
      if (data.error) message = data.error
    } catch {
      // ignore
    }
    throw new Error(message)
  }
  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = /filename\*?=(?:UTF-8''|")?([^\";]+)/i.exec(disposition)
  let name = fallbackName || 'download'
  if (match?.[1]) {
    try {
      name = decodeURIComponent(match[1].replace(/"/g, '').trim())
    } catch {
      name = match[1].replace(/"/g, '').trim() || name
    }
  }
  const type = blob.type || response.headers.get('Content-Type') || 'application/octet-stream'
  return new File([blob], name, { type })
}
