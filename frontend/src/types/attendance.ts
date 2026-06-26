export type SchoolDayStatus = 'Present' | 'Unexcused Absence' | 'Late' | 'Excused Absence' | ''

export interface AttendanceInsights {
  total_students: number
  school_day_present: number
  classes_completed: number
  class_period_rate: number
}

export interface SchoolDayStats {
  total: number
  present: number
  absent: number
  late: number
  excused: number
}

export interface SchoolDayStudentRow {
  id: number
  name: string
  grade_display: string
  status: string
  notes: string
}

export interface ClassPeriodStats {
  classes_completed: number
  pending_classes: number
  overall_rate: number
}

export interface ClassPeriodItem {
  id: number
  name: string
  subject: string
  student_count: number
  teacher_name: string
  grade_levels_display: string
  attendance_taken: boolean
  today_present: number
  today_absent: number
  take_attendance_url: string
  view_class_url: string
}

export interface AttendanceHubMeta {
  has_active_school_year: boolean
  active_school_year_id: number | null
  active_school_year_name: string | null
  school_day_year_independent: boolean
}

export interface AttendanceHubResponse {
  school_date: string
  class_date: string
  status_options: SchoolDayStatus[]
  insights: AttendanceInsights
  school_day_stats: SchoolDayStats
  school_day_students: SchoolDayStudentRow[]
  class_period_stats: ClassPeriodStats
  classes: ClassPeriodItem[]
  meta: AttendanceHubMeta
  urls: {
    analytics: string
    reports: string
  }
}

export interface AttendanceReportsSummaryStats {
  total_records: number
  present: number
  late: number
  unexcused_absence: number
  excused_absence: number
  suspended: number
}

export interface AttendanceReportRecord {
  id: number
  date: string
  date_display: string
  student: { id: number; first_name: string; last_name: string; label: string } | null
  class: { id: number; name: string } | null
  status: string
  notes: string
  recorded_by: string | null
}

export interface AttendanceReportsResponse {
  filters: {
    start_date: string
    end_date: string
    student_ids: number[]
    class_ids: number[]
    status: string
  }
  summary_stats: AttendanceReportsSummaryStats
  records: AttendanceReportRecord[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
    has_prev: boolean
    has_next: boolean
    prev_page: number | null
    next_page: number | null
  }
  filter_options: {
    students: { id: number; label: string }[]
    classes: { id: number; name: string }[]
    statuses: string[]
  }
  presets: { label: string; start_date: string; end_date: string }[]
  default_range_days: number
}

export interface AttendanceAnalyticsResponse {
  filters: {
    start_date: string
    end_date: string
    risk: 'all' | 'high' | 'medium'
  }
  summary: {
    overall_rate: number
    total_records: number
    present_count: number
    students_tracked: number
    at_risk_high: number
    at_risk_medium: number
    days_analyzed: number
  }
  status_counts: {
    present: number
    late: number
    unexcused: number
    excused: number
    suspended: number
    other: number
  }
  daily_trend: {
    date: string
    date_label: string
    date_short: string
    total: number
    present: number
    rate: number | null
  }[]
  trend_max: number
  at_risk_students: {
    student: {
      id: number
      first_name: string
      last_name: string
      label: string
      grade_display: string
      view_url: string
    }
    attendance_rate: number
    risk_level: 'high' | 'medium'
    pattern: {
      total_days: number
      present: number
      absent: number
      late: number
      excused: number
      max_consecutive_absences: number
    }
  }[]
  presets: { label: string; start_date: string; end_date: string }[]
}

export interface AttendanceSaveResponse {
  success: boolean
  message: string
  created_count?: number
  updated_count?: number
}

export interface SchoolDayEntry {
  student_id: number
  status: string
  notes: string
}
