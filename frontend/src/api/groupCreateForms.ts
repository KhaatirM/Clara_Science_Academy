import { apiFetch } from './client'
import type { ClassBrief } from './assignmentCreateForms'

export interface GroupClassPickerMeta {
  classes: ClassBrief[]
  back_url: string
  type_selector_url: string
  meta?: { can_manage?: boolean }
}

export interface GroupTypeSelectorMeta {
  class: ClassBrief
  back_url: string
  class_picker_url: string
  type_selector_url: string
  links: {
    pdf: string
    quiz: string
    discussion: string | null
  }
  meta?: { can_manage?: boolean }
}

export interface GroupQuizFormMeta {
  class: ClassBrief
  current_quarter: string
  academic_periods: AcademicPeriodBrief[]
  groups_api_url: string
  post_url: string
  back_url: string
  type_selector_url: string
  assignments_url: string
  defaults: {
    allow_save_and_continue: boolean
    time_limit_minutes: number
    passing_score: number
    group_size_min: number
  }
  meta?: { can_manage?: boolean }
}

export interface AcademicPeriodBrief {
  id: number
  name: string
  period_type?: string | null
}

export interface ClassGroupBrief {
  id: number
  name: string
  description?: string | null
  member_count: number
}

export interface GroupPdfFormMeta {
  class: ClassBrief
  accessible_classes: ClassBrief[]
  current_quarter: string
  academic_periods: AcademicPeriodBrief[]
  groups_api_url: string
  post_url: string
  back_url: string
  type_selector_url: string
  assignments_url: string
  meta?: { can_manage?: boolean }
}

export async function fetchGroupClassPicker() {
  return apiFetch<GroupClassPickerMeta>('/api/spa/assignments/create/group')
}

export async function fetchGroupTypeSelector(classId: number) {
  return apiFetch<GroupTypeSelectorMeta>(`/api/spa/assignments/create/group/${classId}`)
}

export async function fetchGroupPdfForm(classId: number) {
  return apiFetch<GroupPdfFormMeta>(`/api/spa/assignments/create/group/${classId}/pdf`)
}

export async function fetchGroupQuizForm(classId: number) {
  return apiFetch<GroupQuizFormMeta>(`/api/spa/assignments/create/group/${classId}/quiz`)
}

export async function fetchClassGroups(apiUrl: string) {
  const response = await fetch(apiUrl, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    cache: 'no-store',
  })
  const data = (await response.json()) as { success?: boolean; groups?: ClassGroupBrief[] }
  if (!response.ok || !data.success) {
    throw new Error('Could not load class groups')
  }
  return data.groups || []
}
