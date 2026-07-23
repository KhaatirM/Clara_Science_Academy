export interface TeacherDashboardProfile {
  display_name: string
  role: string
  email: string | null
  phone: string | null
  initials: string
  class_count: number
}

export interface TeacherDashboardStats {
  classes: number
  students: number
  active_assignments: number
  total_assignments: number
  notifications: number
}

export interface TeacherDashboardFeedItem {
  type: string
  title: string
  message?: string
  description?: string
  timestamp: string | null
  link: string | null
  is_read?: boolean
}

export interface TeacherDashboardHomeResponse {
  home_display_date: string
  has_active_school_year: boolean
  latest_school_year_label: string | null
  is_admin: boolean
  profile: TeacherDashboardProfile
  stats: TeacherDashboardStats
  monthly_stats: { grades_entered: number }
  weekly_stats: { due_assignments: number }
  notifications: TeacherDashboardFeedItem[]
  recent_activity: TeacherDashboardFeedItem[]
}
