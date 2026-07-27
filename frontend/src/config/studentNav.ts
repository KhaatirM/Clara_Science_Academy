import type { NavItem } from './navTypes'

/** Mirrors templates/shared/dashboard_layout.html student tabs. */
export const STUDENT_NAV: NavItem[] = [
  {
    id: 'home',
    label: 'Home',
    icon: 'bi-house-door-fill',
    reactTo: '/student',
    legacyHref: '/student/dashboard',
  },
  {
    id: 'assignments',
    label: 'Assignments',
    icon: 'bi-file-earmark-text-fill',
    reactTo: '/student/assignments',
    legacyHref: '/student/assignments',
  },
  {
    id: 'classes',
    label: 'Classes',
    icon: 'bi-journal-bookmark-fill',
    reactTo: '/student/classes',
    legacyHref: '/student/classes',
  },
  {
    id: 'grades',
    label: 'Grades',
    icon: 'bi-card-checklist',
    reactTo: '/student/grades',
    legacyHref: '/student/grades',
  },
  {
    id: 'collaborate',
    label: 'Collaborate',
    icon: 'bi-people-fill',
    reactTo: '/student/collaborate',
    legacyHref: '/student/submissions',
  },
  {
    id: 'schedule',
    label: 'Schedule',
    icon: 'bi-calendar-week-fill',
    reactTo: '/student/schedule',
    legacyHref: '/student/schedule',
  },
  {
    id: 'calendar',
    label: 'School Calendar',
    icon: 'bi-calendar-event-fill',
    reactTo: '/student/calendar',
    legacyHref: '/student/school-calendar',
  },
  {
    id: 'jobs',
    label: 'Student Jobs',
    icon: 'bi-briefcase-fill',
    reactTo: '/student/jobs',
    legacyHref: '/management/student-jobs',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: 'bi-gear-fill',
    reactTo: '/student/settings',
    legacyHref: '/student/settings',
  },
]
