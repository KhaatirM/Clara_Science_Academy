import type { NavItem } from './navTypes'

/** Mirrors templates/shared/dashboard_layout.html teacher tabs. */
export const TEACHER_NAV: NavItem[] = [
  {
    id: 'home',
    label: 'Home',
    icon: 'bi-grid-1x2-fill',
    reactTo: '/teacher',
    legacyHref: '/teacher/dashboard',
  },
  {
    id: 'classes',
    label: 'Classes',
    icon: 'bi-house-door-fill',
    reactTo: '/teacher/classes',
    legacyHref: '/teacher/classes',
  },
  {
    id: 'assignments',
    label: 'Assignments & Grades',
    icon: 'bi-journal-check',
    reactTo: '/teacher/assignments-and-grades',
    legacyHref: '/teacher/assignments-and-grades',
  },
  {
    id: 'students',
    label: 'Students',
    icon: 'bi-people-fill',
    reactTo: '/teacher/students',
    legacyHref: '/teacher/students',
  },
  {
    id: 'attendance',
    label: 'Attendance',
    icon: 'bi-calendar-check-fill',
    reactTo: '/teacher/attendance',
    legacyHref: '/teacher/attendance',
  },
  {
    id: 'schedule',
    label: 'Schedule',
    icon: 'bi-calendar-week-fill',
    reactTo: '/teacher/schedule',
    legacyHref: '/teacher/schedule',
  },
  {
    id: 'calendar',
    label: 'School Calendar',
    icon: 'bi-calendar-event-fill',
    reactTo: '/teacher/calendar',
    legacyHref: '/teacher/calendar',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: 'bi-gear-fill',
    reactTo: '/teacher/settings',
    legacyHref: '/teacher/settings',
  },
]
