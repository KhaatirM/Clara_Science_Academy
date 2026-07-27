import type { SessionUser } from '../types/session'

export function canStaffAdminUi(user: SessionUser): boolean {
  return user.management_entry || user.permissions.includes('teachers_staff:manage')
}
