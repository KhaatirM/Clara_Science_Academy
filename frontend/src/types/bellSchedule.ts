export type BellPeriodKind = 'class' | 'break' | 'lunch' | 'tutorial' | 'other'

export interface BellPeriodDto {
  id?: number
  name: string
  kind: BellPeriodKind | string
  start_time: string
  end_time: string
  time_str?: string
  color_hex: string
  sort_order: number
  days_of_week: number[]
  day_labels?: string[]
}

export interface BellScheduleDto {
  id: number
  school_year_id: number
  title: string
  is_active: boolean
  periods: BellPeriodDto[]
}

export interface BellGridClass {
  class_id: number
  class_name: string
  subject: string
  time_str: string
  room: string
  teacher_name?: string
  student_count?: number
  is_now?: boolean
  is_upcoming?: boolean
}

export interface BellGridCell {
  period_id: number
  name: string
  kind: string
  time_str: string
  start_time: string
  end_time: string
  color_hex: string
  classes: BellGridClass[]
  is_now?: boolean
}

export interface BellGridDayColumn {
  day_index: number
  day_name: string
  day_short: string
  is_today: boolean
  cells: BellGridCell[]
}

export interface BellGridUnmapped {
  class_id: number
  class_name: string
  subject: string
  day_index: number
  day_name: string
  time_str: string
  room: string
}

export interface BellGridPayload {
  bell_schedule: BellScheduleDto | null
  day_columns: BellGridDayColumn[]
  unmapped: BellGridUnmapped[]
}
