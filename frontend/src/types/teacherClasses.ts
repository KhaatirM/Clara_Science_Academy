export interface TeacherClassFeatures {
  gradek_standards?: boolean
  grade1_standards: boolean
  grade2_standards?: boolean
  grade3_standards: boolean
  syllabus?: boolean
}

export interface TeacherClassLinks {
  view_class: string
  attendance: string
  assignment: string
  link_google: string
  create_google: string
  unlink_google: string
  gradek_standards?: string
  grade1_standards?: string
  grade2_standards?: string
  grade3_standards?: string
  open_google?: string
}

export interface TeacherClassItem {
  id: number
  name: string
  subject: string
  grade_levels: number[]
  grade_levels_display: string
  teacher_display: string
  enrollment_count: number
  assignment_count: number
  schedule: string | null
  google_classroom_id: string | null
  google_classroom_linked: boolean
  google_group_email: string | null
  show_google_integration: boolean
  features: TeacherClassFeatures
  links: TeacherClassLinks
}

export interface TeacherClassesStats {
  total_classes: number
  total_enrollments: number
  linked_classrooms: number
  total_assignments: number
}

export interface TeacherClassesResponse {
  items: TeacherClassItem[]
  stats: TeacherClassesStats
  meta?: {
    active_school_year_id: number | null
    active_school_year_name: string | null
    has_active_school_year: boolean
  }
}
