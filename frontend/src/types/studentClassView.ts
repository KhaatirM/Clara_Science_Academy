export interface StudentClassDetailClass {
  id: number
  name: string
  subject: string
  grade_levels_display: string
}

export interface StudentClassDetailTeacher {
  id: number
  name: string
  position: string
  email: string | null
  phone: string | null
}

export interface StudentClassDetailStats {
  student_count: number
  assignment_count: number
  class_gpa: number
  graded_count: number
}

export interface StudentClassDetailGroupMember {
  id: number
  name: string
  is_you: boolean
}

export interface StudentClassDetailGroup {
  id: number
  name: string
  members: StudentClassDetailGroupMember[]
}

export interface StudentClassDetailRosterItem {
  id: number
  name: string
  email: string | null
  is_you: boolean
}

export interface StudentClassDetailAnnouncement {
  id: number
  title: string
  message: string
  timestamp: string | null
  timestamp_display: string | null
}

export interface StudentClassDetailAssignment {
  id: number
  title: string
  description_preview: string
  assignment_type: string
  type_label: string
  due_date: string | null
  due_display: string | null
  status: string
  letter_grade: string | null
  primary_url: string | null
}

export interface StudentClassDetailLinks {
  back: string
  assignments: string
  assistant: string | null
}

export interface StudentClassDetailResponse {
  class: StudentClassDetailClass
  teacher: StudentClassDetailTeacher | null
  stats: StudentClassDetailStats
  group: StudentClassDetailGroup | null
  roster: StudentClassDetailRosterItem[]
  announcements: StudentClassDetailAnnouncement[]
  assignments: StudentClassDetailAssignment[]
  is_assistant: boolean
  links: StudentClassDetailLinks
  server_now: string
}
