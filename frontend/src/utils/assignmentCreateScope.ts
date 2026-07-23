import { useLocation } from 'react-router-dom'

export type AssignmentCreateScope = 'management' | 'teacher'

export function useAssignmentCreateScope(): AssignmentCreateScope {
  const { pathname } = useLocation()
  return pathname.startsWith('/teacher/assignments/create') ? 'teacher' : 'management'
}

export function assignmentCreateApiBase(scope: AssignmentCreateScope): string {
  return scope === 'teacher' ? '/api/spa/teacher/assignments/create' : '/api/spa/assignments/create'
}

export function assignmentCreateRoutePrefix(scope: AssignmentCreateScope): string {
  return scope === 'teacher' ? '/teacher/assignments/create' : '/management/assignments/create'
}

export function assignmentCreateHubPath(scope: AssignmentCreateScope, classId?: number | null): string {
  const hub =
    scope === 'teacher' ? '/teacher/assignments-and-grades' : '/management/assignments'
  return classId ? `${hub}/${classId}` : hub
}
