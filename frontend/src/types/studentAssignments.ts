export type StudentAssignmentBucket = 'upcoming' | 'active' | 'inactive'

export interface StudentAssignmentGradeInfo {
  has_grade: boolean
  percentage: number | null
  letter: string | null
  feedback: string | null
  feedback_preview: string | null
  display: string | null
}

export interface StudentAssignmentAction {
  label: string
  url: string | null
  kind: string
  disabled: boolean
}

export interface StudentAssignmentCard {
  id: number
  is_group: boolean
  title: string
  description: string
  description_preview: string
  assignment_type: string
  type_label: string
  bucket?: StudentAssignmentBucket
  class_id: number
  class_name: string
  teacher_name: string
  due_date: string | null
  due_display: string
  open_date: string | null
  open_display: string | null
  quarter: string | number | null
  total_points: number | null
  student_status: string
  attempts_remaining: number | null
  has_submission: boolean
  group_name: string | null
  group_leader: string | null
  grade: StudentAssignmentGradeInfo
  attachment_name: string | null
  download_url: string | null
  extension: { status: string; id: number } | null
  redo: { status: string; id: number } | null
  can_request_extension?: boolean
  can_request_redo?: boolean
  primary_action: StudentAssignmentAction | null
  legacy_url: string
}

export interface StudentAssignmentsFilters {
  class_id: number | null
  status: string
  start_date: string
  end_date: string
}

export interface StudentLowGradeItem {
  assignment_id: number
  title: string
  class_name: string
  class_id: number | null
  percentage: number
  letter: string
  points_earned?: number
  total_points?: number
  feedback: string
  assignment_type: string
  is_group: boolean
  graded_at: string | null
  graded_display: string | null
  legacy_url: string
}

export interface StudentAssignmentsResponse {
  has_active_school_year: boolean
  school_year_name?: string
  filters: StudentAssignmentsFilters
  classes: Array<{ id: number; name: string }>
  upcoming: StudentAssignmentCard[]
  active: StudentAssignmentCard[]
  inactive: StudentAssignmentCard[]
  counts: { upcoming: number; active: number; inactive: number }
  low_grades: {
    threshold: number
    items: StudentLowGradeItem[]
    classes: string[]
    summary: { avg_percentage?: number | null }
  }
  links: { legacy: string }
}
