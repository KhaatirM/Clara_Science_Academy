export interface TeacherTabStat {
  label: string
  value: string | number
  icon: string
  tone?: 'classes' | 'students' | 'assignments' | 'notifications'
}

export interface TeacherStudentItem {
  id: number
  first_name: string
  last_name: string
  full_name: string
  grade_level: number | null
  grade_label: string
  email: string | null
  student_id: string | null
  state_id: string | null
  address: string | null
  date_of_birth: string | null
  date_of_birth_display: string | null
  class_names: string[]
  photo_url: string
  links: {
    grades: string
    attendance: string
  }
}

export interface TeacherStudentsResponse {
  items: TeacherStudentItem[]
  stats: {
    total_students: number
    grade_levels: number
    with_email: number
    with_id: number
    total_classes: number
  }
  meta: {
    active_school_year_id: number | null
    active_school_year_name: string | null
    has_active_school_year: boolean
  }
}

import type { ClassListItem, SchoolYearOption } from './classes'

export interface TeacherAssignmentsClassItem extends ClassListItem {
  links: {
    open: string
    create_assignment: string
  }
}

export interface TeacherAssignmentsHubResponse {
  items: TeacherAssignmentsClassItem[]
  school_years: SchoolYearOption[]
  meta: {
    default_school_year_id: number | null
    active_school_year_id: number | null
    active_school_year_name: string | null
    has_active_school_year: boolean
    can_select_school_year: boolean
  }
  hub: {
    extension_request_count: number
    redo_request_count: number
  }
  stats: {
    total_classes: number
    total_assignments: number
    total_students: number
    extension_requests: number
    redo_requests: number
  }
}

export interface TeacherAttendanceClassItem {
  id: number
  name: string
  subject: string
  grade_levels_display: string
  enrollment_count: number
  attendance_taken_today: boolean
  links: {
    take: string
    records: string
  }
}

export interface TeacherAttendanceResponse {
  items: TeacherAttendanceClassItem[]
  stats: {
    total_classes: number
    completed_today: number
    pending_today: number
  }
  today_display: string
}

export interface TeacherScheduleBlock {
  class_id: number
  class_name: string
  subject: string
  time_str: string
  room: string
  student_count?: number
  is_now: boolean
  is_upcoming: boolean
  links: {
    view_class: string
  }
}

export interface TeacherScheduleDay {
  day_index: number
  day_name: string
  is_today: boolean
  blocks: TeacherScheduleBlock[]
}

export interface TeacherScheduleResponse {
  days: TeacherScheduleDay[]
  grid_rows: Array<{
    time_label: string
    cells: TeacherScheduleBlock[][]
  }>
  today_weekday: number
  today_display: string
  stats: {
    today_blocks: number
    total_blocks: number
    active_days: number
    unique_classes: number
  }
}

export interface TeacherCalendarEvent {
  title: string
  category?: string
  type: string
  description?: string
}

export interface TeacherCalendarDay {
  day_num: number | null
  is_current_month: boolean
  is_today: boolean
  events: TeacherCalendarEvent[]
}

export interface TeacherCalendarResponse {
  month: number
  year: number
  month_name: string
  weekdays: string[]
  weeks: TeacherCalendarDay[][]
  prev_month: { month: number; year: number }
  next_month: { month: number; year: number }
  events_this_month: number
  active_school_year: { id: number; name: string } | null
  read_only: boolean
}

export interface TeacherSettingsResponse {
  role_canonical: string
  is_director: boolean
  account: {
    username: string
    email: string | null
    role: string | null
  }
  preferences: {
    theme: string
    saved_theme: string
    theme_locked: boolean
    site_theme_override: string | null
    theme_options: Array<{ value: string; label: string; group: string }>
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
