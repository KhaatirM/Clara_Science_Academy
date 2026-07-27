export interface StudentCollaborateStats {
  feedback: number
  journals: number
  conflicts: number
  open_feedback: number
}

export interface StudentCollaborateCriterion {
  id: number | null
  name: string
  description: string | null
  type: string
  scale_min: number
  scale_max: number
  required: boolean
}

export interface StudentCollaborateFeedbackSession {
  id: number
  title: string
  description: string | null
  class_name: string
  target_name: string
  due_display: string | null
  criteria: StudentCollaborateCriterion[]
}

export interface StudentCollaborateGroupAssignment {
  id: number
  title: string
  class_name: string
  group_id: number
  group_name: string
  label: string
}

export interface StudentCollaborateFeedbackHistory {
  id: number
  submitted_at: string | null
  submitted_display: string | null
  session_title: string
  target_name: string
  class_name: string | null
  is_anonymous: boolean
  preview: string | null
}

export interface StudentCollaborateJournalHistory {
  id: number
  submitted_at: string | null
  submitted_display: string | null
  group_name: string
  assignment_title: string
  collaboration_rating: number
  learning_rating: number
  reflection_preview: string
}

export interface StudentCollaborateConflictHistory {
  id: number
  reported_at: string | null
  reported_display: string | null
  group_name: string
  assignment_title: string
  conflict_type: string
  conflict_type_label: string
  severity_level: string
  status: string
  status_label: string
  description_preview: string
}

export interface StudentCollaborateOption {
  value: string
  label: string
}

export interface StudentCollaborateResponse {
  school_year_name: string | null
  stats: StudentCollaborateStats
  available_feedback_sessions: StudentCollaborateFeedbackSession[]
  group_assignments: StudentCollaborateGroupAssignment[]
  feedback_history: StudentCollaborateFeedbackHistory[]
  journal_history: StudentCollaborateJournalHistory[]
  conflict_history: StudentCollaborateConflictHistory[]
  conflict_types: StudentCollaborateOption[]
  severity_levels: StudentCollaborateOption[]
}
