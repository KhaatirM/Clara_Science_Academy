import { apiFetch } from './client'
import type {
  ClassAnalyticsResponse,
  ClassAssessmentToolResponse,
} from '../types/classTools'

export type { ClassDeadlineRemindersResponse } from '../types/classTools'
export {
  createDeadlineReminder,
  deleteDeadlineReminder,
  fetchClassDeadlineReminders,
  fetchDeadlineReminderCreateForm,
  fetchDeadlineReminderEditForm,
  fetchStudentsNeedingReminder,
  sendDeadlineReminderNow,
  toggleDeadlineReminder,
  updateDeadlineReminder,
} from './deadlineReminders'

export type AssessmentToolSlug = '360-feedback' | 'reflection-journals' | 'conflicts'
export type ClassToolsScope = 'management' | 'teacher'

function toolsBase(classId: number, scope: ClassToolsScope) {
  return scope === 'teacher'
    ? `/api/spa/teacher/classes/${classId}`
    : `/api/spa/classes/${classId}`
}

export async function fetchClassAnalytics(classId: number, scope: ClassToolsScope = 'management') {
  return apiFetch<ClassAnalyticsResponse>(`${toolsBase(classId, scope)}/tools/analytics`)
}

export async function fetchClassAssessmentTool(
  classId: number,
  tool: AssessmentToolSlug,
  scope: ClassToolsScope = 'management',
) {
  return apiFetch<ClassAssessmentToolResponse>(`${toolsBase(classId, scope)}/tools/${tool}`)
}
