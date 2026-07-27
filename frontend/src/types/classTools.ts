export interface ClassToolHeader {
  id: number
  name: string
  subject?: string | null
  teacher_name?: string
}

export interface ClassAnalyticsResponse extends ClassToolHeader {
  tool: 'analytics'
  title: string
  summary: {
    groups: number
    group_assignments: number
    students: number
  }
  groups: { id: number; name: string; member_count: number }[]
  group_assignments: {
    id: number
    title: string
    status: string | null
    due_date: string | null
  }[]
}

export interface DeadlineReminderRow {
  id: number
  title: string
  message: string
  reminder_type: string
  reminder_frequency: string
  send_at: string | null
  status: string
  is_upcoming: boolean
  assignment_id?: number | null
  group_assignment_id?: number | null
  assignment_title?: string | null
  last_sent?: string | null
  created_at?: string | null
}

export interface ClassDeadlineRemindersResponse extends ClassToolHeader {
  tool: 'deadline-reminders'
  title: string
  stats: {
    total: number
    active: number
    upcoming: number
    assignment: number
  }
  reminders: DeadlineReminderRow[]
  upcoming: DeadlineReminderRow[]
}

export interface DeadlineReminderFormMeta {
  class: { id: number; name: string }
  assignments: { id: number; title: string; due_date?: string | null }[]
  group_assignments: { id: number; title: string; due_date?: string | null }[]
  students: { id: number; display_name: string }[]
  defaults: {
    reminder_type: string
    reminder_frequency: string
    reminder_date: string
  }
  reminder?: {
    id: number
    reminder_type: string
    reminder_frequency: string
    reminder_title: string
    reminder_message: string
    reminder_date: string
    assignment_id?: number | null
    group_assignment_id?: number | null
    selected_student_ids: number[]
    is_active: boolean
    last_sent?: string | null
    created_at?: string | null
  }
}

export interface StudentNeedingReminder {
  id: number
  display_name: string
  student_id?: string | null
  status: 'not_submitted' | 'submitted_not_graded'
}

export interface ClassFeedback360Response extends ClassToolHeader {
  tool: '360-feedback'
  title: string
  stats?: { total: number; active: number }
  sessions: {
    id: number
    title: string
    status: string
    feedback_type?: string | null
    due_date?: string | null
    created_at?: string | null
  }[]
}

export interface ClassReflectionJournalsResponse extends ClassToolHeader {
  tool: 'reflection-journals'
  title: string
  stats?: { total: number }
  journals: {
    id: number
    title: string
    assignment_title?: string | null
    submitted_at?: string | null
    status: string
    collaboration_rating?: number | null
    learning_rating?: number | null
  }[]
}

export interface ClassConflictsResponse extends ClassToolHeader {
  tool: 'conflicts'
  title: string
  stats?: { total: number; open: number }
  conflicts: {
    id: number
    title: string
    status: string
    severity?: string | null
    description?: string
    created_at?: string | null
  }[]
}

export type ClassAssessmentToolResponse =
  | ClassFeedback360Response
  | ClassReflectionJournalsResponse
  | ClassConflictsResponse
