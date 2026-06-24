export interface ClosureSchoolYearOption {
  id: number
  name: string
  is_active: boolean
  start_date: string | null
  end_date: string | null
  has_active_closure?: boolean
}

export interface ClosureScheduleResponse {
  today: string
  suggested_date: string | null
  suggested_year_id: number | null
  school_years: ClosureSchoolYearOption[]
  active_closures: Record<
    string,
    {
      id: number
      phase: string
      phase_label: string
      school_year_name: string | null
    }
  >
  phase_labels: Record<string, string>
}

export interface ClosureExtension {
  id: number
  for_role: string
  extended_until: string | null
  reason: string
  target_label: string
  scope_user_id?: number | null
  scope_class_id?: number | null
  granted_by: string | null
}

export interface ClosureAuditEvent {
  id: number
  event_type: string
  created_at: string | null
  actor: string | null
  actor_label: string | null
}

export interface ClosureDashboardResponse {
  closure: {
    id: number
    phase: string
    phase_label: string
    closure_date: string | null
    student_lockout_at: string | null
    teacher_lockout_at: string | null
    finalize_at: string | null
    finalized_at: string | null
    notes: string | null
    created_by: string | null
    paused_by: string | null
    paused_at: string | null
    cancelled_by: string | null
    cancelled_at: string | null
    cancellation_reason: string | null
  }
  school_year: { id: number | null; name: string | null }
  today: string
  days_to: {
    student_lockout: number
    teacher_lockout: number
    finalize: number
  }
  extensions: ClosureExtension[]
  events: ClosureAuditEvent[]
  checklist: {
    classes_total: number
    students_total: number
    classes_without_q4_grades: {
      class_name: string
      subject: string
      missing_student_count: number
      roster_size: number
    }[]
  } | null
  finalize_stats: Record<string, unknown> | null
  next_year_suggestion: {
    name: string
    start_date: string
    end_date: string
    prior_year_name: string
    prior_year_start: string | null
    prior_year_end: string | null
  } | null
  next_year_exists: boolean
  phase_labels: Record<string, string>
  terminal_phases: string[]
  teachers: { id: number; name: string; user_id: number | null; username: string | null }[]
  classes: { id: number; name: string; subject: string }[]
}

export interface ActionResponse {
  success: boolean
  message: string
  closure_id?: number
  redirect_url?: string
}
