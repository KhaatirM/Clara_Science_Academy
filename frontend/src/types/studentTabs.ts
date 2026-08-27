import type { BellGridPayload } from './bellSchedule'

export interface StudentScheduleBlock {
  class_id: number
  class_name: string
  subject: string
  time_str: string
  room: string
  teacher_name: string
  is_now: boolean
  is_upcoming: boolean
  links: { view_class: string }
}

export interface StudentScheduleDay {
  day_index: number
  day_name: string
  is_today: boolean
  blocks: StudentScheduleBlock[]
}

export interface StudentScheduleResponse {
  days: StudentScheduleDay[]
  bell_grid?: BellGridPayload
  today_weekday: number
  today_display: string
  stats: {
    today_blocks: number
    total_blocks: number
    active_days: number
    unique_classes: number
  }
  links: { calendar: string; pdf?: string }
}

export interface StudentCalendarEvent {
  title: string
  category?: string
  type: string
  description?: string
}

export interface StudentCalendarDay {
  day_num: number | null
  is_current_month: boolean
  is_today: boolean
  events: StudentCalendarEvent[]
}

export interface StudentCalendarResponse {
  month: number
  year: number
  month_name: string
  weekdays: string[]
  weeks: StudentCalendarDay[][]
  prev_month: { month: number; year: number }
  next_month: { month: number; year: number }
  events_this_month: number
  active_school_year: { id: number; name: string } | null
  read_only: boolean
}

export interface StudentSettingsResponse {
  account: {
    username: string
    email: string | null
    role: string | null
    student: {
      id: number
      state_id: string | null
      first_name: string | null
      last_name: string | null
      full_name: string
      grade_level: number | null
    } | null
  }
  preferences: {
    theme: string
    saved_theme: string
    theme_locked: boolean
    site_theme_override: string | null
    theme_options: Array<{ value: string; label: string; group: string }>
    low_grade_threshold: number
    notifications_coming_soon: boolean
    language_coming_soon: boolean
  }
  academic: {
    school_year: { id: number; name: string } | null
    enrollment_count: number
    gpa: number
  }
  urls: {
    home: string
    change_password: string
    bug_reports_tab: string
  }
}
