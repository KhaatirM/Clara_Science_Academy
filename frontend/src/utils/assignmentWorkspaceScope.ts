import { useLocation } from 'react-router-dom'

export type AssignmentWorkspaceScope = 'management' | 'teacher'

export function useAssignmentWorkspaceScope(): AssignmentWorkspaceScope {
  const { pathname } = useLocation()
  return pathname.startsWith('/teacher/') ? 'teacher' : 'management'
}

export function assignmentWorkspaceApiBase(scope: AssignmentWorkspaceScope): string {
  return scope === 'teacher' ? '/api/spa/teacher/assignments' : '/api/spa/assignments'
}

export function assignmentWorkspaceHubPath(scope: AssignmentWorkspaceScope, classId?: number): string {
  if (scope === 'teacher') {
    return classId ? `/teacher/assignments-and-grades/${classId}` : '/teacher/assignments-and-grades'
  }
  return classId ? `/management/assignments/${classId}` : '/management/assignments'
}
