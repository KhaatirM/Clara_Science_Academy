import type { SessionUser } from '../types/session'
import { MANAGEMENT_NAV } from './managementNav'
import {
  hasManagementNavAccess,
  isStudentShellUser,
  isTeacherShellUser,
  type NavItem,
} from './navTypes'
import { STUDENT_NAV } from './studentNav'
import { TEACHER_NAV } from './teacherNav'

export function getSidebarNav(user: SessionUser): NavItem[] {
  if (isStudentShellUser(user)) {
    return STUDENT_NAV
  }
  if (isTeacherShellUser(user)) {
    return TEACHER_NAV
  }
  return MANAGEMENT_NAV.filter((item) => hasManagementNavAccess(user, item))
}
