export interface DashboardProfile {
  display_name: string
  role: string
  email: string | null
  staff_id: string
}

export interface DashboardStats {
  students: number
  teachers: number
  classes: number
  assignments: number
  active_assignments: number
}

export interface DashboardMonthlyStats {
  new_students: number
  attendance_rate: number
  average_grade: number
}

export interface DashboardWeeklyStats {
  due_assignments: number
}

export interface DashboardFeedItem {
  type: string
  title: string
  message?: string
  description?: string
  timestamp: string | null
  link: string | null
}

export interface DashboardHomeResponse {
  home_display_date: string
  has_active_school_year: boolean
  latest_school_year_label: string | null
  dual_dashboard_staff: boolean
  profile: DashboardProfile
  at_risk_count: number
  stats: DashboardStats
  monthly_stats: DashboardMonthlyStats
  weekly_stats: DashboardWeeklyStats
  pending_extension_count: number
  notifications: DashboardFeedItem[]
  recent_activity: DashboardFeedItem[]
}
