import type { StudentDetail } from '../types/students'

export function formatStudentFullName(
  detail: Pick<StudentDetail, 'first_name' | 'middle_name' | 'last_name'>,
): string {
  return [detail.first_name, detail.middle_name, detail.last_name].filter(Boolean).join(' ')
}

export function studentInitials(
  detail: Pick<StudentDetail, 'first_name' | 'last_name'>,
): string {
  const a = detail.first_name?.[0] ?? ''
  const b = detail.last_name?.[0] ?? ''
  return (a + b).toUpperCase() || '?'
}
