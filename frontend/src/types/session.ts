export interface SchoolTimezone {
  iana: string
  clock: string
  zone: string
}

export interface SessionUser {
  id: number
  username: string
  role: string
  role_canonical: string
  email: string | null
  permissions: string[]
  management_entry: boolean
  /** True for directors/admins and permission-only Administration staff SPA access. */
  management_shell?: boolean
  teacher_entry: boolean
  student_entry: boolean
  parent_entry: boolean
  tech_entry: boolean
  staff_dashboard_target: 'tech' | 'management' | null
  student_id: number | null
  sidebar_title: string
  csrf_token: string
  theme: string
}

export interface AppVersionInfo {
  version: string
  display: string
  origin: string
  updates_estimate: number
  release_label: string
  product_name: string
}

export interface SessionResponse {
  authenticated: boolean
  user?: SessionUser
  school_timezone?: SchoolTimezone
  login_url?: string
  app_version?: AppVersionInfo
  /** Flask flash messages consumed once on SPA bootstrap (corner toasts). */
  flashes?: Array<{ category: string; message: string }>
}
