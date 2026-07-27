export interface StudentClassLinks {
  open_class: string
  assignments: string
  assistant: string | null
}

export interface StudentClassCard {
  id: number
  name: string
  subject: string
  grade_levels_display: string
  teacher_name: string
  average: number | null
  average_band: 'a' | 'b' | 'c' | 'd' | null
  group_name: string | null
  is_assistant: boolean
  archived: boolean
  links: StudentClassLinks
}

export interface StudentAssistantClassLink {
  id: number
  name: string
  hub_url: string
}

export interface StudentClassesResponse {
  has_active_school_year: boolean
  school_year_name: string | null
  classes: StudentClassCard[]
  archived_classes: StudentClassCard[]
  assistant_classes: StudentAssistantClassLink[]
  closure_phase_label: string | null
  assistant_console_url: string
}
