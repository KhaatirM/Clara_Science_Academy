import { apiFetch } from './client'
import type {
  ClassDeadlineRemindersResponse,
  DeadlineReminderFormMeta,
  StudentNeedingReminder,
} from '../types/classTools'

export type DeadlineScope = 'management' | 'teacher'

function classApiBase(classId: number, scope: DeadlineScope) {
  return scope === 'teacher'
    ? `/api/spa/teacher/classes/${classId}`
    : `/api/spa/classes/${classId}`
}

export async function fetchClassDeadlineReminders(
  classId: number,
  scope: DeadlineScope = 'management',
) {
  return apiFetch<ClassDeadlineRemindersResponse>(
    `${classApiBase(classId, scope)}/tools/deadline-reminders`,
  )
}

export async function fetchDeadlineReminderCreateForm(
  classId: number,
  scope: DeadlineScope = 'management',
) {
  return apiFetch<DeadlineReminderFormMeta>(
    `${classApiBase(classId, scope)}/deadline-reminders/form`,
  )
}

export async function fetchDeadlineReminderEditForm(
  classId: number,
  reminderId: number,
  scope: DeadlineScope = 'management',
) {
  return apiFetch<DeadlineReminderFormMeta>(
    `${classApiBase(classId, scope)}/deadline-reminders/${reminderId}/form`,
  )
}

export async function createDeadlineReminder(
  classId: number,
  body: Record<string, unknown>,
  scope: DeadlineScope = 'management',
) {
  return apiFetch<{ success: boolean; message: string; id?: number }>(
    `${classApiBase(classId, scope)}/deadline-reminders`,
    { method: 'POST', body: JSON.stringify(body) },
  )
}

export async function updateDeadlineReminder(
  classId: number,
  reminderId: number,
  body: Record<string, unknown>,
  scope: DeadlineScope = 'management',
) {
  return apiFetch<{ success: boolean; message: string }>(
    `${classApiBase(classId, scope)}/deadline-reminders/${reminderId}`,
    { method: 'PUT', body: JSON.stringify(body) },
  )
}

export async function toggleDeadlineReminder(
  classId: number,
  reminderId: number,
  scope: DeadlineScope = 'management',
) {
  return apiFetch<{ success: boolean; message: string; is_active?: boolean }>(
    `${classApiBase(classId, scope)}/deadline-reminders/${reminderId}/toggle`,
    { method: 'POST', body: '{}' },
  )
}

export async function sendDeadlineReminderNow(
  classId: number,
  reminderId: number,
  scope: DeadlineScope = 'management',
) {
  return apiFetch<{ success: boolean; message: string; sent_count?: number }>(
    `${classApiBase(classId, scope)}/deadline-reminders/${reminderId}/send-now`,
    { method: 'POST', body: '{}' },
  )
}

export async function deleteDeadlineReminder(
  classId: number,
  reminderId: number,
  scope: DeadlineScope = 'management',
) {
  return apiFetch<{ success: boolean; message: string }>(
    `${classApiBase(classId, scope)}/deadline-reminders/${reminderId}`,
    { method: 'DELETE' },
  )
}

export async function fetchStudentsNeedingReminder(assignmentId: number) {
  return apiFetch<{ success: boolean; students: StudentNeedingReminder[] }>(
    `/api/spa/assignments/${assignmentId}/students-needing-reminder`,
  )
}
