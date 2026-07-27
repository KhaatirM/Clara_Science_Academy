export interface StudentDashboardProfile {
  id: number
  first_name: string
  last_name: string
  display_name: string
  state_id: string | null
  grade_level: number | null
  grade_display: string
  dob: string | null
  email: string | null
}

export interface StudentDashboardStats {
  gpa: number
  class_count: number
  upcoming_count: number
  grade_display: string
}

export interface StudentUpNextItem {
  assignment_id: number
  title: string
  class_id: number
  class_name: string
  days_offset: number
  urgency: 'overdue' | 'due_today' | 'due_soon' | string
  url: string
}

export interface StudentFailingClass {
  class_id: number
  class_name: string
  average: number
  url: string
}

export interface StudentAnnouncement {
  id: number
  title: string
  message: string
  preview: string
  is_important: boolean
  is_schoolwide: boolean
  audience_label: string
  class_id: number | null
  timestamp: string | null
  timestamp_display: string
  timestamp_full: string
}

export interface StudentGoalRow {
  class_id: number
  class_name: string
  current_grade: number
  goal_id: number | null
  target_grade: number | null
  progress_pct: number | null
}

export interface StudentAssignmentCard {
  id: number
  title: string
  class_id: number
  class_name: string
  due_date: string | null
  due_display: string
  url: string
}

export interface StudentNotification {
  id: number
  type?: string
  title: string
  message: string
  preview?: string
  is_long?: boolean
  timestamp: string | null
  timestamp_display: string
}

export interface StudentAssistantClass {
  id: number
  name: string
  url: string
}

export interface StudentDashboardHomeResponse {
  has_active_school_year: boolean
  latest_school_year_label: string | null
  school_year_name?: string
  home_display_date: string
  profile: StudentDashboardProfile
  stats: StudentDashboardStats
  attendance_summary: { Present: number; Tardy: number; Absent: number }
  today_schedule?: Array<{
    class_id: number
    class_name: string
    time: string
    room: string
    teacher: string
  }>
  failing_classes: StudentFailingClass[]
  up_next_items: StudentUpNextItem[]
  announcements: StudentAnnouncement[]
  goals: StudentGoalRow[]
  upcoming_assignments: StudentAssignmentCard[]
  past_due_assignments: StudentAssignmentCard[]
  notifications: StudentNotification[]
  assistant_classes: StudentAssistantClass[]
  links: {
    assignments: string
    classes: string
    grades: string
    assistant_console: string
  }
}
