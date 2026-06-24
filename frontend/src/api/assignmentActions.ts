import { getCsrfToken } from './client'
import type { AssignmentWorkspaceItem } from '../types/assignments'

export type DeleteAssignmentTarget = {
  id: number
  title: string
  type: 'individual' | 'group'
}

export function spaAssignmentViewPath(classId: number, item: AssignmentWorkspaceItem) {
  if (item.type === 'group') {
    return `/management/assignments/${classId}/group/${item.id}/view`
  }
  return `/management/assignments/${classId}/individual/${item.id}/view`
}

export function spaAssignmentGradePath(classId: number, item: AssignmentWorkspaceItem) {
  if (item.type === 'group') {
    return `/management/assignments/${classId}/group/${item.id}/grade`
  }
  return `/management/assignments/${classId}/individual/${item.id}/grade`
}

function resolveAssignmentPath(
  item: AssignmentWorkspaceItem,
  mode: 'view' | 'grade',
  classId?: number,
) {
  if (classId) {
    return mode === 'view' ? spaAssignmentViewPath(classId, item) : spaAssignmentGradePath(classId, item)
  }
  const path = mode === 'view' ? item.links.view : item.links.grade
  return path || null
}

export function openAssignmentView(
  item: AssignmentWorkspaceItem,
  navigate?: (path: string) => void,
  classId?: number,
) {
  const path = resolveAssignmentPath(item, 'view', classId)
  if (!path) return
  if (navigate) {
    navigate(path)
    return
  }
  window.location.assign(path.startsWith('/app') ? path : `/app${path}`)
}

export function openAssignmentGrade(
  item: AssignmentWorkspaceItem,
  navigate?: (path: string) => void,
  classId?: number,
) {
  const path = resolveAssignmentPath(item, 'grade', classId)
  if (!path) return
  if (navigate) {
    navigate(path)
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

export async function removeIndividualAssignment(assignmentId: number, classId: number) {
  return postLegacyAction(`/management/remove-assignment/${assignmentId}?class_id=${classId}`)
}

export async function removeGroupAssignment(assignmentId: number) {
  return postLegacyAction(`/management/group-assignment/${assignmentId}/delete`)
}
