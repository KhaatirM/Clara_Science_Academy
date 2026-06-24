export interface AcademicPeriod {
  id: number
  name: string
  period_type: 'quarter' | 'semester' | string
  start_date: string | null
  end_date: string | null
}

export interface CalendarEventRow {
  id: number
  name: string
  event_type: string
  start_date: string | null
  end_date: string | null
}

export interface SchoolYearRow {
  id: number
  name: string
  is_active: boolean
  start_date: string | null
  end_date: string | null
  total_days: number | null
  academic_periods: AcademicPeriod[]
  calendar_events: CalendarEventRow[]
}

export interface SchoolYearsPageResponse {
  school_years: SchoolYearRow[]
  active_school_year: SchoolYearRow | null
  stats: {
    total_years: number
    inactive_count: number
    active_periods: number
    active_total_days: number | null
  }
}

export interface ActionResponse {
  success: boolean
  message: string
  school_year_id?: number
}
