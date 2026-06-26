export type StudentJobsMember = {
  id: number
  member_id: number
  name: string
  role: string
  assignment_description: string
}

export type StudentJobsTeam = {
  id: number
  name: string
  description: string
  team_type: string
  current_score: number
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
  bonus_points: number
  status: string
  inspector_name: string
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
  point_system: {
    starting_points: number
    redo_threshold: number
    max_bonus: number
    deduction_levels: string
  }
  urls: { home: string }
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
