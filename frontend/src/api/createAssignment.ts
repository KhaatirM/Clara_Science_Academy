import { apiFetch } from './client'
import type { AssignmentCreateScope } from '../utils/assignmentCreateScope'
import { assignmentCreateApiBase } from '../utils/assignmentCreateScope'

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
  meta?: { can_manage?: boolean; scope?: string }
}

export async function fetchCreateAssignmentMeta(
  classId?: number | null,
  scope: AssignmentCreateScope = 'management',
) {
  const qs = classId ? `?class_id=${classId}` : ''
  return apiFetch<CreateAssignmentMeta>(`${assignmentCreateApiBase(scope)}${qs}`)
}
