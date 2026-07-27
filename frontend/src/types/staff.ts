export interface StaffRoleBadge {
  label: string
  class: string
}

export interface StaffListItem {
  id: number
  first_name: string
  middle_initial: string | null
  last_name: string
  display_name: string
  staff_id: string | null
  email: string
  phone: string | null
  department: string | null
  employment_type: string | null
  employment_status: string
  status_display: string
  status_tone: 'success' | 'warning' | 'danger' | 'muted'
  marked_for_removal: boolean
  portal_login: boolean
  has_account: boolean
  username: string | null
  role_labels: string[]
  role_badges: StaffRoleBadge[]
  image_url: string | null
  hire_date: string | null
  assigned_role: string | null
}

export interface StaffListResponse {
  items: StaffListItem[]
  stats: {
    total: number
    with_accounts: number
    without_accounts: number
    full_time: number
  }
  filters: StaffFilters
}

export interface StaffFilters {
  search: string
  search_type: string
  department: string
  role: string
  employment: string
  sort: string
  order: string
}

export interface StaffRosterItem {
  id: number
  display_name: string
  staff_id: string | null
  email: string | null
  department: string | null
  has_account: boolean
  role_display: string | null
  assigned_role: string | null
  status_display: string
  status_tone: 'success' | 'warning' | 'danger' | 'muted'
  marked_for_removal: boolean
  is_deleted: boolean
  deleted_at: string | null
}

export type StaffRosterTab = 'current' | 'former'

export interface StaffRosterResponse {
  tab: StaffRosterTab
  q: string
  counts: { current: number; former: number }
  items: StaffRosterItem[]
}

export interface StaffDetail extends Record<string, unknown> {
  id: number
  first_name: string
  last_name: string
  middle_initial?: string | null
  staff_id?: string | null
  dob?: string | null
  staff_ssn?: string | null
  email?: string
  phone?: string | null
  role?: string
  primary_role?: string
  secondary_roles?: string[]
  permissions?: string[]
  staff_role_options?: string[]
  assigned_role?: string | null
  employment_type?: string | null
  employment_status?: string
  marked_for_removal?: boolean
  removal_note?: string | null
  portal_login?: boolean
  username?: string | null
  google_workspace_email?: string | null
  school_email?: string | null
  department?: string | null
  department_list?: string[]
  position?: string | null
  subject?: string | null
  hire_date?: string | null
  street?: string | null
  apt_unit?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  address?: string
  emergency_contact?: string
  emergency_first_name?: string | null
  emergency_last_name?: string | null
  emergency_email?: string | null
  emergency_phone?: string | null
  emergency_relationship?: string | null
  grades_taught_list?: string[]
  assigned_classes?: { id: number; name: string; subject?: string }[]
  total_students?: number
  is_temporary?: boolean
  access_expires_at?: string | null
  image?: string | null
}

export interface CredentialModalPayload {
  variant: string
  title: string
  subtitle?: string
  fields: { label: string; value: string; mono?: boolean }[]
  alerts?: { type: string; text: string }[]
  notes?: string[]
}

export interface StaffSaveResponse {
  success: boolean
  message: string
  redirect?: string
  credential_modal?: CredentialModalPayload
}
