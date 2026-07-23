import type { TeacherClassFeatures } from './teacherClasses'

export interface TeacherClassViewStudent {
  id: number
  student_id: string | null
  first_name: string
  last_name: string
  display_name: string
  grade_level: number | null
  grade_label: string
  initial: string
  photo_url: string
  email: string | null
  school_email: string | null
  date_of_birth_display: string | null
  parent1_name: string | null
  parent1_email: string | null
  parent1_phone: string | null
  links: {
    grades: string
    attendance: string
  }
}

export interface TeacherClassViewAnnouncement {
  id: number
  title: string
  message: string
  message_preview: string
  timestamp: string | null
  timestamp_display: string
}

export interface TeacherClassViewAssistantLog {
  id: number
  action_type: string
  action_label: string
  action_tone: string
  summary: string
  alert_sent: boolean
  created_at: string | null
  created_at_display: string
}

export interface TeacherClassViewLinks {
  back_to_classes: string
  add_assignment: string
  take_attendance: string
  manage_groups: string
  assignments_and_grades: string
  group_assignments: string
  deadline_reminders: string
  analytics: string
  feedback_360: string
  reflection_journals: string
  conflicts: string
  assistant_approvals: string
  announcements_legacy: string
  grade1_standards?: string
  grade3_standards?: string
}

export interface TeacherClassViewClass {
  id: number
  name: string
  subject: string
  grade_levels: number[]
  grade_levels_display: string
  enrollment_count: number
  assignment_count: number
  school_year_name: string | null
  room_display: string
  schedule_display: string
  google_group_email: string | null
  show_google_integration: boolean
}

export interface TeacherClassViewResponse {
  class: TeacherClassViewClass
  enrolled_students: TeacherClassViewStudent[]
  announcements: TeacherClassViewAnnouncement[]
  student_assistants: { id: number; display_name: string }[]
  assistant_action_logs: TeacherClassViewAssistantLog[]
  stats: {
    students: number
    assignments: number
    announcements: number
  }
  pending_assistant_count: number
  has_student_assistants: boolean
  features: TeacherClassFeatures
  links: TeacherClassViewLinks
}
