export interface ClassTeacherSummary {
  id: number | null
  display_name: string
}

export interface ClassListItem {
  id: number
  name: string
  subject: string
  grade_levels: number[]
  grade_levels_display: string
  teacher: ClassTeacherSummary
  school_year_id: number | null
  school_year_name: string | null
  is_active: boolean
  enrollment_count: number
  assignment_count: number
  room_number: string | null
  schedule: string | null
  google_classroom_id: string | null
  google_classroom_linked: boolean
  search_text: string
}

export interface SchoolYearOption {
  id: number
  name: string
  is_active: boolean
}

export interface ClassListStats {
  total_classes: number
  total_enrollments: number
  unique_teachers: number
  total_assignments: number
}

export interface ClassListResponse {
  items: ClassListItem[]
  stats: ClassListStats
  filters: {
    school_year_id: number | null
  }
  school_years: SchoolYearOption[]
  meta: {
    default_school_year_id: number | null
    active_school_year_id: number | null
    has_active_school_year: boolean
    can_admin_ui: boolean
    can_create: boolean
  }
}
