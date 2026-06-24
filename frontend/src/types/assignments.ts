import type { ClassListItem, SchoolYearOption } from './classes'

export interface AssignmentsHubResponse {
  items: ClassListItem[]
  stats: {
    total_classes: number
    total_enrollments: number
    unique_teachers: number
    total_assignments: number
  }
  school_years: SchoolYearOption[]
  hub: {
    extension_request_count: number
    redo_request_count: number
    pending_assistant_by_class: Record<number, number>
    total_pending_assistant_proposals: number
  }
  meta: {
    default_school_year_id: number | null
    active_school_year_id: number | null
    has_active_school_year: boolean
    can_manage?: boolean
  }
}

export interface AssignmentItemStats {
  total_submissions: number
  graded_count: number
  average_score: number
  all_voided: boolean
  partially_voided: boolean
  voided_count: number
  needs_grading: boolean
}

export interface AssignmentWorkspaceItem {
  id: number
  key: string
  title: string
  type: 'individual' | 'group'
  assignment_type: string | null
  due_date: string | null
  quarter: string | null
  status: string | null
  total_points: number | null
  stats: AssignmentItemStats
  links: {
    view: string
    grade: string
    class: string
    class_spa_grades: string
  }
}

export interface AssignmentsClassResponse {
  class: ClassListItem & { schedule?: string | null }
  view_mode: string
  sort_by: string
  sort_order: string
  assignments: AssignmentWorkspaceItem[]
  stats: {
    total_assignments: number
    active_assignments: number
    students: number
    average_score: number | null
  }
  toolbar: {
    extension_request_count: number
    redo_request_count: number
    pending_assistant_count: number
    new_assignment_url: string
    redo_url: string
    extensions_url: string
    assistant_proposals_url: string
  }
  meta: { can_manage?: boolean }
}
