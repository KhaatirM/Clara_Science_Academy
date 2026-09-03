export type ClassNotesMediaKind = 'document' | 'image' | 'video' | 'other' | string

export type ClassNotesItemSource = 'upload' | 'drive'

export type ClassNotesItem = {
  id: number
  source?: ClassNotesItemSource
  class_id: number
  folder_id: number | null
  title: string
  original_filename: string
  content_type: string | null
  file_size: number | null
  media_kind: ClassNotesMediaKind
  duration_seconds: number | null
  download_url: string
  web_view_link?: string | null
  uploaded_at: string | null
  uploaded_by: string | null
}

export type ClassNotesDriveLink = {
  id: number
  class_id: number
  folder_id: number | null
  drive_folder_id: string
  drive_folder_name: string
  drive_web_view_link: string | null
  include_subfolders: boolean
  last_synced_at: string | null
  last_error: string | null
  needs_reauth: boolean
  is_stale?: boolean
  linked_by: string | null
  item_count: number
}

export type ClassNotesFolder = {
  id: number
  parent_id?: number | null
  name: string
  description: string
  sort_order: number
  depth?: number
  item_count: number
  is_drive_folder?: boolean
  items: ClassNotesItem[]
  children?: ClassNotesFolder[]
  created_at: string | null
}

export type ClassNotesBulkResult = {
  ok: boolean
  filename?: string | null
  error?: string
  item?: ClassNotesItem
}

export type ClassNotesResponse = {
  class: { id: number; name: string; subject: string }
  folders: ClassNotesFolder[]
  folders_flat?: ClassNotesFolder[]
  root_items: ClassNotesItem[]
  drive_links?: ClassNotesDriveLink[]
  drive_link?: ClassNotesDriveLink
  can_manage: boolean
  allowed_extensions: string[]
  max_video_seconds: number
  max_folder_depth?: number
  success?: boolean
  message?: string
  results?: ClassNotesBulkResult[]
}
