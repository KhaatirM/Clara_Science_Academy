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

/** Mirrors templates/shared/dashboard_layout.html management tabs. */
export const MANAGEMENT_NAV: NavItem[] = [
  {
    id: 'home',
    label: 'Home',
    icon: 'bi-grid-1x2-fill',
    reactTo: '/management',
    legacyHref: '/management/dashboard',
  },
  {
    id: 'students',
    label: 'Students',
    icon: 'bi-people-fill',
    reactTo: '/management/students',
    legacyHref: '/management/students',
    perm: ['students:view', 'students:edit'],
  },
  {
    id: 'parents',
    label: 'Family Portal',
    icon: 'bi-people-fill',
    reactTo: '/management/parents',
    legacyHref: '/management/parents',
    perm: ['students:view', 'students:edit'],
  },
  {
    id: 'teachers',
    label: 'Teachers & Staff',
    adminStaffLabel: 'Staff',
    icon: 'bi-person-badge-fill',
    reactTo: '/management/teachers',
    legacyHref: '/management/teachers',
    perm: 'teachers_staff:manage',
  },
  {
    id: 'classes',
    label: 'Classes',
    icon: 'bi-house-door-fill',
    reactTo: '/management/classes',
    legacyHref: '/management/classes',
    perm: 'classes:manage',
  },
  {
    id: 'assignments',
    label: 'Assignments & Grades',
    icon: 'bi-journal-check',
    reactTo: '/management/assignments',
    legacyHref: '/management/assignments-and-grades',
    perm: 'assignments_grades:manage',
  },
  {
    id: 'attendance',
    label: 'Attendance',
    icon: 'bi-calendar-check-fill',
    reactTo: '/management/attendance',
    legacyHref: '/management/unified-attendance',
    perm: 'attendance:manage',
  },
  {
    id: 'report-cards',
    label: 'Report Cards',
    icon: 'bi-mortarboard-fill',
    reactTo: '/management/report-cards',
    legacyHref: '/management/report-cards',
    perm: ['report_cards:view', 'report_cards:generate'],
  },
  {
    id: 'billing',
    label: 'Billing & Financials',
    icon: 'bi-currency-dollar',
    reactTo: '/management/billing',
    legacyHref: '/management/billing',
    perm: 'billing:manage',
  },
  {
    id: 'calendar',
    label: 'School Calendar',
    adminStaffLabel: 'Calendar',
    icon: 'bi-calendar-event-fill',
    reactTo: '/management/calendar',
    legacyHref: '/management/calendar',
  },
  {
    id: 'student-jobs',
    label: 'Student Jobs',
    icon: 'bi-briefcase-fill',
    reactTo: '/management/student-jobs',
    legacyHref: '/management/student-jobs',
    adminOnly: true,
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: 'bi-gear-fill',
    reactTo: '/management/settings',
    legacyHref: '/management/settings',
  },
]

export function navItemLabel(item: NavItem, user: SessionUser): string {
  if (user.role_canonical === 'School Administrator' && item.adminStaffLabel) {
    return item.adminStaffLabel
  }
  return item.label
}

export function hasNavAccess(user: SessionUser, item: NavItem): boolean {
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

/** Prefer the React route when a page is migrated; otherwise open legacy in full page. */
export function navItemHref(item: NavItem): string {
  if (item.reactTo) {
    return `/app${item.reactTo}`
  }
  return item.legacyHref
}
