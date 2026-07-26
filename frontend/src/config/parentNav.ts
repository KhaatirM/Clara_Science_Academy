import type { NavItem } from './navTypes'

/** Mirrors templates/shared/dashboard_layout.html parent / Family Portal tabs. */
export const PARENT_NAV: NavItem[] = [
  {
    id: 'home',
    label: 'Home',
    icon: 'bi-house-door-fill',
    reactTo: '/parent',
    legacyHref: '/parent/dashboard',
  },
  {
    id: 'grades',
    label: 'Grades',
    icon: 'bi-card-checklist',
    reactTo: '/parent/grades',
    legacyHref: '/parent/dashboard',
  },
  {
    id: 'attendance',
    label: 'Attendance',
    icon: 'bi-clipboard-check-fill',
    reactTo: '/parent/attendance',
    legacyHref: '/parent/dashboard',
  },
  {
    id: 'classes',
    label: 'Classes',
    icon: 'bi-journal-bookmark-fill',
    reactTo: '/parent/classes',
    legacyHref: '/parent/dashboard',
  },
  {
    id: 'report-cards',
    label: 'Report Cards',
    icon: 'bi-file-earmark-pdf-fill',
    reactTo: '/parent/report-cards',
    legacyHref: '/parent/dashboard',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: 'bi-gear-fill',
    reactTo: '/parent/settings',
    legacyHref: '/parent/settings',
  },
]
