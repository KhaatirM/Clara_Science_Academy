import { getCsrfToken } from './client'
import type { AssignmentWorkspaceItem } from '../types/assignments'
import type { AssignmentWorkspaceScope } from '../utils/assignmentWorkspaceScope'

export type DeleteAssignmentTarget = {
  id: number
  title: string
  type: 'individual' | 'group'
}

export function spaAssignmentViewPath(
  classId: number,
  item: AssignmentWorkspaceItem,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const base = scope === 'teacher' ? `/teacher/assignments-and-grades/${classId}` : `/management/assignments/${classId}`
  if (item.type === 'group') {
    return `${base}/group/${item.id}/view`
  }
  return `${base}/individual/${item.id}/view`
}

export function assignmentTypeGradesViaSubmissions(assignmentType: string | null | undefined): boolean {
  const t = (assignmentType || '').toLowerCase().replace(/[/\s-]+/g, '_')
  return t === 'discussion' || t === 'quiz'
}

export function spaAssignmentSubmissionsPath(
  classId: number,
  item: AssignmentWorkspaceItem,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const base = scope === 'teacher' ? `/teacher/assignments-and-grades/${classId}` : `/management/assignments/${classId}`
  if (item.type === 'group') {
    return `${base}/group/${item.id}/submissions`
  }
  return `${base}/individual/${item.id}/submissions`
}

export function spaAssignmentGradePath(
  classId: number,
  item: AssignmentWorkspaceItem,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const base = scope === 'teacher' ? `/teacher/assignments-and-grades/${classId}` : `/management/assignments/${classId}`
  if (item.type === 'group') {
    return `${base}/group/${item.id}/grade`
  }
  return `${base}/individual/${item.id}/grade`
}

function resolveAssignmentPath(
  item: AssignmentWorkspaceItem,
  mode: 'view' | 'grade',
  classId?: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  if (classId) {
    return mode === 'view'
      ? spaAssignmentViewPath(classId, item, scope)
      : spaAssignmentGradePath(classId, item, scope)
  }
  const path = mode === 'view' ? item.links.view : item.links.grade
  return path || null
}

export function openAssignmentView(
  item: AssignmentWorkspaceItem,
  navigate?: (path: string) => void,
  classId?: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const path = resolveAssignmentPath(item, 'view', classId, scope)
  if (!path) return
  if (navigate) {
    navigate(path.startsWith('/app') ? path.replace(/^\/app/, '') : path)
    return
  }
  window.location.assign(path.startsWith('/app') ? path : `/app${path}`)
}

export function openAssignmentGrade(
  item: AssignmentWorkspaceItem,
  navigate?: (path: string) => void,
  classId?: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const path = resolveAssignmentPath(item, 'grade', classId, scope)
  if (!path) return
  if (navigate) {
    navigate(path.startsWith('/app') ? path.replace(/^\/app/, '') : path)
    return
  }
  window.location.assign(path.startsWith('/app') ? path : `/app${path}`)
}

async function postLegacyAction(url: string): Promise<{ success: boolean; message: string }> {
  const formData = new FormData()
  const token = getCsrfToken()
  if (token) formData.append('csrf_token', token)

  const response = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: formData,
  })

  const data = (await response.json()) as { success?: boolean; message?: string; error?: string }
  if (!response.ok || data.success === false) {
    throw new Error(data.message || data.error || `Request failed (${response.status})`)
  }
  return { success: true, message: data.message || 'Done' }
}

export async function removeIndividualAssignment(
  assignmentId: number,
  classId: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const url =
    scope === 'teacher'
      ? `/teacher/assignment/remove/${assignmentId}?class_id=${classId}`
      : `/management/remove-assignment/${assignmentId}?class_id=${classId}`
  return postLegacyAction(url)
}

export async function removeGroupAssignment(
  assignmentId: number,
  scope: AssignmentWorkspaceScope = 'management',
) {
  const url =
    scope === 'teacher'
      ? `/teacher/group-assignment/${assignmentId}/delete`
      : `/management/group-assignment/${assignmentId}/delete`
  return postLegacyAction(url)
}
