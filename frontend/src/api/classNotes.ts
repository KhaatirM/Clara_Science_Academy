import { apiFetch, getCsrfToken } from './client'
import type { ClassNotesResponse } from '../types/classNotes'

export async function fetchClassNotes(classId: number) {
  return apiFetch<ClassNotesResponse>(`/api/spa/classes/${classId}/notes`)
}

export async function createClassNotesFolder(
  classId: number,
  body: { name: string; description?: string; parent_id?: number | null },
) {
  return apiFetch<ClassNotesResponse>(`/api/spa/classes/${classId}/notes/folders`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateClassNotesFolder(
  classId: number,
  folderId: number,
  body: { name?: string; description?: string; parent_id?: number | null },
) {
  return apiFetch<ClassNotesResponse>(`/api/spa/classes/${classId}/notes/folders/${folderId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function deleteClassNotesFolder(classId: number, folderId: number) {
  return apiFetch<ClassNotesResponse>(`/api/spa/classes/${classId}/notes/folders/${folderId}`, {
    method: 'DELETE',
  })
}

export async function uploadClassNotesItem(
  classId: number,
  file: File,
  opts?: { folderId?: number | null; title?: string; durationSeconds?: number | null },
) {
  const body = new FormData()
  body.append('file', file)
  if (opts?.folderId != null) body.append('folder_id', String(opts.folderId))
  if (opts?.title) body.append('title', opts.title)
  if (opts?.durationSeconds != null && Number.isFinite(opts.durationSeconds)) {
    body.append('duration_seconds', String(opts.durationSeconds))
  }

  const headers = new Headers()
  const csrf = getCsrfToken()
  if (csrf) headers.set('X-CSRFToken', csrf)

  const response = await fetch(`/api/spa/classes/${classId}/notes/items`, {
    method: 'POST',
    body,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
  })
  const data = (await response.json().catch(() => ({}))) as ClassNotesResponse & {
    error?: string
    message?: string
  }
  if (!response.ok) {
    throw new Error(data.error || data.message || `Upload failed (${response.status})`)
  }
  return data
}

export async function uploadClassNotesItemsBulk(
  classId: number,
  files: File[],
  opts?: { folderId?: number | null },
) {
  const body = new FormData()
  for (const file of files) body.append('files', file)
  if (opts?.folderId != null) body.append('folder_id', String(opts.folderId))

  const headers = new Headers()
  const csrf = getCsrfToken()
  if (csrf) headers.set('X-CSRFToken', csrf)

  const response = await fetch(`/api/spa/classes/${classId}/notes/items/bulk`, {
    method: 'POST',
    body,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
  })
  const data = (await response.json().catch(() => ({}))) as ClassNotesResponse & {
    error?: string
    message?: string
  }
  if (!response.ok && !data.results?.length) {
    throw new Error(data.error || data.message || `Upload failed (${response.status})`)
  }
  return data
}

export async function deleteClassNotesItem(classId: number, itemId: number) {
  return apiFetch<ClassNotesResponse>(`/api/spa/classes/${classId}/notes/items/${itemId}`, {
    method: 'DELETE',
  })
}

export function classNotesItemDownloadUrl(classId: number, itemId: number) {
  return `/api/spa/classes/${classId}/notes/items/${itemId}/download`
}

export async function linkClassNotesDriveFolder(
  classId: number,
  body: { folder_url: string; folder_id?: number | null; include_subfolders?: boolean },
) {
  return apiFetch<ClassNotesResponse>(`/api/spa/classes/${classId}/notes/drive/link`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function syncClassNotesDriveLink(classId: number, linkId: number) {
  return apiFetch<ClassNotesResponse>(
    `/api/spa/classes/${classId}/notes/drive/links/${linkId}/sync`,
    { method: 'POST' },
  )
}

export async function unlinkClassNotesDriveFolder(classId: number, linkId: number) {
  return apiFetch<ClassNotesResponse>(`/api/spa/classes/${classId}/notes/drive/links/${linkId}`, {
    method: 'DELETE',
  })
}

/** Read video duration in the browser (used before upload). */
export function readVideoDurationSeconds(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      const duration = video.duration
      URL.revokeObjectURL(url)
      if (!Number.isFinite(duration) || duration <= 0) {
        reject(new Error('Could not read video length'))
        return
      }
      resolve(duration)
    }
    video.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Could not read video length'))
    }
    video.src = url
  })
}
