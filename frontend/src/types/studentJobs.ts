export type StudentJobsMember = {
  id: number
  member_id: number
  name: string
  role: string
  assignment_description: string
  task_id: number | null
  task_name: string | null
  /** Whether this student already took a lunch turn during the current week. */
  served_lunch: boolean
  served_at: string | null
}

export type StudentJobsDuty = {
  id: number
  team_id: number
  name: string
  area: string
  description: string
  scoring_type: string
  scoring_label: string
  sort_order: number
  assigned: Array<{ member_id: number; student_id: number; name: string }>
}

export type StudentJobsInspectionType = {
  value: string
  label: string
  description: string
  starting_score: number
  pass_threshold: number
  deductions: StudentJobsDeductionOption[]
  bonuses: StudentJobsBonusOption[]
}

export type StudentJobsTeamStats = {
  inspection_count: number
  average_score: number | null
  best_score: number | null
  pass_rate: number | null
  trend: number | null
  last_inspected: string | null
  sparkline: number[]
}

export type StudentJobsTeam = {
  id: number
  name: string
  description: string
  team_type: string
  /** Weekday numbers the team works, Mon=0. Empty means every school day. */
  days_of_week: number[]
  day_labels: string[]
  lunch_served_count: number
  current_score: number
  stats: StudentJobsTeamStats
  members: StudentJobsMember[]
  duties: StudentJobsDuty[]
  detailed_description: Record<string, unknown>
  recent_inspections: Array<{
    id: number
    date: string
    score: number
    status: string
    inspector_name: string
  }>
}

export type StudentJobsInspectionHistoryItem = {
  id: number
  date: string
  inspection_type?: string
  inspection_type_label?: string
  team_id: number
  team_name: string
  score: number
  major_deductions: number
  moderate_deductions?: number
  minor_deductions?: number
  bonus_points: number
  status: string
  inspector_name: string
  inspector_notes?: string
}

export type StudentJobsInspectionDetail = StudentJobsInspectionHistoryItem & {
  inspection_type?: string
  starting_score?: number
  is_archived?: boolean
  created_at?: string | null
  deductions?: string[]
  bonuses?: string[]
}

export type StudentJobsInspectionPagination = {
  page: number
  per_page: number
  total: number
  total_pages: number
}

export type StudentJobsInspectionHistoryResponse = {
  items: StudentJobsInspectionHistoryItem[]
  pagination: StudentJobsInspectionPagination
  passed_on_page: number
}

export type CreateStudentJobsTeamPayload = {
  name: string
  description?: string
  team_type: string
  student_ids?: number[]
  days_of_week?: number[]
}

export type UpdateStudentJobsTeamPayload = {
  name?: string
  description?: string
  team_type?: string
  days_of_week?: number[]
}

export type StudentJobsHubResponse = {
  role_canonical: string
  is_director: boolean
  summary: {
    teams: number
    members: number
    inspections: number
    passed: number
  }
  teams: StudentJobsTeam[]
  /** Monday of the week the lunch checks apply to. */
  lunch_week_start: string
  inspection_history: StudentJobsInspectionHistoryItem[]
  inspection_pagination: StudentJobsInspectionPagination
  point_system: {
    starting_points: number
    redo_threshold: number
    max_bonus: number
    deduction_levels: string
  }
  deduction_options: StudentJobsDeductionOption[]
  bonus_options: StudentJobsBonusOption[]
  inspection_types: StudentJobsInspectionType[]
  team_type_options: Array<{ value: string; label: string }>
  urls: { home: string }
}

export type StudentJobsDeductionOption = {
  key: string
  label: string
  points: number
  severity: 'major' | 'moderate' | 'minor'
}

export type StudentJobsBonusOption = {
  key: string
  label: string
  points: number
}

/** Checklist items are keyed by inspection type, so the shape stays open. */
export type CleaningDeductionFlags = Record<string, boolean>

export type CleaningBonusFlags = Record<string, boolean>

export type StudentJobsStudentOption = {
  id: number
  first_name: string
  last_name: string
  student_id: string
}

export type CleaningInspectionPayload = {
  team_id: number
  inspection_type: string
  inspection_date: string
  inspector_name: string
  inspector_notes?: string
  /** Checked checklist items, spread in by key. The server recalculates the score. */
  [key: string]: boolean | string | number | undefined
}
