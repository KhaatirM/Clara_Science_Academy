import type { SessionUser } from '../types/session'

/** Matches backend `_can_student_admin_ui` (Director/Admin or explicit students:edit). */
export function canStudentAdminUi(user: SessionUser): boolean {
  return user.management_entry || user.permissions.includes('students:edit')
}

export function canStudentView(user: SessionUser): boolean {
  return (
    canStudentAdminUi(user) ||
    user.permissions.includes('students:view')
  )
}
