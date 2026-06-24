export interface RedoClassOption {
  id: number
  name: string
}

export interface RedoStudentRef {
  id: number | null
  display_name: string
  grade_level?: number | null
}

export interface RedoAssignmentRef {
  id: number | null
  title: string
}

export interface RedoClassRef {
  id: number | null
  name: string
}

export interface RedoRequestItem {
  id: number
  assignment_id: number
  reason: string
  requested_at: string | null
  student: RedoStudentRef
  assignment: RedoAssignmentRef
  class: RedoClassRef
  search_text: string
}

export interface ReopeningItem {
  id: number
  reopened_at: string | null
  additional_attempts: number
  student: RedoStudentRef
  assignment: RedoAssignmentRef
  class: RedoClassRef
  status: string
  search_text: string
}

export interface ActiveRedoItem {
  id: number
  assignment_id: number
  reason: string
  original_grade: number | null
  redo_grade: number | null
  final_grade: number | null
  was_redo_late: boolean
  is_used: boolean
  is_overdue: boolean
  redo_deadline: string | null
  granted_at: string | null
  status: 'pending' | 'submitted' | 'graded' | 'overdue' | string
  student: RedoStudentRef
  assignment: RedoAssignmentRef
  class: RedoClassRef
  grade_url: string | null
  search_text: string
}

export interface RedoDashboardResponse {
  redo_requests: RedoRequestItem[]
  reopenings: ReopeningItem[]
  redos: ActiveRedoItem[]
  classes: RedoClassOption[]
  stats: {
    active_redos: number
    completed_redos: number
    active_reopenings: number
    improvement_rate: number
    overdue_redos: number
  }
  meta: {
    active_school_year_id: number | null
    active_school_year_name: string | null
    has_active_school_year: boolean
    teacher_not_found?: boolean
  }
}

export interface ApiActionResponse {
  success: boolean
  message: string
}
