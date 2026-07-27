export interface AcademicConcernAlert {
  student_name: string
  student_user_id: number
  current_gpa: number
  grade_level: number | null
  class_count: number
  classes_label: string
  enrolled_class_names: string[]
  failing_count: number
  overdue_count: number
  not_submitted_count: number
  missing_count: number
  issues_total: number
  alert_reason: string
}

export interface AcademicConcernsHubResponse {
  scope: 'management' | 'teacher'
  schoolwide: boolean
  has_active_school_year: boolean
  school_year: { id: number; name: string } | null
  alerts: AcademicConcernAlert[]
  failing_count: number
  overdue_count: number
  not_submitted_count: number
  count: number
  details_base: string
}

export interface AcademicConcernAssignmentItem {
  assignment_id?: number
  assignment_title?: string
  title?: string
  status?: string
  submission_status?: string
  due_date?: string | null
  due_display?: string | null
  score_display?: string | null
  percentage?: number | null
}

export interface AcademicConcernStudentDetailsResponse {
  success: boolean
  error?: string
  student?: {
    name: string
    student_id: number
    current_gpa: number
    hypothetical_gpa: number
    missing_assignments: Record<string, AcademicConcernAssignmentItem[]>
    class_gpa: Record<string, { current?: number | null; hypothetical?: number | null }>
    failing_count: number
    missing_count: number
  }
}
