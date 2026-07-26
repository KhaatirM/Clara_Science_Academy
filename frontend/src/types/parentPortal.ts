export type ParentChildBrief = {
  id: number
  first_name: string
  last_name: string
  display_name: string
  student_id: string | null
  grade_level: number | null
  initial: string
}

export type ParentSchoolYearBrief = {
  id: number
  name: string
} | null

export type ParentBootstrap = {
  parent_display_name: string
  children: ParentChildBrief[]
  active_child_id: number | null
  active_child: ParentChildBrief | null
  school_year: ParentSchoolYearBrief
  has_active_school_year: boolean
  links: {
    home: string
    grades: string
    attendance: string
    classes: string
    report_cards: string
    settings: string
  }
}

export type ParentClassRow = {
  id: number
  name: string
  subject: string
  teacher_name: string
  room: string | null
  schedule: string | null
  average: number | null
}

export type ParentRecentGrade = {
  assignment_title: string
  class_name: string
  percentage: number | null
  graded_at: string | null
  graded_at_display: string | null
}

export type ParentAcademicSummary = {
  student: ParentChildBrief | null
  school_year: ParentSchoolYearBrief
  gpa: number
  attendance_summary: { Present: number; Tardy: number; Absent: number }
  attendance_rate: number | null
  classes: ParentClassRow[]
  recent_grades: ParentRecentGrade[]
}

export type ParentHomeResponse = ParentBootstrap & {
  summary: ParentAcademicSummary | null
  report_card_count: number
}

export type ParentTabResponse = ParentBootstrap & {
  summary?: ParentAcademicSummary | null
  report_cards?: ParentReportCardItem[]
}

export type ParentReportCardItem = {
  id: number
  quarter: string | number | null
  school_year_id: number | null
  generated_at: string | null
  generated_at_display: string | null
  approved_at: string | null
  download_url: string
}

export type ParentSettingsResponse = {
  account: {
    username: string
    email: string | null
    display_name: string
    role: string
  }
  preferences: {
    saved_theme: string
    theme: string
    theme_locked: boolean
    theme_options: Array<{ value: string; label: string; group: string }>
  }
  children: ParentChildBrief[]
}
