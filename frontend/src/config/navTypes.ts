import type { SessionUser } from '../types/session'

export interface NavItem {
  id: string
  label: string
  adminStaffLabel?: string
  icon: string
  /** In-app React route (basename /app is applied by the router). */
  reactTo?: string
  /** Full-page legacy URL — leaves the React shell. */
  legacyHref: string
  perm?: string | string[]
  /** Director / School Administrator only (matches legacy sidebar). */
  adminOnly?: boolean
}

export function navItemLabel(item: NavItem, user: SessionUser): string {
  if (user.role_canonical === 'School Administrator' && item.adminStaffLabel) {
    return item.adminStaffLabel
  }
  return item.label
}

/** Prefer the React route when a page is migrated; otherwise open legacy in full page. */
export function navItemHref(item: NavItem): string {
  if (item.reactTo) {
    return `/app${item.reactTo}`
  }
  return item.legacyHref
}

export function hasManagementNavAccess(user: SessionUser, item: NavItem): boolean {
  if (item.id === 'billing') {
    if (user.role_canonical === 'Director') return true
    return user.permissions.includes('billing:manage')
  }
  if (item.adminOnly && !user.management_entry) {
    return false
  }
  if (user.management_entry) {
    return true
  }
  if (!item.perm) {
    return true
  }
  const required = Array.isArray(item.perm) ? item.perm : [item.perm]
  return required.some((p) => user.permissions.includes(p))
}

export function isTeacherShellUser(user: SessionUser): boolean {
  if (isTechShellUser(user)) return false
  if (isManagementShellUser(user)) return false
  return Boolean(user.teacher_entry)
}

export function isStudentShellUser(user: SessionUser): boolean {
  if (isTechShellUser(user)) return false
  if (isManagementShellUser(user)) return false
  return Boolean(user.student_entry && !user.teacher_entry)
}

export function isParentShellUser(user: SessionUser): boolean {
  if (isTechShellUser(user)) return false
  if (isManagementShellUser(user)) return false
  return Boolean(user.parent_entry && !user.teacher_entry && !user.student_entry)
}

export function isTechShellUser(user: SessionUser): boolean {
  if (!user.tech_entry) return false
  if (user.staff_dashboard_target === 'tech') return true
  if (user.management_entry || user.management_shell) return false
  return true
}

export function isManagementShellUser(user: SessionUser): boolean {
  if (isTechShellUser(user)) return false
  return Boolean(user.management_entry || user.management_shell)
}

export function spaHomePath(user: SessionUser): string {
  if (isTechShellUser(user)) return '/tech'
  if (isParentShellUser(user)) return '/parent'
  if (isStudentShellUser(user)) return '/student'
  if (isTeacherShellUser(user)) return '/teacher'
  return '/management'
}
