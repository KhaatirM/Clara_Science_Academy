import { apiFetch } from './client'
import type { ClassGroupsAction, ClassGroupsResponse } from '../types/classGroups'

export type ClassGroupsScope = 'management' | 'teacher'

function groupsBase(classId: number, scope: ClassGroupsScope) {
  return scope === 'teacher'
    ? `/api/spa/teacher/classes/${classId}/groups`
    : `/api/spa/classes/${classId}/groups`
}

export async function fetchClassGroups(
  classId: number,
  scope: ClassGroupsScope = 'management',
) {
  const qs = scope === 'teacher' ? '?full=1' : ''
  return apiFetch<ClassGroupsResponse>(`${groupsBase(classId, scope)}${qs}`)
}

export async function mutateClassGroups(
  classId: number,
  body: ClassGroupsAction,
  scope: ClassGroupsScope = 'management',
) {
  return apiFetch<{ success: boolean; message: string; group_id?: number }>(
    groupsBase(classId, scope),
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
  )
}
