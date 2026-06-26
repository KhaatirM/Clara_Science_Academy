import type { CredentialModalPayload } from './staff'

export type StudentTone = 'success' | 'warning' | 'danger' | 'primary' | 'muted'
export type GpaAlertLevel = 'none' | 'critical' | 'warning' | 'excellent'

export interface StudentSaveResponse {
  success: boolean
  message?: string
  redirect?: string
  credential_modal?: CredentialModalPayload
}
export interface StudentListItem {
  id: number
  first_name: string
  last_name: string
  display_name: string
  initials: string
  grade_level: number | null
  grade_display: string
  student_id: string | null
  gpa: number | null
  alert_level: GpaAlertLevel
  academic_status: string
  academic_tone: StudentTone
  is_deleted: boolean
  has_account: boolean
  username: string | null
  account_status: string
  account_badge_kind: 'removed' | 'has_young' | 'has_active' | 'no_young' | 'no_active'
  dob?: string | null
}

export interface StudentFilters {
  search: string
  search_type: string
  grade_level: string
  status: string
  alert_filter: string
  sort: string
  order: string
  page: number
}

export interface StudentListResponse {
  items: StudentListItem[]
  stats: {
    total: number
    with_accounts: number
    without_accounts: number
    on_page: number
    high_gpa: number
  }
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
  filters: StudentFilters
  meta: {
    can_admin_ui: boolean
  }
}

export interface StudentAssignedClass {
  name: string
  subject?: string | null
}

export interface StudentClassesSchoolYear {
  id: number
  name: string
  is_active: boolean
}

export interface StudentParentPortalStatus {
  parent1?: {
    has_email?: boolean
    has_login?: boolean
    is_linked?: boolean
    username?: string | null
    email?: string | null
    name?: string
  } | null
  parent2?: {
    has_email?: boolean
    has_login?: boolean
    is_linked?: boolean
    username?: string | null
    email?: string | null
    name?: string
  } | null
}

export interface StudentDetail extends Record<string, unknown> {
  id: number
  first_name: string
  middle_name: string | null
  last_name: string
  dob: string | null
  age: number | null
  grade_level: number | null
  student_id: string | null
  gender: string | null
  entrance_date: string | null
  expected_grad_date: string | null
  email: string | null
  google_workspace_email: string | null
  suggested_google_workspace_email: string | null
  gpa: number
  assigned_classes: StudentAssignedClass[]
  assigned_classes_school_year: StudentClassesSchoolYear | null
  photo_filename: string | null
  parent1_first_name: string | null
  parent1_last_name: string | null
  parent1_email: string | null
  parent1_phone: string | null
  parent1_relationship: string | null
  parent2_first_name: string | null
  parent2_last_name: string | null
  parent2_email: string | null
  parent2_phone: string | null
  parent2_relationship: string | null
  emergency_first_name: string | null
  emergency_last_name: string | null
  emergency_email: string | null
  emergency_phone: string | null
  emergency_relationship: string | null
  street: string | null
  apt_unit: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  previous_school?: string | null
  medical_concerns?: string | null
  notes?: string | null
  parent_portal?: StudentParentPortalStatus | null
}
