import type { SessionUser } from '../types/session'
import { canStudentAdminUi } from '../utils/studentAccess'

export type HomeActionGroup = 'people' | 'academics' | 'operations'

export interface HomeQuickAction {
  id: string
  group: HomeActionGroup
  icon: string
  label: string
  reactTo?: string
  legacyHref: string
  /** When set, user must have one of these permissions (directors/admins always pass). */
  perm?: string | string[]
  /** Extra gate beyond perm, e.g. add-student needs edit access. */
  visible?: (user: SessionUser) => boolean
}

export const HOME_QUICK_ACTIONS: HomeQuickAction[] = [
  {
    id: 'add-student',
    group: 'people',
    icon: 'bi-person-plus-fill',
    label: 'Add student',
    reactTo: '/management/students/new',
    legacyHref: '/management/add-student',
    perm: ['students:view', 'students:edit'],
    visible: canStudentAdminUi,
  },
  {
    id: 'add-staff',
    group: 'people',
    icon: 'bi-person-badge',
    label: 'Add staff',
    reactTo: '/management/teachers/new',
    legacyHref: '/management/add-teacher-staff',
    perm: 'teachers_staff:manage',
  },
  {
    id: 'students',
    group: 'people',
    icon: 'bi-people',
    label: 'Students',
    reactTo: '/management/students',
    legacyHref: '/management/students',
    perm: ['students:view', 'students:edit'],
  },
  {
    id: 'parents',
    group: 'people',
    icon: 'bi-heart-fill',
    label: 'Family Portal',
    reactTo: '/management/parents',
    legacyHref: '/management/parents',
    perm: ['students:view', 'students:edit'],
  },
  {
    id: 'teachers',
    group: 'people',
    icon: 'bi-person-workspace',
    label: 'Teachers & staff',
    reactTo: '/management/teachers',
    legacyHref: '/management/teachers',
    perm: 'teachers_staff:manage',
  },
  {
    id: 'add-class',
    group: 'academics',
    icon: 'bi-plus-circle',
    label: 'Add class',
    reactTo: '/management/classes?open=create',
    legacyHref: '/management/classes?open=create',
    perm: 'classes:manage',
  },
  {
    id: 'classes',
    group: 'academics',
    icon: 'bi-mortarboard',
    label: 'Classes',
    reactTo: '/management/classes',
    legacyHref: '/management/classes',
    perm: 'classes:manage',
  },
  {
    id: 'add-assignment',
    group: 'academics',
    icon: 'bi-journal-plus',
    label: 'Add assignment',
    reactTo: '/management/assignments/create',
    legacyHref: '/management/assignment-type-selector',
    perm: 'assignments_grades:manage',
  },
  {
    id: 'assignments',
    group: 'academics',
    icon: 'bi-clipboard-data',
    label: 'Grades & assignments',
    reactTo: '/management/assignments',
    legacyHref: '/management/assignments-and-grades',
    perm: 'assignments_grades:manage',
  },
  {
    id: 'report-cards-generate',
    group: 'academics',
    icon: 'bi-file-earmark-text',
    label: 'Report cards',
    legacyHref: '/management/report/card/generate',
    reactTo: '/management/report-cards/generate',
    perm: ['report_cards:view', 'report_cards:generate'],
  },
  {
    id: 'report-cards-view',
    group: 'academics',
    icon: 'bi-collection',
    label: 'View report cards',
    reactTo: '/management/report-cards',
    legacyHref: '/management/report-cards',
    perm: ['report_cards:view', 'report_cards:generate'],
  },
  {
    id: 'attendance',
    group: 'operations',
    icon: 'bi-calendar-check',
    label: 'Attendance',
    reactTo: '/management/attendance',
    legacyHref: '/management/unified-attendance',
    perm: 'attendance:manage',
  },
  {
    id: 'extensions',
    group: 'operations',
    icon: 'bi-clock-history',
    label: 'Extensions',
    reactTo: '/management/extensions',
    legacyHref: '/management/extensions',
    perm: 'assignments_grades:manage',
  },
]

export function canSeeHomeAction(user: SessionUser, action: HomeQuickAction): boolean {
  if (action.visible && !action.visible(user)) return false
  if (user.management_entry) return true
  if (!action.perm) return true
  const required = Array.isArray(action.perm) ? action.perm : [action.perm]
  return required.some((p) => user.permissions.includes(p))
}

export function homeActionsForGroup(
  user: SessionUser,
  group: HomeActionGroup,
): HomeQuickAction[] {
  return HOME_QUICK_ACTIONS.filter((a) => a.group === group && canSeeHomeAction(user, a))
}
