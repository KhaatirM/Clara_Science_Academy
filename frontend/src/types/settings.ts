export type ThemeOption = {
  value: string
  label: string
  group: string
}

export type SettingsHubResponse = {
  role_canonical: string
  is_director: boolean
  account: {
    username: string
    email: string | null
    role: string | null
  }
  preferences: {
    theme: string
    theme_options: ThemeOption[]
    notifications_coming_soon: boolean
    timezone_coming_soon: boolean
  }
  google: {
    connected: boolean
    connect_url: string
    disconnect_url: string
  }
  urls: {
    home: string
    change_password: string
    bug_reports_tab: string
  }
}

export type BugReportItem = {
  id: number
  title: string
  description: string
  contact_email: string | null
  severity: string
  status: string
  page_url: string | null
  created_at: string | null
  reporter_username: string | null
}

export type BugReportsResponse = {
  can_manage: boolean
  summary: {
    total: number
    open: number
    in_progress: number
    resolved: number
  }
  reports: BugReportItem[]
}
