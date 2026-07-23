import { apiFetch } from './client'
import type { ClassBrief } from './assignmentCreateForms'
import type { AssignmentCreateScope } from '../utils/assignmentCreateScope'
import { assignmentCreateApiBase } from '../utils/assignmentCreateScope'

export interface GroupClassPickerMeta {
  classes: ClassBrief[]
  back_url: string
  type_selector_url: string
  meta?: { can_manage?: boolean; scope?: string }
}

export interface GroupTypeSelectorMeta {
  class: ClassBrief
  back_url: string
  class_picker_url: string
  type_selector_url: string
  links: {
    pdf: string
    quiz: string
    discussion: string
  }
  meta?: { can_manage?: boolean; scope?: string }
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
  meta?: { can_manage?: boolean; scope?: string }
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
  meta?: { can_manage?: boolean; scope?: string }
}

export interface GroupDiscussionFormMeta {
  class: ClassBrief
  current_quarter: string
  academic_periods: AcademicPeriodBrief[]
  groups_api_url: string
  post_url: string
  back_url: string
  type_selector_url: string
  assignments_url: string
  defaults: {
    min_posts: number
    min_words: number
    max_posts: number
    group_size_min: number
  }
  meta?: { can_manage?: boolean; scope?: string }
}

const groupApiBase = (scope: AssignmentCreateScope) => `${assignmentCreateApiBase(scope)}/group`

export async function fetchGroupDiscussionForm(
  classId: number,
  scope: AssignmentCreateScope = 'management',
) {
  return apiFetch<GroupDiscussionFormMeta>(`${groupApiBase(scope)}/${classId}/discussion`)
}

export async function fetchGroupClassPicker(scope: AssignmentCreateScope = 'management') {
  return apiFetch<GroupClassPickerMeta>(groupApiBase(scope))
}

export async function fetchGroupTypeSelector(
  classId: number,
  scope: AssignmentCreateScope = 'management',
) {
  return apiFetch<GroupTypeSelectorMeta>(`${groupApiBase(scope)}/${classId}`)
}

export async function fetchGroupPdfForm(classId: number, scope: AssignmentCreateScope = 'management') {
  return apiFetch<GroupPdfFormMeta>(`${groupApiBase(scope)}/${classId}/pdf`)
}

export async function fetchGroupQuizForm(classId: number, scope: AssignmentCreateScope = 'management') {
  return apiFetch<GroupQuizFormMeta>(`${groupApiBase(scope)}/${classId}/quiz`)
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
