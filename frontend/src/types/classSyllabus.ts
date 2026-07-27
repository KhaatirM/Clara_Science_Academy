export type SyllabusBlock = {
  type: 'paragraph' | 'bullet' | string
  text: string
}

export type SyllabusSection = {
  title: string
  level: number
  blocks: SyllabusBlock[]
}

export type SyllabusOutline = {
  title: string
  sections: SyllabusSection[]
}

export type ClassSyllabusPayload = {
  id: number
  class_id: number
  original_filename: string
  content_type: string | null
  file_size: number | null
  download_url: string
  uploaded_at: string | null
  updated_at: string | null
  uploaded_by: string | null
  outline: SyllabusOutline
  can_manage: boolean
  has_file: boolean
}

export type ClassSyllabusResponse = {
  class: { id: number; name: string; subject: string }
  syllabus: ClassSyllabusPayload | null
  can_manage: boolean
  allowed_extensions: string[]
  success?: boolean
  message?: string
}
