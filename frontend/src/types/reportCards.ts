export interface ReportCardStudentRef {
  id: number
  first_name: string
  last_name: string
  grade_level: number
  grade_display: string
  initials: string
}

export interface ReportCardSchoolYearRef {
  id: number
  name: string
}

export interface ReportCardItem {
  id: number
  student: ReportCardStudentRef | null
  school_year: ReportCardSchoolYearRef | null
  quarter: string
  report_type: string
  generated_at: string | null
  generated_at_display: string | null
  director_approved: boolean
  publish_status: 'published' | 'pending' | 'unofficial'
  urls: {
    view: string
    pdf: string
    history: string | null
  }
}

export interface ReportCardCategoryCard {
  slug: string
  title: string
  range_label: string
  description: string
  icon: string
  tone: string
  student_count: number
  path: string
}

export interface ReportCardsSearchFilters {
  school_years: Array<{ id: number; name: string; is_active: boolean }>
  students: Array<{ id: number; name: string; grade_display: string }>
  classes: Array<{ id: number; name: string; school_year_id: number | null }>
  quarters: string[]
}

export interface ReportCardsSearchResponse {
  report_cards: ReportCardItem[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
  }
  filters: ReportCardsSearchFilters
  applied: {
    school_year_id: number | null
    quarter: string | null
    student_id: number | null
    class_id: number | null
    q: string | null
  }
}

export interface ReportCardsPendingResponse {
  total: number
  report_cards: ReportCardItem[]
}

export interface ReportCardStandardsLegendItem {
  code: string
  label: string
}

export interface ReportCardStandardsChecklist {
  variant: 'grade1' | 'grade3' | 'k2'
  title: string
  description: string
  editor_url: string | null
  pdf_pages: string[]
  legend: ReportCardStandardsLegendItem[]
}

export interface ReportCardStandardsMarksSummary {
  language_arts: { marked: number; total: number }
  math: { marked: number; total: number }
}

export interface ReportCardsHubResponse {
  stats: {
    total_students: number
    total_reports: number
    pending_parent_approval: number
    school_years_count: number
  }
  categories: ReportCardCategoryCard[]
  recent_reports: ReportCardItem[]
  urls: {
    generate_form: string
    students: string
    grades: string
    attendance: string
    home: string
    grade1_standards?: string
    grade3_standards?: string
  }
}

export interface ReportCardsCategoryStudent {
  id: number
  student_id: string
  first_name: string
  last_name: string
  name: string
  grade_level: number
  grade_display: string
  initials: string
  enrollment_count: number
  report_count: number
  generate_url: string
  recent_reports: ReportCardItem[]
}

export interface ReportCardsCategoryResponse {
  category: {
    slug: string
    name: string
    short_name: string
    icon: string
    grade_levels: number[]
    grade_displays: string[]
  }
  stats: {
    total_students: number
    grade_levels: number
    total_reports: number
    students_without_reports: number
  }
  students: ReportCardsCategoryStudent[]
  urls: {
    hub: string
    generate_form: string
    grade1_standards?: string
    grade3_standards?: string
  }
  warnings: {
    unfinalized_grades: number[]
    banner_messages: Record<string, string>
  }
}

export interface ReportCardActionResponse {
  success: boolean
  message: string
}

export interface ReportCardGenerateFormResponse {
  students: Array<{
    id: number
    first_name: string
    last_name: string
    grade_level: number
    grade_display: string
    student_id: string
    is_active: boolean
    label: string
  }>
  school_years: Array<{ id: number; name: string; is_active: boolean }>
  default_school_year_id: number | null
  preselected_student: {
    id: number
    first_name: string
    last_name: string
    grade_level: number
    grade_display: string
    student_id: string
  } | null
  category: string
  quarters: string[]
  standards_checklist_legend: ReportCardStandardsLegendItem[]
  standards_checklist_urls: {
    grade1_standards?: string
    grade3_standards?: string
  }
  preselected_standards_checklist: ReportCardStandardsChecklist | null
  urls: {
    hub: string
    students_profile: string
    grade1_standards?: string
    grade3_standards?: string
  }
  warnings: {
    unfinalized_grades: number[]
    banner_messages: Record<string, string>
  }
}

export interface ReportCardStudentDetails {
  id: number
  first_name: string
  last_name: string
  student_id: string
  gender: string
  grade_level: number
  grade_display: string
  address: string
  dob: string | null
  state_id: string
  entrance_date: string
  expected_grad_date: string
  profile_url: string
  standards_checklist?: ReportCardStandardsChecklist | null
}

export interface ReportCardClassOption {
  id: number
  name: string
  subject: string
  teacher_name: string
}

export interface ReportCardGeneratePayload {
  student_id: number
  school_year_id: number
  class_ids: number[]
  quarters: string[]
  report_type: 'official' | 'unofficial'
  include_attendance: boolean
  include_comments: boolean
  persist_comment_overrides: boolean
  additional_comments?: string
  comment_overrides?: Record<string, string>
  return_category?: string
}

export interface ReportCardGenerateResponse {
  success: boolean
  message?: string
  report_card_id?: number
  warnings?: string[]
  inconsistency_flag?: boolean
  return_category?: string
  urls?: {
    view: string
    pdf: string
    history: string | null
    return_category?: string
  }
  student?: { id: number; name: string }
}

export interface ReportCardDetailResponse {
  report_card: {
    id: number
    quarter: string
    report_type: string
    generated_at: string | null
    generated_at_display: string | null
    director_approved: boolean
    publish_status: 'published' | 'pending' | 'unofficial'
    is_official: boolean
    approved_at_display: string | null
    approved_by: string | null
  }
  student: {
    id: number
    first_name: string
    last_name: string
    grade_level: number
    grade_display: string
    student_id: string
  } | null
  school_year: { id: number; name: string } | null
  classes: Array<{ id: number; name: string; subject: string }>
  grades: Array<{ subject: string; letter_grade: string; percentage: number }>
  attendance: Array<{
    class_name: string
    present: number
    unexcused: number
    excused: number
    tardy: number
  }>
  include_attendance: boolean
  include_comments: boolean
  comments: Array<{ class_id: number | null; class_name: string; comment: string }>
  is_director: boolean
  urls: { view: string; pdf: string; history: string | null }
  standards_checklist?: ReportCardStandardsChecklist | null
  standards_marks_summary?: ReportCardStandardsMarksSummary | null
}

export interface ReportCardHistoryYearGroup {
  school_year: string
  school_year_id?: number | null
  is_active?: boolean
  grade_level?: number | null
  grade_display?: string
  report_cards: Array<
    ReportCardItem & {
      generated_at_long: string | null
      class_count: number
      class_count_label: string
    }
  >
}

export interface ReportCardStudentSchoolYear {
  id: number
  name: string
  is_active: boolean
  status_label: string
  grade_level: number | null
  grade_display: string
  class_count: number
  report_count: number
  generate_url: string
  has_enrollment: boolean
  report_cards: ReportCardItem[]
}

export interface ReportCardHistoryResponse {
  student: {
    id: number
    first_name: string
    last_name: string
    grade_level: number
    grade_display: string
    student_id: string
    initials: string
  }
  total_count: number
  report_cards_by_year: ReportCardHistoryYearGroup[]
  school_years: ReportCardStudentSchoolYear[]
  urls: { generate: string; hub: string }
}
