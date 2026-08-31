export type StudentJobsMember = {
  id: number
  member_id: number
  name: string
  role: string
  assignment_description: string
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
  current_score: number
  stats: StudentJobsTeamStats
  members: StudentJobsMember[]
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
  team_type_options: Array<{ value: string; label: string }>
  urls: { home: string }
}

export type StudentJobsDeductionOption = {
  key: keyof CleaningDeductionFlags
  label: string
  points: number
  severity: 'major' | 'moderate' | 'minor'
}

export type StudentJobsBonusOption = {
  key: keyof CleaningBonusFlags
  label: string
  points: number
}

export type CleaningDeductionFlags = {
  bathroom_not_restocked: boolean
  trash_can_left_full: boolean
  floor_not_swept: boolean
  materials_left_out: boolean
  tables_missed: boolean
  classroom_trash_full: boolean
  bathroom_floor_poor: boolean
  not_finished_on_time: boolean
  small_debris_left: boolean
  trash_spilled: boolean
  dispensers_half_filled: boolean
}

export type CleaningBonusFlags = {
  exceptional_finish: boolean
  speed_efficiency: boolean
  going_above_beyond: boolean
  teamwork_award: boolean
}

export type StudentJobsStudentOption = {
  id: number
  first_name: string
  last_name: string
  student_id: string
}

export type CleaningInspectionPayload = {
  team_id: number
  inspection_date: string
  inspector_name: string
  inspector_notes?: string
  final_score: number
  major_deductions: number
  moderate_deductions: number
  minor_deductions: number
  bonus_points: number
  bathroom_not_restocked: boolean
  trash_can_left_full: boolean
  floor_not_swept: boolean
  materials_left_out: boolean
  tables_missed: boolean
  classroom_trash_full: boolean
  bathroom_floor_poor: boolean
  not_finished_on_time: boolean
  small_debris_left: boolean
  trash_spilled: boolean
  dispensers_half_filled: boolean
  exceptional_finish: boolean
  speed_efficiency: boolean
  going_above_beyond: boolean
  teamwork_award: boolean
}
