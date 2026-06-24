import { apiFetch } from './client'

export interface CreateAssignmentMeta {
  preselected_class: { id: number; name: string; subject?: string | null } | null
  back_url: string
  links: {
    pdf_in_class: string
    pdf_homework: string
    quiz: string
    discussion: string
    group: string
  }
  meta?: { can_manage?: boolean }
}

export async function fetchCreateAssignmentMeta(classId?: number | null) {
  const qs = classId ? `?class_id=${classId}` : ''
  return apiFetch<CreateAssignmentMeta>(`/api/spa/assignments/create${qs}`)
}
