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
  sidebar_title: string
  csrf_token: string
}

export interface SessionResponse {
  authenticated: boolean
  user?: SessionUser
  school_timezone?: SchoolTimezone
  login_url?: string
}
