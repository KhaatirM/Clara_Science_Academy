import type { SessionUser } from '../types/session'
import { MANAGEMENT_NAV } from './managementNav'
import {
  hasManagementNavAccess,
  isParentShellUser,
  isStudentShellUser,
  isTeacherShellUser,
  isTechShellUser,
  type NavItem,
} from './navTypes'
import { PARENT_NAV } from './parentNav'
import { STUDENT_NAV } from './studentNav'
import { TEACHER_NAV } from './teacherNav'
import { TECH_NAV } from './techNav'

export function getSidebarNav(user: SessionUser): NavItem[] {
  if (isTechShellUser(user)) {
    return TECH_NAV
  }
  if (isParentShellUser(user)) {
    return PARENT_NAV
  }
  if (isStudentShellUser(user)) {
    return STUDENT_NAV
  }
  if (isTeacherShellUser(user)) {
    return TEACHER_NAV
  }
  return MANAGEMENT_NAV.filter((item) => hasManagementNavAccess(user, item))
}
