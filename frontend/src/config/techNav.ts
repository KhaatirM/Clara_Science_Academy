import type { NavItem } from './navTypes'

/** Mirrors templates/shared/dashboard_layout.html Tech / IT Support tabs. */
export const TECH_NAV: NavItem[] = [
  {
    id: 'home',
    label: 'Home',
    icon: 'bi-grid-1x2-fill',
    reactTo: '/tech',
    legacyHref: '/tech/dashboard',
  },
  {
    id: 'devices',
    label: 'Devices',
    icon: 'bi-laptop',
    reactTo: '/tech/devices',
    legacyHref: '/tech/devices',
  },
  {
    id: 'logs',
    label: 'Logs',
    icon: 'bi-list-check',
    reactTo: '/tech/logs',
    legacyHref: '/tech/activity-log',
  },
  {
    id: 'bugs',
    label: 'Bugs',
    icon: 'bi-bug-fill',
    reactTo: '/tech/bugs',
    legacyHref: '/tech/error/reports',
  },
  {
    id: 'system',
    label: 'System',
    icon: 'bi-hdd-stack-fill',
    reactTo: '/tech/system',
    legacyHref: '/tech/system',
  },
  {
    id: 'users',
    label: 'User Management',
    icon: 'bi-people-fill',
    reactTo: '/tech/users',
    legacyHref: '/tech/user/management',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: 'bi-gear-fill',
    reactTo: '/tech/settings',
    legacyHref: '/tech/settings',
  },
]
