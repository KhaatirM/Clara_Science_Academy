export interface CalendarEventItem {
  title: string
  category: string
  type: string
  description?: string
  source?: 'calendar_event' | 'academic_period' | 'school_year' | 'teacher_work_day' | 'school_break'
  entity_id?: number
  deletable?: boolean
}

export interface CalendarDayCell {
  day_num: number | null
  is_current_month: boolean
  is_today: boolean
  events: CalendarEventItem[]
}

export interface CalendarWorkDay {
  id: number
  title: string
  date: string
  attendance_requirement?: string | null
  description: string
}

export interface CalendarBreak {
  id: number
  name: string
  start_date: string
  end_date: string
  break_type: string
  description: string
}

export interface ActiveClosureBrief {
  id: number
  phase: string
  phase_label: string
  school_year_id: number
  school_year_name: string | null
}

export interface CalendarPageResponse {
  month: number
  year: number
  month_name: string
  weekdays: string[]
  weeks: CalendarDayCell[][]
  prev_month: { month: number; year: number }
  next_month: { month: number; year: number }
  events_this_month: number
  active_school_year: {
    id: number
    name: string
    start_date: string | null
    end_date: string | null
  } | null
  work_days: CalendarWorkDay[]
  breaks: CalendarBreak[]
  active_closures: ActiveClosureBrief[]
  event_categories: { value: string; label: string }[]
  break_types: string[]
}
