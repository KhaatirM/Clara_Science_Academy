export type PendingGradeAssignment = {
  id: number
  title: string
  class_id: number
  class_name: string
  is_group: boolean
  assignment_type: string | null
  pending_count: number
  due_date: string | null
  grade_url: string
}

export type PendingGradesResponse = {
  scope: 'management' | 'teacher' | string
  schoolwide: boolean
  has_active_school_year: boolean
  school_year: { id: number; name: string } | null
  total_pending: number
  assignment_count: number
  assignments: PendingGradeAssignment[]
}
