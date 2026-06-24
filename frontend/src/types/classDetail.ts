import type { ClassListItem, SchoolYearOption } from './classes'

export interface ClassMeta {
  can_admin_ui: boolean
  can_create: boolean
}

export interface StudentBrief {
  id: number
  student_id: string | null
  first_name: string
  last_name: string
  display_name: string
  grade_level: number | null
  initial: string
  photo_url: string | null
}

export interface StudentRosterEntry extends StudentBrief {
  email?: string | null
  has_account?: boolean
  username?: string | null
  view_url?: string
}

export interface ClassTeacherAssignee {
  id: number
  display_name: string
  role: string
}

export interface ClassManagementLinks {
  add_assignment: string
  attendance: string
  manage_roster: string
  grade1_standards: string
  grade3_standards: string
  assistant_approvals: string
  view_grades: string
  edit_class: string
  analytics: string
  feedback_360: string
  reflection_journals: string
  conflicts: string
  assignments_and_grades: string
  manage_groups: string
  deadline_reminders: string
  class_assignments?: string
  take_attendance?: string
}

export interface ClassDetailResponse {
  class: ClassListItem & {
    description?: string | null
    max_students?: number
    term_type?: string
    term_value?: string | null
    school_year_name?: string | null
    room_display?: string
    schedule_display?: string
  }
  teacher: { id: number | null; display_name: string; email?: string | null; phone?: string | null }
  enrolled_students: StudentBrief[]
  stats: {
    students: number
    assignments: number
    teacher_count: number
    grade_levels_display: string
  }
  pending_assistant_count: number
  features: { grade1_standards: boolean; grade3_standards: boolean }
  links: ClassManagementLinks
  meta: ClassMeta
}

export interface TeacherOption {
  id: number
  first_name: string
  last_name: string
  display_name: string
}

export interface ClassEditResponse extends ClassDetailResponse {
  form: {
    substitute_teacher_ids: number[]
    additional_teacher_ids: number[]
    student_assistant_ids: number[]
    is_active: boolean
  }
  teachers: TeacherOption[]
  eligible_assistants: StudentBrief[]
  max_assistants_per_class: number
  can_manage_assistants: boolean
}

export interface ClassRosterResponse {
  class: ClassListItem & {
    max_students?: number
    room_number?: string | null
    schedule?: string | null
  }
  enrolled_students: StudentRosterEntry[]
  available_students: StudentRosterEntry[]
  stats?: {
    enrolled: number
    with_accounts: number
    capacity_percent: number
    max_students: number
  }
  teachers?: {
    primary: ClassTeacherAssignee | null
    substitute: ClassTeacherAssignee[]
    additional: ClassTeacherAssignee[]
  }
  meta: ClassMeta
}

export interface ClassGradesColumn {
  key: string
  id: number
  title: string
  type: 'individual' | 'group'
  due_date: string | null
  status: string | null
}

export interface ClassGradesRow {
  student: StudentBrief
  grades: Record<string, { grade: string | number; type: string; group_name?: string | null }>
  average: string | number
}

export interface ClassGradesResponse {
  class: ClassListItem & {
    schedule?: string | null
    schedule_display?: string
  }
  view_mode: string
  columns: ClassGradesColumn[]
  rows: ClassGradesRow[]
  stats?: {
    students: number
    assignments: number
    individual_count: number
    group_count: number
    schedule_display: string
  }
  meta: ClassMeta
}

export interface ClassFormOptionsResponse {
  teachers: TeacherOption[]
  active_school_year: { id: number; name: string } | null
  meta: ClassMeta
}

export interface ClassSaveResponse {
  success: boolean
  message: string
  class_id?: number
  redirect?: string
}

export interface GoogleClassroomOption {
  id: string
  name: string
  section?: string
  room?: string
}

export interface CoreSetupGradeEntry {
  index: number
  subject: string
  class_name: string
  setup_key: string
  assignment_key: string
}

export interface CoreSetupGrade {
  grade_level: number
  label: string
  entries: CoreSetupGradeEntry[]
}

export interface CoreSetupFormResponse {
  school_years: SchoolYearOption[]
  default_school_year_id: number | null
  setup_grade_levels: number[]
  grades: CoreSetupGrade[]
  teachers: TeacherOption[]
  guide: unknown[]
  meta: ClassMeta
}

export interface CoreSetupPreviewResult {
  to_create: Array<Record<string, unknown>>
  skipped: Array<Record<string, unknown>>
  errors: string[]
  created_count?: number
}

export interface CreateClassPayload {
  name: string
  subject: string
  teacher_id: number
  room_number?: string
  schedule?: string
  max_students?: number
  description?: string
  grade_levels?: number[]
  substitute_teacher_ids?: number[]
  additional_teacher_ids?: number[]
}

export interface UpdateClassPayload extends CreateClassPayload {
  is_active?: boolean
  term_type?: string
  term_value?: string | null
  student_assistant_ids?: number[]
}
