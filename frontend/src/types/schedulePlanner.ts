export interface PlannerClassCard {
  class_id: number
  class_name: string
  subject: string
  room: string
  teacher_name: string
  schedule_text: string | null
  grade_levels: number[]
}

export interface PlannerAssignedClass extends PlannerClassCard {
  assignment_id: number
  days_of_week: number[]
  day_labels?: string[]
}

export interface PlannerPeriodRow {
  id: number
  name: string
  kind: string
  usage_label?: string | null
  start_time: string
  end_time: string
  time_str?: string
  color_hex: string
  sort_order: number
  days_of_week: number[]
  day_labels?: string[]
  assigned_classes: PlannerAssignedClass[]
}

export interface SchedulePlannerResponse {
  bell_schedule: import('./bellSchedule').BellScheduleDto | null
  grade_level: number
  grade_label: string
  periods: PlannerPeriodRow[]
  classes: PlannerClassCard[]
  unassigned_classes: PlannerClassCard[]
}
