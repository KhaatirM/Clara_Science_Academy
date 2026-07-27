export type GradeStandardsLegendItem = {
  code: string
  label: string
}

export type GradeStandardsQuarterStats = {
  filled: number
  total: number
  percent: number
}

export type GradeStandardsClassStats = {
  total_cells_per_quarter: number
  standards_count: number
  students_count: number
  quarters: Record<string, GradeStandardsQuarterStats>
  overall: GradeStandardsQuarterStats
  last_updated?: string | null
}

export type GradeStandardsClassCard = {
  id: number
  name: string
  subject: string
  subject_key: 'language_arts' | 'math'
  student_count: number
  stats: GradeStandardsClassStats
  editor_path: string
}

export type GradeStandardsHubResponse = {
  grade_level: number
  title: string
  school_year: { id: number; name: string } | null
  current_quarter: string
  quarter_columns: string[]
  valid_marks: string[]
  legend: GradeStandardsLegendItem[]
  groups: {
    language_arts: GradeStandardsClassCard[]
    math: GradeStandardsClassCard[]
  }
  summary: {
    total_classes: number
    total_students: number
    overall_percent: number
    overall_filled: number
    overall_total: number
  }
  urls: {
    hub: string
    report_cards: string
  }
  error?: string
}

export type GradeStandardsStandard = {
  id: string
  section: string
  text: string
}

export type GradeStandardsStudent = {
  id: number
  first_name: string
  last_name: string
  display_name: string
}

export type GradeStandardsEditorResponse = {
  grade_level: number
  class: {
    id: number
    name: string
    subject: string
    subject_key: string
  }
  subject_catalog: { subject: string }
  school_year: { id: number; name: string }
  students: GradeStandardsStudent[]
  standards: GradeStandardsStandard[]
  quarter: string
  quarter_columns: string[]
  valid_marks: string[]
  view_mode: 'grid' | 'student'
  selected_student_id: number | null
  marks_grid: Record<number, Record<string, string>>
  marks_student_view: Record<number, Record<string, Record<string, string>>>
  overall_stats: GradeStandardsClassStats & { last_updated_display?: string | null }
  section_stats: Record<string, GradeStandardsQuarterStats>
  other_classes: GradeStandardsClassCard[]
  can_copy_previous: boolean
  urls: {
    hub: string
    report_cards: string
  }
}

export type GradeStandardsSavePayload = {
  quarter: string
  bulk_action?: string
  marks?: Array<{
    student_id: number
    standard_id: string
    quarter?: string
    value: string
  }>
}

export type GradeStandardsSaveResponse = {
  success: boolean
  changed: number
  message: string
}
